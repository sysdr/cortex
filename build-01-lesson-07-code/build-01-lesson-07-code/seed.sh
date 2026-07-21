#!/usr/bin/env bash
# Cortex — seed.sh
# Unchanged since Lesson 03. Still runs on the host, not inside the
# container — docker-compose.yml mounts its output in via a volume.

set -euo pipefail

DATA_DIR="${1:-./data/documents}"

mkdir -p "$DATA_DIR"

SAMPLE_DOCS=(
  '{"id":"doc-001","title":"Q3 Roadmap","body":"Draft roadmap for Q3.","owner_id":"user-1"}'
  '{"id":"doc-002","title":"Onboarding Notes","body":"Notes for new hires.","owner_id":"user-1"}'
  '{"id":"doc-003","title":"Design Review","body":"Notes from the design review.","owner_id":"user-2"}'
)

created=0
skipped=0

for doc in "${SAMPLE_DOCS[@]}"; do
  id=$(echo "$doc" | grep -oE '"id":"[^"]+"' | head -1 | cut -d'"' -f4)
  file="$DATA_DIR/$id.json"

  if [[ -f "$file" ]]; then
    skipped=$((skipped + 1))
    continue
  fi

  echo "$doc" > "$file"
  created=$((created + 1))
done

total=$((created + skipped))
echo "seed.sh: created=$created skipped=$skipped total=$total"
