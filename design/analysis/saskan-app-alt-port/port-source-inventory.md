# `saskan-app-alt` Source Inventory

Part of the [`saskan-app-alt` → `sask` port analysis](README.md). This file answers
"what does the legacy repository actually contain" — a factual inventory of code,
docs, and process machinery, scored by maturity. Behavior (what the working parts
*do*) is covered separately in [feature-analysis.md](feature-analysis.md); ADR-level
design evaluation is in [design-components-analysis.md](design-components-analysis.md).

**Scope note:** `docs/design/Big_Picture/` is excluded from this entire analysis — it
is a separate set of forward-looking design notes for `sask`'s own future, unrelated
to what `saskan-app-alt` implements, and is being carried over to `sask` unchanged
elsewhere. `docs/reference/` (glossary, Python/SQLite/math cheatsheets, macOS notes,
etc.) is a generic personal knowledge base, not project-specific design — noted below
for completeness but not analyzed further.

## Top-level layout

| Path | Contents | Relevance |
|---|---|---|
| `saskan/` | The installable package (`saskan = "saskan.ui_cli.manage:cli"` entry point) | Primary subject of this inventory |
| `draw/` | One standalone DALL-E art-generation script | See [Non-package content](#non-package-content) |
| `docs/architecture/` | 17 ADRs + 6 architecture docs | Covered in [design-components-analysis.md](design-components-analysis.md) |
| `docs/design/` | 3 feature-design docs, 1 test-results transcript, `Big_Picture/` (excluded), `design_notes/refactoring_notes.md` (the governing brief) | Covered in [design-components-analysis.md](design-components-analysis.md) |
| `docs/reference/` | ~60 generic cheatsheet/reference files (glossary, Python, SQLite, math/physics, macOS) | Not project-specific; not analyzed further |
| `tests/` | 8 pytest files | See [feature-analysis.md](feature-analysis.md) for what they prove |
| `scripts/` | 4 repo-admin/ops shell scripts | Ops tooling, not app features |
| `.github/` | 8 workflows, issue/PR templates, CODEOWNERS, FUNDING.yml | Covered in [design-components-analysis.md](design-components-analysis.md) — this is the machinery `refactoring_notes.md` says to drop |
| Root docs | `README.md`, `CHANGELOG.md`, `AUTHORS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `RELEASE.md`, `.pre-commit-config.yaml`, `.importlinter`, `Makefile` | Covered in [design-components-analysis.md](design-components-analysis.md) |

## `saskan/` package inventory

The directory tree under `saskan/` (`core/`, `data/`, `engine/`, `infra/`, `sims/`,
`tools/`, `ui_cli/`, `ui_pygame/`, `ui_pyside/`) looks like a fully-fledged game
engine. Git history and direct file reads say otherwise: of 297 total commits in the
repo, `core/`, `engine/`, `sims/`, `ui_pygame/`, and `ui_pyside/` each have **exactly
1** (the initial scaffold), and each is a single 0-byte `__init__.py`, identical on
every branch. Confirmed directly:

```text
core/__init__.py        0 bytes
engine/__init__.py      0 bytes
sims/__init__.py        0 bytes
ui_pygame/__init__.py   0 bytes
ui_pyside/__init__.py   0 bytes
```

No domain/game-model class (`Player`, `Character`, `World`, `Hex`, `Tile`, `Map`,
`Item`, `Game`, ...) exists anywhere in the codebase. Across the entire `saskan/`
package there are only 21 classes total, and every one of them is infrastructure/
protocol plumbing (logging, TCP handshake, JSON-Schema DTOs) — none is a domain model.

| Subsystem | Status | Key files | Notes |
|---|---|---|---|
| `saskan/core/` | **STUB** (empty) | `core/__init__.py` | Intended home for hex-grid/axial-cube math per ADR-0001/0005/0006. Nothing to port. |
| `saskan/engine/` | **STUB** (empty) | `engine/__init__.py` | Intended turn engine + worldgen per ADR-0002/0007. Only trace anywhere: a commented-out `# self.server.game = Game()  # Future` at `infra/net/server/server.py:239`. |
| `saskan/sims/` | **STUB** (empty) | `sims/__init__.py` | No content, no references elsewhere. |
| `saskan/ui_pygame/` | **STUB** (empty) | `ui_pygame/__init__.py` | ADR-0016 describes an intended render/input-only role; `pygame` is an optional `pyproject.toml` extra but is imported in zero `.py` files. |
| `saskan/ui_pyside/` | **STUB** (empty) | `ui_pyside/__init__.py` | ADR-0016 describes an intended menus/dialogs/i18n-surface role; `PySide`/`PySide6` isn't even a declared dependency — referenced only in a docstring comment in `localize.py`. |
| `saskan/ui_cli/` | **WORKING** — most heavily tested part of the app | `ui_cli/manage.py`; `ui_cli/commands/{greet,version,start,connect}.py` | Typer CLI, 4 commands. See [feature-analysis.md § CLI](feature-analysis.md#cli). |
| `saskan/infra/net/` | **WORKING**, self-described as a "skeleton" | `infra/net/client/client.py`; `infra/net/server/server.py` | TCP+NDJSON one-shot handshake protocol. See [feature-analysis.md § Handshake protocol](feature-analysis.md#handshake-protocol). |
| `saskan/infra/schema/` | **WORKING** (protocol schemas) + **DEAD** (manifest schemas) | `dto.py`, `convert.py`, `validator.py`, `types.py`, `*.schema.json` | The envelope/handshake/welcome/reject schemas are live and validated. `manifest_dto.py`/`manifest_convert.py`/`manifest.schema.json` are a richer, unused duplicate — see [Dead/superseded code](#deadsuperseded-code-not-to-be-ported). |
| `saskan/infra/i18n/` | **WORKING**, runtime-proven | `infra/i18n/lookup.py`, `infra/i18n/localize.py` | See [feature-analysis.md § i18n](feature-analysis.md#i18n). |
| `saskan/data/locales/` | **WORKING** (data only, not code) | `en-US/messages.yaml`, `es-ES/messages.yaml`, `i18n_keymap.json` | 18 keys per locale. One real bug: en-US has `msg.reason.text` (line 7) where es-ES has `msg.reason.code` instead — a key-name mismatch between the two files. |
| `saskan/infra/config/` | **WORKING** | `infra/config/net.py`, `infra/config/services.py` | Protocol/network constants, single source of truth for most other modules. `net.py:32` has a stray `print(f"Configuring network on {HOST}:{PORT}")` at *module import time* — a debug leftover, not a feature. |
| `saskan/infra/log/` | **WORKING**, under-utilized | `infra/log/logger.py`, `infra/log/events.py` | Structured JSON logging, custom TRACE level, redaction. `events.py`'s `tick()`, `state_snap()`, `ai_gen()`, `asset_fetch()` helpers have zero callers anywhere — built ahead of features (game loop, AI-art pipeline) that don't exist. No dedicated test file. |
| `saskan/infra/nginx/`, `saskan/infra/deploy/` | **WORKING** ops tooling | `infra/nginx/saskan.conf.example`, `infra/deploy/push-assets.sh` | Reverse-proxy config + rsync deploy script for a live-but-minor external host (nginx readme calls it "a little-used static toy gaming website"). Entirely decoupled from the Python app. |
| `saskan/tools/studio/build_assets.py` | **WORKING**, most recently active code in the repo | `tools/studio/build_assets.py` | WebP variant builder. See [feature-analysis.md § Asset pipeline](feature-analysis.md#asset-pipeline). **See the convergent-prior-art note below before treating this as a porting candidate.** |
| `saskan/tools/utils/{match_semver,stamps,platform}.py`, `saskan/tools/validate_json.py` | **WORKING**, small and correct | as named | Semver check, ISO timestamp, host/platform sysinfo, JSON-Schema CLI validator. **See the convergent-prior-art note below before treating these as porting candidates.** |
| `draw/huge_barbican.py` | **WORKING**, standalone | `draw/huge_barbican.py` | DALL-E/OpenAI concept-art generator; no `saskan.*` imports; fully manual, fully decoupled from the asset pipeline above. Needs a paid `OPENAI_API_KEY`. |

## Dead/superseded code (not to be ported)

Confirmed by direct read, explicitly flagged so a future porting pass doesn't
resurrect these:

- **`saskan/tools/snips/assets_snip.py`** — an earlier, abandoned draft of
  `build_assets.py`. Contains a real bug: `_save_variant()`/`_copy_or_reencode_1x()`
  reference a module-level name `OUT` that is never defined (only `IMAGES_OUT`/
  `THUMBS_OUT` exist) — calling either raises `NameError`. Also has noisy
  import-time `print()` debug statements and an ad-hoc `_run_inline_tests()` never
  wired into pytest.
- **`saskan/infra/schema/manifest_dto.py` / `manifest_convert.py` /
  `manifest.schema.json`** — a fully-built, JSON-Schema-validated asset-manifest
  DTO layer (models `asset_type`/`purpose`/`variants{format,mime,url,size_bytes,
  hash,sprite,tileset,cache,license,source}`) with **zero callers anywhere**. The
  real manifest writer (`build_assets.py`) hand-rolls a much simpler flat
  `{id: url}` dict that doesn't conform to this schema at all.
- **`saskan/tools/utils/__init.py__`** — misnamed (should be `__init__.py`).
  Harmless under Python 3 namespace packages, but a clear leftover typo.
- **Stray unrelated media** under `saskan/assets/local/`: a Kdenlive video-editing
  project (`video.kdenlive` + `.srt`), `test-video.mp4`, `test_audio.mp3` — no
  referencing code anywhere.
- **Stale header comments** in `ui_cli/commands/{connect,version,start}.py`
  reference a `ui_cli/client/`/`ui_cli/server/` split that no longer exists
  (collapsed into flat `ui_cli/commands/`) — cosmetic, but could mislead a porter
  searching by the path named in the comment rather than the real one.

## Declared-but-unused dependencies

Cross-referencing every "core runtime" dependency in `pyproject.toml` against actual
imports in `saskan/` and `draw/` (excluding `__pycache__`): **`SQLAlchemy`,
`networkx`, `beautifulsoup4`, `Levenshtein`, `numbers-parser`, `twisted`, `psycopg`,
`matplotlib`, `nltk`, `pandas` are declared but never imported anywhere.** Notably,
`twisted` is declared despite the server actually using stdlib `socketserver` — a
documented, deliberate choice (see [design-components-analysis.md](design-components-analysis.md)),
making `twisted` an orphaned exploratory dependency. Do not treat any of these as
evidence of real functionality when scoping the port; they are aspirational/leftover.

Confirmed used: `pyyaml` (i18n), `jsonschema` (schema/validator), `rich` + `typer`
(CLI), `psutil` (platform.py), `pillow` (build_assets.py), `openai` (huge_barbican.py
only). `pygame` appears in exactly one file (a comment); `PySide`/`PySide6` isn't
declared at all.

## Convergent prior art — verify before porting

**`sask` already contains code that closely resembles several `saskan-app-alt`
utilities, but it did *not* come from `saskan-app-alt`.** Direct diff confirms:

| `saskan-app-alt` | `sask` | Resemblance |
|---|---|---|
| `saskan/tools/utils/match_semver.py` | `tools/helpers/match_semver.py` | Same regex, same function purpose; `sask`'s version adds type hints, a doctest, and a named compiled pattern |
| `saskan/tools/utils/stamps.py` | `tools/helpers/stamps.py` | Same single function (`create_iso_timestamp`), same underlying call |
| `saskan/tools/utils/platform.py` | `tools/helpers/host_info.py` | Same `sys_info()` purpose/field set; `sask`'s version is renamed (was shadowing stdlib `platform`), returns a `dict` instead of a JSON string, and logs failures instead of swallowing them |
| `saskan/tools/validate_json.py` | `tools/helpers/validate_json.py` | Same purpose (validate JSON against a Draft 2020-12 schema from the CLI); `sask`'s version adds `argparse`, proper exit codes, and error handling |
| `saskan/tools/studio/build_assets.py` | `tools/studio/build_assets.py` | Same purpose (WebP variant generation under a 1 MiB budget, content-hash cache-busting, flat manifest); `sask`'s version points at its own env-var names and notes in-code that the live app actually serves assets from a config-driven catalog, not this manifest |

This looks like direct lineage. **It is not.** `sask`'s own design docs are explicit
and unambiguous on this point — `design/decisions/dd-0016-asset-retrieval.toml`:

> "The sask-proto sibling project built a small authenticated Flask resource server
> (resource retrieval by kind/id, returning bytes). The next phase of sask work ports
> an improved asset-retrieval capability into the active codebase..."

and `docs/devlog.md` (2026-06-25 entry) describes "a full read-and-rewrite pass over
`tools/candidates/` (8 files inherited from the sibling `sask[-proto]` project, not
wired into this app)". `sask-proto` is named 7 times across `sask`'s design docs,
devlog, and acceptance tests; **`saskan-app-alt` is named zero times anywhere in
`sask`**. `sask-proto` itself is not present on this machine — per the devlog, it was
"archived on Dropbox" once superseded.

**Conclusion:** the resemblance is real (confirmed by diff) but the attributed
lineage is a separate, third project (`sask-proto`), not `saskan-app-alt`. Whether
`saskan-app-alt` and `sask-proto` share a common ancestor further back (e.g. a
personal utility-snippet habit reused across the author's own hobby projects) cannot
be determined from what's on this machine, and isn't decision-relevant. **What is
decision-relevant: `sask` already has equivalent, already-tested functionality for
these five files' purposes, built to a higher standard than the `saskan-app-alt`
originals (type hints, docstrings, `tests/test_{host_info,match_semver,stamps,
validate_json}.py`).** These should not be re-ported from `saskan-app-alt` — see
[porting-roadmap.md § Port Phase 0](porting-roadmap.md#port-phase-0--legacy-scope-closure).

## Non-package content

- **`docs/reference/`** — roughly 60 files: a glossary (ADR, DSL, DTO, HUD, IPC, MVP,
  MVVM, NDJSON, PR, QoS, RNG, RPC, TTL, URN, i18n, idempotent, semver, ...), Python
  tips (mypy, pytest, monkeypatch, logging, traceback handling), SQLite tips, math/
  physics reference notes (ellipsoid volume, collision, pitch/yaw/roll), macOS
  quirks, build/release/deploy reference. This is a personal knowledge base the
  author built up alongside the project, not project-specific design — no further
  action proposed beyond noting it exists (it is not carried forward as part of this
  port; if any of it is wanted later, that is a separate, explicit decision, not an
  automatic one).
- **`saskan/assets/local/` vs `saskan/assets/v0/`** — a two-tier asset-authoring
  scheme: `local/` holds raw/unpublished source images (plus the unrelated stray
  media noted above); `v0/images/` holds the published, versioned, content-hashed
  output of `build_assets.py`. See [feature-analysis.md § Asset pipeline](feature-analysis.md#asset-pipeline).
- **`scripts/`** — `backup_certbots.sh`, `graphic_tweaks.sh`, `make_tree.sh`,
  `use_archive_repo_on_do.sh` — repo-admin/ops scripts, not app features.
