"""
Cortex — Build 02, Lesson 06
PyTorch fundamentals: the same classifier again, now production-shaped.

The exact architecture from Lesson 05 — two linear layers, ReLU in
between — reimplemented in PyTorch. The point of today isn't a new model;
it's proving that autograd computes the identical gradients Lesson 05
derived by hand, then wrapping the same math in the conventions a real
PyTorch codebase actually uses: nn.Module, DataLoader, an optimizer,
device handling, and a checkpoint you can save and reload.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


# ── Same XOR problem as Lesson 05, unchanged ────────────────────────────


def generate_xor_documents(n: int = 400, noise: float = 0.15, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    is_urgent = rng.integers(0, 2, size=n).astype(np.float32)
    is_long = rng.integers(0, 2, size=n).astype(np.float32)
    needs_review = (is_urgent.astype(int) ^ is_long.astype(int)).astype(np.float32)
    X = np.column_stack([is_urgent, is_long]).astype(np.float32)
    X += rng.normal(0, noise, size=X.shape).astype(np.float32)
    return X, needs_review


class XORDataset(Dataset):
    """Wrapping the array in a Dataset isn't ceremony for two features and
    400 rows — it's the same interface Cortex's real training data will
    need once it's a real corpus, not synthetic. DataLoader batching,
    shuffling, and (later) multi-worker loading all depend on this
    interface existing, regardless of how small today's dataset is."""

    def __init__(self, X: np.ndarray, y: np.ndarray) -> None:
        self.X = torch.from_numpy(X)
        self.y = torch.from_numpy(y)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


class CortexXORClassifier(nn.Module):
    """Structurally identical to Lesson 05's hand-built network: a
    Linear(2, 4), a ReLU, a Linear(4, 1). The forward pass deliberately
    returns raw logits, not a sigmoid-squashed probability — paired with
    BCEWithLogitsLoss below, that's a numerical-stability choice, not a
    simplification. Computing sigmoid and then log() as two separate
    steps can lose precision in exactly the extreme cases Lesson 01's
    manual clipping worked around; BCEWithLogitsLoss fuses them into one
    numerically stable operation instead."""

    def __init__(self, n_hidden: int = 4) -> None:
        super().__init__()
        self.layer1 = nn.Linear(2, n_hidden)
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(n_hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.layer1(x)
        x = self.relu(x)
        x = self.layer2(x)
        return x.squeeze(-1)  # raw logits, shape (batch,)


def get_device() -> torch.device:
    """CPU here, always — this sandbox has no GPU. The pattern is written
    the way every real PyTorch project writes it anyway: never hardcode
    "cpu", always ask, so the exact same code runs unmodified on a machine
    that does have a GPU."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def train(
    model: nn.Module,
    dataloader: DataLoader,
    epochs: int = 300,
    lr: float = 0.1,
    device: torch.device | None = None,
) -> list[float]:
    device = device or get_device()
    model.to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=lr)
    criterion = nn.BCEWithLogitsLoss()

    loss_history = []
    model.train()  # enables any train-only behavior (dropout, batchnorm) —
                    # a no-op for this architecture, but the habit matters
                    # the moment either of those gets added later.
    for _ in range(epochs):
        epoch_loss = 0.0
        for X_batch, y_batch in dataloader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()  # gradients accumulate by default —
                                    # forgetting this is a real, common bug
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()        # autograd: the entire chain rule from
                                    # Lesson 05, computed automatically
            optimizer.step()

            epoch_loss += loss.item() * len(X_batch)
        loss_history.append(epoch_loss / len(dataloader.dataset))

    return loss_history


def evaluate(model: nn.Module, X: torch.Tensor, y: torch.Tensor, device: torch.device | None = None) -> float:
    device = device or get_device()
    model.eval()  # the counterpart to model.train() — again a no-op for
                  # this architecture, but the discipline matters later
    with torch.no_grad():  # no need to track gradients just to predict
        logits = model(X.to(device))
        preds = (torch.sigmoid(logits) >= 0.5).float().cpu()
    return float((preds == y).float().mean())


def save_checkpoint(model: nn.Module, path: Path) -> None:
    torch.save(model.state_dict(), path)


def load_checkpoint(model: nn.Module, path: Path) -> nn.Module:
    model.load_state_dict(torch.load(path, weights_only=True))
    return model


# ── The actual proof: does autograd match Lesson 05's hand-derived math? ─


def compare_autograd_to_manual_gradients(X: np.ndarray, y: np.ndarray, n_hidden: int = 4, seed: int = 0) -> dict:
    """Builds a PyTorch model and a from-scratch (Lesson 05 style) model
    with IDENTICAL starting weights, runs one forward and backward pass
    in both, and compares the resulting gradients directly. If PyTorch's
    autograd and Lesson 05's hand-derived chain rule don't agree, one of
    them has a real bug — this is gradient checking's sibling: instead of
    checking against a numerical approximation, check two independent,
    from-first-principles implementations against each other."""
    rng = np.random.default_rng(seed)
    W1 = rng.normal(0, 0.5, size=(2, n_hidden)).astype(np.float32)
    b1 = np.zeros(n_hidden, dtype=np.float32)
    W2 = rng.normal(0, 0.5, size=(n_hidden, 1)).astype(np.float32)
    b2 = np.zeros(1, dtype=np.float32)

    # --- manual (Lesson 05 style) forward + backward ---
    z1 = X @ W1 + b1
    a1 = np.maximum(0, z1)
    z2 = (a1 @ W2 + b2).flatten()
    a2 = 1.0 / (1.0 + np.exp(-np.clip(z2, -500, 500)))

    n = X.shape[0]
    dz2 = (a2 - y) / n
    manual_dW2 = a1.T @ dz2.reshape(-1, 1)
    manual_db2 = dz2.sum()
    da1 = dz2.reshape(-1, 1) @ W2.T
    dz1 = da1 * (z1 > 0).astype(np.float32)
    manual_dW1 = X.T @ dz1
    manual_db1 = dz1.sum(axis=0)

    # --- PyTorch, with identical starting weights ---
    torch_model = CortexXORClassifier(n_hidden=n_hidden)
    with torch.no_grad():
        torch_model.layer1.weight.copy_(torch.from_numpy(W1.T))
        torch_model.layer1.bias.copy_(torch.from_numpy(b1))
        torch_model.layer2.weight.copy_(torch.from_numpy(W2.T))
        torch_model.layer2.bias.copy_(torch.from_numpy(b2))

    X_t = torch.from_numpy(X)
    y_t = torch.from_numpy(y)
    criterion = nn.BCEWithLogitsLoss()

    logits = torch_model(X_t)
    loss = criterion(logits, y_t)
    loss.backward()

    return {
        "dW1_max_diff": float(np.max(np.abs(manual_dW1 - torch_model.layer1.weight.grad.numpy().T))),
        "db1_max_diff": float(np.max(np.abs(manual_db1 - torch_model.layer1.bias.grad.numpy()))),
        "dW2_max_diff": float(np.max(np.abs(manual_dW2.flatten() - torch_model.layer2.weight.grad.numpy().flatten()))),
        "db2_max_diff": float(np.max(np.abs(manual_db2 - torch_model.layer2.bias.grad.numpy()[0]))),
    }


def _demo() -> None:
    torch.manual_seed(0)  # reproducibility — the PyTorch-specific seed,
                           # separate from NumPy's, and easy to forget

    X, y = generate_xor_documents(n=400)
    dataset = XORDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    device = get_device()
    print(f"Device: {device}\n")

    model = CortexXORClassifier(n_hidden=4)
    loss_history = train(model, dataloader, epochs=300, lr=0.1, device=device)

    X_t, y_t = torch.from_numpy(X), torch.from_numpy(y)
    acc = evaluate(model, X_t, y_t, device=device)
    print(f"Final loss: {loss_history[-1]:.4f}")
    print(f"Accuracy: {acc:.1%}")

    checkpoint_path = Path("model.pt")
    save_checkpoint(model, checkpoint_path)
    reloaded = CortexXORClassifier(n_hidden=4)
    load_checkpoint(reloaded, checkpoint_path)
    reloaded_acc = evaluate(reloaded, X_t, y_t, device=device)
    print(f"Reloaded model accuracy: {reloaded_acc:.1%}  (should match exactly)")

    print("\n--- Does autograd match Lesson 05's hand-derived gradients? ---")
    diffs = compare_autograd_to_manual_gradients(X, y, n_hidden=4)
    for key, value in diffs.items():
        print(f"  {key}: {value:.2e}")


if __name__ == "__main__":
    _demo()
