# SourceGuard

Version-controlled rules, manifests, frozen metadata, checkpoints,
source indexes, code and tests for the SourceGuard pipeline.

## Frozen architecture

Container → Object → ReadingRegion → Anchor → ReadingLane →
RegionGrowing → Validation → Render

## Storage policy

Git stores:
- source code
- JSON / JSONL metadata
- rules
- manifests
- checkpoints
- tests
- documentation
- SHA256 references

Large source images, PDFs, video and other binary evidence remain
on Google Drive and are referenced by path + SHA256.

## GitHub owner

zvutuanlinh
