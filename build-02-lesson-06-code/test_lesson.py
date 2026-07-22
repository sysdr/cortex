"""
Tests for Build 02, Lesson 06.
Run with: pytest test_lesson.py -v
"""

from pathlib import Path

import torch
import pytest
from torch import nn
from torch.utils.data import DataLoader

from lesson_code import (
    CortexXORClassifier,
    XORDataset,
    compare_autograd_to_manual_gradients,
    evaluate,
    generate_xor_documents,
    get_device,
    load_checkpoint,
    save_checkpoint,
    train,
)


@pytest.fixture
def xor_data():
    return generate_xor_documents(n=400, seed=7)


def test_dataset_length_and_item_shapes(xor_data):
    X, y = xor_data
    dataset = XORDataset(X, y)

    assert len(dataset) == 400
    x_item, y_item = dataset[0]
    assert x_item.shape == (2,)
    assert y_item.shape == ()


def test_model_forward_returns_one_logit_per_row():
    model = CortexXORClassifier(n_hidden=4)
    batch = torch.randn(16, 2)

    output = model(batch)

    assert output.shape == (16,)  # squeezed, not (16, 1)


def test_training_solves_xor(xor_data):
    torch.manual_seed(0)
    X, y = xor_data
    dataset = XORDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    model = CortexXORClassifier(n_hidden=4)
    train(model, dataloader, epochs=300, lr=0.1)

    X_t, y_t = torch.from_numpy(X), torch.from_numpy(y)
    acc = evaluate(model, X_t, y_t)

    assert acc > 0.90


def test_checkpoint_save_and_load_produces_identical_predictions(tmp_path: Path, xor_data):
    torch.manual_seed(0)
    X, y = xor_data
    dataset = XORDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    model = CortexXORClassifier(n_hidden=4)
    train(model, dataloader, epochs=100, lr=0.1)

    checkpoint_path = tmp_path / "model.pt"
    save_checkpoint(model, checkpoint_path)

    reloaded = CortexXORClassifier(n_hidden=4)
    load_checkpoint(reloaded, checkpoint_path)

    X_t = torch.from_numpy(X)
    model.eval()
    reloaded.eval()
    with torch.no_grad():
        original_logits = model(X_t)
        reloaded_logits = reloaded(X_t)

    assert torch.allclose(original_logits, reloaded_logits)


def test_get_device_returns_a_valid_torch_device():
    device = get_device()

    assert isinstance(device, torch.device)
    assert device.type in ("cpu", "cuda")


# ── The actual proof: autograd vs hand-derived backprop ─────────────────


def test_autograd_matches_manual_gradients(xor_data):
    """The core claim of this lesson, checked directly: PyTorch's
    autograd and Lesson 05's hand-derived chain rule should agree to
    within float32 precision, not just 'roughly similar.'"""
    X, y = xor_data
    diffs = compare_autograd_to_manual_gradients(X, y, n_hidden=4, seed=0)

    for key, diff in diffs.items():
        assert diff < 1e-5, f"{key} differs by {diff}, too large for float32 agreement"


# ── The zero_grad() failure mode, verified directly ─────────────────────


def test_forgetting_zero_grad_causes_training_to_diverge(xor_data):
    """A real, verified failure mode, not a hypothetical warning:
    omitting optimizer.zero_grad() lets gradients accumulate across every
    batch, forever — loss looks fine for the first few epochs, then
    explodes. Checked directly, not just asserted in a comment."""
    torch.manual_seed(0)
    X, y = xor_data
    dataset = XORDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    model = CortexXORClassifier(n_hidden=4)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    criterion = nn.BCEWithLogitsLoss()

    final_loss = None
    model.train()
    for _ in range(300):
        epoch_loss = 0.0
        for X_batch, y_batch in dataloader:
            # deliberately never call optimizer.zero_grad() here
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * len(X_batch)
        final_loss = epoch_loss / len(dataset)

    # a healthy run ends near 0.02; without zero_grad(), it ends
    # somewhere far larger, having diverged rather than converged
    assert final_loss > 1.0
