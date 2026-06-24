# Open questions — for the design session, not resolved here

These are choices, not facts, and several can't be settled by reading more
code. They're listed for the off-line design session this analysis feeds;
none are answered or recommended here, deliberately — each is presented with
the relevant context on both sides where there are sides to present.

## 1. What kind of consumer is the asset service for?

DD-0003 shaped the message-unit seam so that "an HTTP API, and later the RPG
engine, can wrap the same calls without changing the engine (API-ready, not
API-now)" — naming a future consumer without building it. Separately, sask's
own retrospective (`docs/notes/lessons.md` section 4) frames its
resource-server pattern as "the resource-delivery layer of a game," serving
"the client (desktop) [that] holds a session token." Is a ported asset
service the API-ready consumer DD-0003 left room for, a different thing
entirely, or does answering this question depend on decisions about the RPG
engine that haven't been made yet?

## 2. Does the asset catalog join `AppConfig`, or stay separate?

`config_loader.py` validates every config file exhaustively and loads all of
it once, at `create_app()` time, into one frozen `AppConfig`. sask's manifest
loader does neither of those things today. If an asset catalog is ported,
does it become a new `AppConfig` field — subject to the same load-once,
validate-exactly discipline as every other config file — or does it remain
a separately-loaded, separately-lifecycled concern that `AppConfig` doesn't
know about? See `integration-seams.md` §1 and `persistence.md`.

## 3. Does asset access need authentication in the merged app at all?

DD-0014 already decided the calendar UI itself is public, no authentication,
"deferred but explicitly not designed out." Does that deferral extend to
asset-serving, or does asset-serving have a different audience (a
future desktop/game client, per the lessons.md framing) that needs its own
auth answer on a different timeline than the rest of the app?

## 4. If auth is needed, what shape?

sask's auth model is a flat, undifferentiated list of shared bearer tokens —
no scope, no expiry, no rotation without a redeploy. Its own author flagged
a SQLite-backed token store as "the right next step" and never built it (see
`persistence.md`). Is the flat-list model an acceptable starting point for a
port, or does the previously-deferred token store get built now instead of
later? This question is downstream of question 3 — it only matters if some
form of auth is needed at all.

## 5. Is "kind" a closed code-level enum, or config data?

sask's `_SUPPORTED_KINDS` is a hardcoded `frozenset` in `app.py`; adding a
fourth kind requires a code change. `sask-calendar`'s established commitment
(DD-0002 point 1, REQ-OPS-006) is that domain data lives in config, not
hardcoded in functions. Does a ported asset kind list follow that
commitment, and if so, does "kind" stay a meaningful closed concept at all,
or does it dissolve into something more like content-type plus a free-form
category tag?

## 6. What would the merged app's asset catalog actually contain?

sask's catalog is generic placeholder content (a splash image, one JSON
scenario, two audio files) with no relationship to `sask-calendar`'s actual
domain. `sask-calendar` already has an adjacent, informally-similar
capability: `web/routes.py`'s `/ephemeris/download` route generates and
serves a JSON file on demand, with its own filename/Content-Disposition
logic, entirely separate from anything manifest-driven. Does "asset
serving" mean a genuinely new asset catalog (e.g. portrait art, sky-scene
renders) for a future consumer, and if so does it overlap conceptually with
what `/ephemeris/download` already does ad hoc, or are these unrelated?

## 7. Where does the serialization-helper pattern live, and what is it called?

Both projects have a module literally named "translator(s)" doing different
jobs: sask's `translators.py` does wire serialization (JSON encode, raw file
bytes); `sask-calendar`'s `web/translator.py` does message-unit-to-view-model
conversion for Jinja templates. If sask's pattern (explicit functions, no
auto-serializer, one place to look when a response body is wrong) is reused
in any form, where does it live, and what does it get called, given the name
is already taken for a different purpose in this codebase?

## 8. What's the error-response convention for a non-browser consumer?

sask answers every failure as a JSON body with a status code aimed at a
program. `sask-calendar`'s current routes answer failures as a plain string
rendered into an HTML template, aimed at a person. If ported asset-serving
needs its own JSON error convention, is this the first JSON-error precedent
in this codebase, or does something comparable already exist elsewhere that
should be reused instead of invented fresh?

## 9. Does "hot-reload without restart" remain a requirement?

sask's reload-per-request pattern exists specifically so editing
`tokens.toml`/`manifest.toml` takes effect without restarting the service.
`sask-calendar` has never had this capability for any of its own config —
every other config change today requires a restart. Is hot-reload a
requirement worth preserving for an asset catalog specifically, or is
restart-to-reload an acceptable, already-precedented cost to pay for
consistency with how every other config file in this app behaves? See
`persistence.md`'s closing section.

## 10. Does "asset management" need to exist as a concept distinct from "asset retrieval"?

sask's own code has no management half at all — there is no create/update/
delete path for a token or a resource entry over HTTP; every mutation
happens by hand-editing a file or via a deploy step. The user's own framing
of this task asked whether sensible sub-boundaries exist (e.g. "between
asset management and asset retrieval") — and the answer, on sask's
side, is that the question doesn't currently arise because management
doesn't exist as code at all, only as an out-of-band file edit. Whether a
merged app needs to build a management capability that sask never had, or
whether out-of-band file editing remains the intended mechanism going
forward, is unresolved.
