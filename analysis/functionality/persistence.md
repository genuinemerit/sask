# Persistence — the central divergence between the two functional areas

`sask-calendar`'s engine is, by design, a set of pure functions over a pulse
plus config, with no database (DD-0002 decision point 9: "Persistence is
tiered — config is truth; authored facts are the only persisted source of
truth; computed results are regenerable and at most cached"). `sask`'s
resource service has persistence too, but of a different, much smaller kind.
This document characterizes it precisely, since it's the single largest
architectural gap between the two functional areas and the place a merge
design most needs careful treatment rather than a folded-in summary.

## What is stored

Three things, all flat files on a local filesystem, none of them a database:

1. **Bearer tokens** — `tokens.toml`, default path
   `~/.config/sask/tokens.toml`, overridable via `SASK_TOKENS_PATH`
   (`auth.py:9,28`). Shape: `[[token]]` array-of-tables, each with at least
   `id` and `token` string fields (`auth.py:32` returns `data.get("token",
   [])`, i.e. an empty list if the key is absent — no error on a malformed
   structural shape here, only `tomllib`'s own parse errors and a bare
   `FileNotFoundError` on a missing file).
2. **The resource manifest** — `manifest.toml`, default path
   `./resources/manifest.toml` relative to the process's working directory,
   overridable via `SASK_MANIFEST_PATH` (`manifest.py:9,47`). Shape:
   `[[resource]]` array-of-tables, each with `kind`, `id`, `path` (resolved
   relative to the manifest file's own directory, not the working directory:
   `manifest.py:51,57`), and `content_type`.
3. **The resource payloads themselves** — arbitrary files referenced by the
   manifest's `path` field, currently one PNG, one JSON file, and two audio
   files under `resources/{images,json,audio}/`.

There is no database engine anywhere in this — no SQLite file, no schema, no
migrations. `sqlite` is listed among the tools available in the project's Nix
dev shell (`sask/CLAUDE.md`'s tool table), but grepping the actual source
tree turns up no use of it; its presence there corresponds to a documented
intention (see below), not a built feature.

## How it's stored and read

Both control files are parsed with the standard-library `tomllib` — no ORM,
no schema-validation library, no versioning of the file format itself. The
"schema" each loader expects is implicit in the dataclass it builds
(`ResourceEntry` in `manifest.py:12`) or the dict shape it assumes (`auth.py`
expects each token entry to have an `id` and `token` key, unchecked beyond
that).

The access pattern is the most consequential fact here: **both files are
fully reparsed from disk on every single request**, inside the route handler
itself (`app.py:53` calls `load_tokens(...)`, `app.py:68` calls
`load_manifest(...)`), not once at app-factory time. Concretely, a request
for one resource pays the full cost of parsing the entire tokens file and the
entire manifest file, builds a complete `dict[(kind,id), ResourceEntry]`,
and then uses exactly one entry from it. There is no caching, no
`functools.lru_cache`, no in-memory copy held across requests.

This buys one real property: editing `tokens.toml` or `manifest.toml` on disk
takes effect on the very next request, with no service restart. It costs a
full TOML-parse on every request regardless of catalog size, and it has no
concurrency story — a request arriving mid-write to either file could in
principle observe a partially-written file, though this has evidently never
been an observed problem at the project's actual usage scale (one developer,
files typically replaced atomically by whatever editor or deploy step writes
them).

There is no write path of any kind exposed by the service itself. Nothing
creates, updates, or deletes a token or a resource entry over HTTP; all
mutation is out-of-band — hand-editing a TOML file locally, or Ansible
copying a new `tokens.toml` onto the droplet during a deploy
(`analysis/deployment/`'s territory, not repeated here). This is a read-only
catalog lookup, not an asset-management API in the CRUD sense — there is no
"asset management" half to contrast against an "asset retrieval" half
within sask's own code; everything it has is retrieval.

## What was anticipated but never built

`decisions/0001-secrets-policy.toml`'s followups section names the gap
explicitly: "If token rotation matters later, consider sqlite-backed token
store as a future ADR." `docs/notes/lessons.md`'s hardening checklist
(section 4) repeats this under "Token rotation: Full redeploy required →
SQLite token store + CLI tool" as the named production-readiness step. This
was never implemented in the project's lifetime — it's a documented
direction, not dead code to read, and not something this analysis can
characterize further than "the project's own authors identified the same gap
this document is identifying, and didn't close it." Worth carrying into a
design session as a signal that the *intended* next step for token storage,
according to the original project, was a real database — just one that
hobby-scale usage never forced into existence.

## Contrast with `sask-calendar`'s current persistence model

`sask-calendar`'s `config_loader.load_config()` (`src/sask/config_loader.py:
950`) reads roughly two dozen TOML files once, validates every one of them
exhaustively at load time (exact-cardinality checks like "expected exactly 15
`[[body]]` entries," `config_loader.py:563-566`; type and range checks on
nearly every field; a `ConfigError` raised on any mismatch), and assembles the
result into one frozen `AppConfig` dataclass tree. This happens exactly once,
at `create_app()` time (`src/sask/web/__init__.py:25`), and the resulting
`AppConfig` instance is stashed in `app.config["SASK_CONFIG"]` for the
process's entire lifetime. Every subsequent request reads fields off that
one in-memory object — there is no per-request file I/O anywhere in
`sask-calendar`'s current request path, for config or anything else. This is
not an accident of implementation; it follows directly from the engine being
defined as pure functions over `(pulse, config)` — config is loaded once
because the engine's contract assumes it doesn't change during the process's
life.

## The precise divergence to carry forward

Two working, internally-consistent models, optimized for different things:

- **sask's model** (reload-per-request) optimizes for hot-reloadability of an
  externally-edited catalog at the cost of a full reparse on every hit and no
  caching.
- **sask-calendar's model** (load-once-at-startup) optimizes for zero
  per-request I/O and a single validated, typed config object, at the cost of
  requiring a process restart to pick up any config change.

If asset-serving merges into `sask-calendar`, whoever designs that merge
has to choose, deliberately, whether an asset catalog (and, if added, a
token store) becomes another section of the load-once `AppConfig` world —
consistent with everything else in the app, but losing the one property
sask's model had on purpose — or keeps its own separately-reloadable
lifecycle, becoming the one inconsistent I/O pattern in an otherwise
zero-I/O-per-request application. Neither this document nor either project's
existing code resolves that; see open-questions.md items 2 and 9.
