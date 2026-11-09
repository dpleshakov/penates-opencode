# penates-opencode

A penates kit of OpenCode tools, published. Each directory under `items/` is
one item — the unit penates installs, updates, and removes. The kit is the
source of truth for its items; installed copies belong to penates and its
locks.

## Hard rules

- The `name` in `kit.yaml` never changes: it identifies every installed item.
- Item ids never change: a renamed id strands installed copies as orphans.
- The version in `item.yaml` bumps in the same change as the content.
- Content is English only and carries no machine paths.

## Authoring

- One capability per item; variants of one capability are separate items,
  replaced by remove + select in one apply.
- Versions follow semver: major — behavior change, minor — added capability,
  patch — wording. Add `CHANGELOG.md` to an item when a major update lands.
- `shared` in `kit.yaml` lists the target files section and json contributions
  may write to; add entries as the first need appears.
