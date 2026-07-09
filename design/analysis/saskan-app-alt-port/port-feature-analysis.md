# `saskan-app-alt` Feature Analysis

Part of the [`saskan-app-alt` → `sask` port analysis](README.md). This file describes
what each **working** subsystem (per [source-inventory.md](source-inventory.md)) *does*
— request/command lifecycle, inputs/outputs, failure modes — as opposed to where its
files live. Stub subsystems (`core/`, `engine/`, `sims/`, `ui_pygame/`, `ui_pyside/`)
have no behavior to describe and are omitted here; see source-inventory.md for their
status.

## CLI

The only genuinely working, user-facing interface, and the most heavily tested part of
the app (`test_cli_connect.py`, `test_cli_hello.py`, `test_cli_version.py`, all via
`typer.testing.CliRunner`).

- `saskan/ui_cli/manage.py` builds the root Typer app and, as a side effect of import,
  calls `saskan.infra.log.logger.configure()` — merely importing the CLI module turns
  on logging configuration. Registers 4 commands and is the `pyproject.toml` entry
  point (`saskan = "saskan.ui_cli.manage:cli"`).
- **`saskan hello [name]`** (`commands/greet.py`) — prints "Hello {who}!" via `rich`.
  A smoke-test command with no domain purpose.
- **`saskan version`** (`commands/version.py`) — prints platform info plus protocol/
  i18n config, via `tools/utils/platform.py::sys_info()`.
- **`saskan start [--host] [--port]`** (`commands/start.py`) — thin wrapper that calls
  `infra.net.server.server.start_server()` and blocks in `serve_forever()`. This *is*
  "run the game server" — there is no separate server process/binary.
  Config precedence is CLI flags > env vars (`SASKAN_HOST`/`SASKAN_PORT`) > defaults.
- **`saskan connect [--host] [--port] [--protocol] [--request] [--id] [--timeout]`**
  (`commands/connect.py`) — the "game client" command. Defaults to sending a
  `system.handshake.request`; calls `client.send_msg_to_server()`; uses the reply's
  `msg.reply.code` (0=welcome, 1=error, 2=reject) as the **process exit code**; renders
  the reply via `localize.format_reply()` so the printed output is localized.

Exit codes observed/documented: `0` success, `10`/`11`/`12` for CLI-level errors (per
ADR-0004); the reply-code mapping above governs `connect`'s specific exit value. Two
rough edges confirmed in the real smoke-test transcript (`docs/design/test_results/
PR-2_smoke_tests.txt`): a protocol-mismatch test (`-s 3.4.5`) prints `[CLIENT] An error
occurred: 0` rather than a clean `REJECT` message, and the actual `--help` flag letters
(`-h/-p/-s/-r/-i/-t`) don't quite match the letter assignments described in ADR-0004 /
`feat(first_handshake).md` (protocol is `-s` in practice, not `-r`).

No connection exists from the CLI to `core`/`engine`/`sims`/`ui_pygame`/`ui_pyside` —
all are empty. The call graph terminates at `infra/net`, `infra/schema`,
`infra/config`, `infra/i18n`, `infra/log`, `tools/utils`.

## Handshake protocol

A real, working, tested **one-shot request/response** TCP protocol — explicitly *not*
a persistent multiplayer session, and self-described in the server module's own
docstring as a "skeleton" ("real game logic and error handling are omitted for
brevity").

- **Transport:** raw TCP sockets, NDJSON framing (one JSON object per line,
  `\n`-terminated, UTF-8), 8192-byte message cap.
- **Server** (`infra/net/server/server.py`): `IdleShutdownServer(socketserver.
  ThreadingMixIn, socketserver.TCPServer)`. A `ServerState` enum (`READY`/`DRAINING`/
  `STOPPED`) with a background `_idle_watchdog()` thread: `READY`→`DRAINING` after 10s
  of inactivity, `DRAINING`→`STOPPED` once active connections reach 0 and a 5s drain
  grace period elapses, then the server actually shuts down. Confirmed in the real
  smoke-test transcript: the running server auto-drains after **20.0s** of inactivity
  (a concrete number not stated in any ADR). `GameRequestHandler` implements strict
  one-exchange semantics: read exactly one NDJSON line, validate, reply exactly once,
  close the write half.
- **Session tokens** come from `secrets.token_urlsafe(32)` in `_register_session()`,
  stored only as an address in `server.clients` — explicitly a placeholder; the
  docstrings say "Future. ... In a real game, this step would involve authentication
  and player state setup," and no `Game` class exists to attach real state to.
- **Envelope shape:** `{id, ver(=1), name, ts(ISO8601), meta:{protocol}, payload,
  [audience], [severity]}`; `name` must match `^[a-z0-9]+(\.[a-z0-9_-]+)+$`.
- **Exactly 3 allowed message names:** `system.handshake.request` (client→server),
  `system.welcome` / `system.reject` (server→client). Handshake payload:
  `{client_version, capabilities: []}`.
- **Server-side validation pipeline:** (1) allow-list check on `name`; (2)
  protocol-version check on `meta.protocol` against `SUPPORTED_PROTOCOLS = ["0.1.0"]`;
  (3) full JSON-Schema (Draft 2020-12) validation of envelope then payload. If the
  server is `DRAINING`/`STOPPED`, it rejects with `server_not_ready` without reading
  the incoming body at all.
- **Reject reasons:** `protocol_version_unsupported`, `server_not_ready`,
  `invalid_contract`.
- **Welcome payload:** `{server_version, session_id, motd, i18n_id,
  accepted_capabilities}` — `accepted_capabilities` is currently just `{"welcome"}`.
- **Client** (`infra/net/client/client.py::send_msg_to_server`): opens a blocking
  socket, sends the request, `shutdown(SHUT_WR)`, reads exactly one reply line,
  dispatches on `name` into a typed DTO (or `"err.unknown_reply"`); attaches the
  synthetic `msg.reply.code` used as the CLI's exit code.
  `ConnectionRefusedError` is caught specially → `"err.connection_refused"`.

**What this is not:** there is no persistent session across multiple messages, no
subscriptions/groups/broadcast, no durable message queue, and no real authentication.
Code comments explicitly mark the whole thing as "PR-2 scope." The richer behaviors
described in later ADRs (multi-client addressing, message retention) are documented
intent, not implemented reality — see [design-components-analysis.md](design-components-analysis.md).

**Test coverage:** `test_client_unit.py` (NDJSON framing over `socket.socketpair()`),
`test_server_integration.py` (real-socket round trip for welcome, plus a
DRAINING→reject path via monkeypatched timeouts), `test_validator.py` (allow-list
checks), `test_cli_connect.py` (asserts exact localized output strings in both
locales).

## i18n

Not GNU gettext — a bespoke, lightweight lookup table, "gettext-inspired in spirit"
(message-ID keys instead of raw source strings, a locale-directory-per-language
layout, env-var-driven active locale with fallback) but with no `.po`/`.mo` files, no
`msgid`/`msgstr`, no `xgettext` extraction step.

- **Locales:** `en-US` (default) and `es-ES`, ~18 keys each, in
  `saskan/data/locales/{locale}/messages.yaml`, loaded via `importlib.resources`
  (works whether packaged or run from source).
- **Selection:** the `SASKAN_LANG` env var only, validated against
  `services.SUPPORTED_LANGS`. This is **process-wide**, not per-request/per-session —
  the server renders its own strings (MOTD, welcome, reject) using its own process's
  `SASKAN_LANG`, independent of whatever the client's is.
- **Two-tier design:**
  1. `infra/i18n/lookup.py::get_text()` — raw key→string lookup with a **4-level
     fallback chain**: active locale → `en-US` → caller-supplied fallback → the raw
     `i18n_id` string itself. `_load_bundle()` is `lru_cache`d.
  2. `infra/i18n/localize.py` — a keymap-based layer (`i18n_keymap.json`) that
     converts internal Python dict field names (e.g. `session_id`, `reply_code`) into
     canonical dotted i18n IDs via `convert_tag()`, then `format_reply(reply: dict) ->
     str` renders an entire server-reply dict into a multi-line human-readable string
     (list-valued fields get special handling, e.g. `accepted_capabilities` →
     `"[cap.chat, cap.assets]"`).
- **Namespace taxonomy:** `system.*`, `msg.*`, `ui.*`, `err.*`, `log.*` — only the
  first four are populated in the actual YAML; `log.*` is planned but unused.
- **Integration reality check:** despite `localize.py`'s docstring claiming support
  for "ui_pyside, ui_cli or ui_pygame modules," **only `ui_cli/commands/connect.py`
  actually calls `format_reply()`** — the other two UIs don't exist. The server calls
  `lookup.get_text()` directly (bypassing the keymap layer) exactly once, for its
  startup MOTD banner.
- **Coverage is currently 100% protocol/handshake vocabulary** — zero gameplay/menu
  text exists because no such UI exists.
- **Runtime-proven, not just designed:** the real smoke-test transcript shows
  `SASKAN_LANG=es-ES` producing `"Bienvenido a las Tierras Saskan"` in place of
  `"Welcome to the Saskan Lands"`, and falling back cleanly to English when the env
  var is unset.
- **Known bugs:** the en-US/es-ES key-name mismatch noted in
  [source-inventory.md](source-inventory.md) (`msg.reason.text` vs `msg.reason.code`);
  and an internal inconsistency between the authoring guide (says locale files are
  JSON) and the actual implementation checklist (says YAML) — the real files are
  YAML, the guide is wrong. A `feat(first_splash).md` refactor log entry documents a
  real bug hunt for code that mistakenly referenced the invalid locale tag `en-EN`
  instead of `en-US`.
- **Tests:** `tests/test_lookup.py` (9 tests, every fallback branch), plus end-to-end
  assertions in `tests/test_cli_connect.py`.

## Config

`infra/config/net.py` and `infra/config/services.py` are small constants modules, the
single source of truth most other modules import from: `PROTOCOL_VERSION`,
`ALLOWED_MESSAGE_NAMES`, `REJECTION_REASONS`, timeouts (`SERVER_TIMEOUT`,
`IDLE_POLL_INTERVAL`, `DRAIN_GRACE_PERIOD`), `MAX_MESSAGE_SIZE`, `DEFAULT_LANG`/
`SUPPORTED_LANGS`, all overridable via `SASKAN_*` env vars. No validation framework —
just module-level constants, some with env-var overrides applied at import time (this
is also where the stray debug `print()` noted in source-inventory.md fires).

## Logging

`infra/log/logger.py` provides structured JSON logging (`JSONFormatter`,
`LevelRangeFilter`, a custom TRACE level below DEBUG) plus `configure()`/
`get_logger()`/`bind_context()`. `infra/log/events.py` layers semantic event helpers
on top (`ready()`, `conn_open()`, `hello()`, `draining_start()`, `conn_close()`,
`msg_recv()`/`msg_sent()`, `cmd()`, `tick()`, `state_snap()`, `asset_fetch()`,
`ai_gen()`, `io_warn()`/`io_err()`). Actually invoked from only two places
(`ui_cli/manage.py`'s import-time `configure()` call, and a handful of `ev.*` calls in
`server.py`) — most of the event-helper surface (`tick`, `state_snap`, `ai_gen`,
`asset_fetch`) has zero callers, built ahead of the game-loop/AI-generation features
that were never built. No dedicated test file exists for this subsystem. A newer,
more mature logging design exists only as a Draft ADR (ADR-0017) describing a target
state — the actual code was never migrated to it (confirmed: the real log lines in
the smoke-test transcript use a nested `message` string with an `event` key, not
ADR-0017's mandated top-level `evt` field).

## Asset pipeline

The most recently active part of the whole repository (its last 3 commits are asset-
pipeline work), and a genuinely working, actively-used tool — but see the
[convergent-prior-art note in source-inventory.md](source-inventory.md#convergent-prior-art--verify-before-porting)
before treating it as something to port.

- **Two-tier storage:** `saskan/assets/local/` (raw/unpublished source images) →
  `saskan/assets/v0/images/` (published, versioned output). The version segment
  (`v0`) comes from `SASKAN_ASSETS_VERSION`, defaulting to `"v0"` — a whole-tree
  version, not per-asset semver.
- **Build tool** (`tools/studio/build_assets.py::build_splash()`): takes one source
  image, produces 4 size variants (full/half/quarter/thumbnail), re-encodes to WebP
  under a strict ≤1 MiB budget per file (`_webp_save_under_1mb()` iteratively lowers
  quality 85→50 in steps of 5, then a last-resort 40, raising `RuntimeError` if still
  too big), enforces/warns on 16:9 aspect, embeds an 8-hex-char SHA-256 prefix into
  each filename for cache-busting, and updates a flat `{logical_id: CDN_url}` JSON
  manifest (`saskantinon.manifest.json`). Invoked manually, e.g. `poetry run python
  saskan/tools/studio/build_assets.py --name SmokingHouse.splash.webp`.
  `TILE_W_H`/`SPRITE_SIZES` constants exist but are never used by any function —
  sprite/tileset asset-building is declared but dead; only the splash path is wired
  end-to-end.
- **Deploy step** (`infra/deploy/push-assets.sh`): validates no asset exceeds 1 MiB,
  cross-checks every manifest URL exists locally, `rsync`s to a **separate remote
  nginx host** over SSH (excluding `local/` and `v0/thumbs/`), reloads nginx, does
  HEAD-request smoke checks. Supports `DRY_RUN=1`.
- **Serving model:** static files served directly by nginx from the remote host
  (`saskan.conf.example`: serves `/saskan/assets/`, 60s cache for `manifest.json`,
  1-year immutable cache for content-hashed filenames, CORS `*`). This is a
  fundamentally different model from a Flask route reading a config-driven catalog.
- **Relation to `draw/huge_barbican.py`:** no automated connection — a human runs the
  DALL-E script, manually places output under `assets/local/`, then manually runs
  `build_assets.py`. Two manual steps, not a pipeline. The `ai_gen()` logging hook
  that appears purpose-built for this is never actually called by either script.
