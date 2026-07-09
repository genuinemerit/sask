# Legacy CLI Deepening Analysis (SPEC-034)

Deepens [port-source-inventory.md](port-source-inventory.md) and
[port-feature-analysis.md](port-feature-analysis.md)'s first-pass survey of
`saskan-app-alt`'s CLI, specifically for the CLI area, through `sask`'s
clean-room lens (DD-0021). **Recommend-only — ports no code.** Source: full
text of `saskan-app-alt/saskan/ui_cli/manage.py` and
`saskan-app-alt/saskan/ui_cli/commands/{greet,version,start,connect}.py`,
re-read fresh for this analysis.

## Why a second pass, and what's different this time

The first-pass port analysis already inventoried the CLI as "the only
genuinely working, tested interface" in the legacy app. That pass was a
whole-project survey; this one asks the specific question DD-0021 poses:
which parts are Typer *mechanics* worth reusing, and which parts are
*command logic* that must not be — because "prototype CLIs commonly bundle
logic into commands," which is exactly what this legacy CLI does.

## (a) Reusable Typer idiom and mechanics

1. **Required no-op root callback.** `manage.py` builds the app as
   `typer.Typer(help=help_text, no_args_is_help=True)` and registers a
   `@app.callback()` that does nothing but exist:
   ```python
   @app.callback()
   def main():
       """Saskan CLI."""
       pass
   ```
   This isn't decorative — `saskan-app-alt`'s own devlog (`feat(greeting).md`)
   records a real bug: `saskan hello` failed until this root callback was
   added. Typer's single-command-vs-multi-command registration behavior
   differs subtly enough that a bare `Typer()` with only subcommands
   registered can misbehave. **Recommend adopting this deliberately** in
   `sask`'s CLI rather than risking rediscovery of the same bug.

2. **Paired long/short options with example-invocation docstrings.** Every
   legacy command option follows `typer.Option(default, "--long", "-short",
   help=...)`, and every command docstring includes 2-3 example invocations
   (e.g. `connect.py`: `` `saskan connect` ``, `` `saskan connect --host
   localhost --port 8000` ``). This is good, cheap self-documentation —
   **recommend adopting** the pattern (paired flags + example docstrings) for
   all `sask` CLI commands.

3. **`raise typer.Exit(code)` for exit-code signaling.** `connect.py` uses
   this to translate a protocol reply code into the process exit code:
   `raise typer.Exit(reply_code)`. **Recommend adopting** this Typer-native
   mechanism wherever a `sask` command needs a non-zero exit (e.g. `config
   check` on an invalid config), instead of `sys.exit()`.

4. **A small aligned-output helper.** `version.py` defines a local
   `echo_dict(title: str, d: dict)` that prints a title line then each
   key/value pair aligned to a fixed column width. It's a reasonable, tiny,
   reusable idea — **recommend generalizing** it into a shared
   `sask/cli/formatting.py` helper available to all command groups, rather
   than each command inventing its own aligned-output logic.

5. **Command registration via `app.command("name")(function)`.** `manage.py`
   registers subcommands with `app.command("hello")(hello)` rather than
   `@app.command()` decorators directly on each function. Both are valid
   Typer idioms; this style keeps registration centralized in one file
   (`manage.py`) separate from each command's own module. **Recommend
   `@app.command()` decorators instead for `sask`** — with only 5 initial
   commands spread across a `commands/` subpackage (not centralized in one
   file the way legacy's 4 commands were), decorating in place is more
   readable and avoids a growing, easy-to-desync registration list in
   `cli/__init__.py`. This is the one idiom recommendation that changes
   rather than directly adopts the legacy style.

## (b) Legacy logic that must NOT be ported

Both non-trivial legacy commands bundle domain logic directly into the
command body — precisely the anti-pattern DD-0021's clean-room rule (“the CLI
is a MOUTH, not a BRAIN”) forbids:

- **`connect.py`** does all of the following inline, inside the `connect()`
  function itself, with no delegation to a separate function: translates the
  `--request` shorthand `"handshake"` into the full message name
  `"system.handshake.request"`; validates the `--protocol` value via
  `match_semver()` and silently falls back to a default if invalid; calls
  the network client; unpacks a `msg.reply.code` key out of the reply dict
  by mutating it (`del reply["msg.reply.code"]`); and finally formats and
  exits. This is a command function acting as its own business-logic layer —
  there is no clean-room function underneath it a web adapter (or anything
  else) could also call.
- **`version.py`** does its own JSON-decoding of `sys_info()`'s return value
  and hand-builds a `saskan_info` dict (protocol version, allowed client
  messages, language config) directly inside `version()`, with no separate,
  independently-callable function producing that dict.

**Neither command has a clean-room counterpart it delegates to** — the
command *is* the logic. `sask`'s CLI must not reproduce this shape: every
`sask` command wraps a call to an existing (or newly added) clean-room
engine/spine function and does no branching/lookup/transformation of its own
beyond argument parsing and output formatting, per DD-0021 and REQ-FUN-014's
explicit acceptance criteria.

## Inconsistency found — resolve, don't import

The four legacy commands are inconsistent in how they print output:
`greet.py` and `start.py` both instantiate `rich.Console()` and use
`console.print(...)`; `connect.py` and `version.py` use plain `typer.echo()`.
There's no technical reason for the split — it reads as incidental, not a
deliberate choice (neither `rich` command uses any `rich`-specific
formatting like styled text, tables, or panels; a `rich.Console().print()`
call with a plain string is functionally identical to `typer.echo()`).

**Recommendation: `sask`'s CLI should use `typer.echo()` uniformly.** None of
the 5 initial `sask` commands (`help`, `convert`, `asset list`, `asset info`,
`config check`, `logs query`) need `rich`'s actual differentiating features
(tables, styled/colored text, progress bars) — plain aligned text (via the
generalized `echo_dict` helper above) is sufficient. This also means **`sask`
does not need a new dependency on `rich`** at all for this round, keeping the
dependency surface smaller than the legacy project's.

## Cautionary note, not a finding to act on

Every legacy command module's header comment names a stale path: `connect.py`
is headed `# saskan/ui_cli/client/connect.py`, `version.py`
`# saskan/ui_cli/client/version.py`, `start.py` `# saskan/ui_cli/server/start.py`
— all reference a `ui_cli/client/`/`ui_cli/server/` split that was collapsed
into the current flat `ui_cli/commands/` at some point and never updated.
Noted only as a small cautionary example (keep header comments in sync with
actual layout, or omit path comments and let the filesystem be the source of
truth) — nothing to port or fix in the legacy repo itself.

## Recommendation summary

| Idiom | Adopt for `sask`? |
|---|---|
| Required no-op root `@app.callback()` | Yes, deliberately (avoids a known bug) |
| Paired long/short `typer.Option` + example-invocation docstrings | Yes |
| `raise typer.Exit(code)` for exit signaling | Yes |
| Generalized `echo_dict`-style aligned output helper | Yes, in `cli/formatting.py` |
| Command registration via `app.command("name")(fn)` | No — use `@app.command()` in place, better fit for a `commands/` subpackage |
| Command bodies containing domain logic (`connect.py`, `version.py`) | No — the exact anti-pattern to avoid |
| Mixed `rich`/`typer.echo()` output | No — `typer.echo()` uniformly, no `rich` dependency |
