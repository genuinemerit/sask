# Functional architecture — sask's resource service, end to end

This describes how `sask`'s resource-serving code actually behaves, as built
— not as a recommendation for how a ported version should behave. All paths
are relative to `~/Code/sask` unless noted.

## The whole service is four small modules

`src/sask/app.py` (91 lines), `auth.py` (69 lines), `manifest.py` (62 lines),
`translators.py` (48 lines). There is no ORM, no schema migration tool, no
background worker, no caching layer. This is worth stating plainly because
it sets the scale against which every divergence below should be read: the
thing being characterized is small enough to read in full in a few minutes,
and most of its "architecture" is really just a small number of explicit
decisions about where each concern lives.

## Request lifecycle for `/resource/<kind>/<resource_id>`

1. `extract_bearer_token` (`auth.py:35`) parses the `Authorization` header;
   anything that isn't exactly `Bearer <token>` (case-insensitive scheme)
   returns `None`.
2. `load_tokens` (`auth.py:12`) re-reads and re-parses the entire tokens TOML
   file from disk — on this request, not at startup. Default path is
   `~/.config/sask/tokens.toml`, overridable via `SASK_TOKENS_PATH`.
3. `is_valid_token` (`auth.py:53`) does an O(n) scan over the token list
   using `hmac.compare_digest` per entry — timing-safe per comparison, but
   the scan itself leaks which-entry-matched only by total time, not by
   per-entry instrumentation, and n is small enough (one token, in practice)
   that this has never needed to be revisited.
4. On auth failure: `401` with a JSON body `{"error": "Unauthorized"}` via
   `translators.error_to_json`.
5. On auth success: `kind` is checked against `_SUPPORTED_KINDS =
   frozenset({"image", "json", "audio"})` (`app.py:12`) — anything else is a
   `404`, not a `400`; an unsupported kind is modeled as "doesn't exist," not
   "malformed request."
6. `load_manifest` (`manifest.py:29`) re-reads and re-parses the entire
   manifest TOML file from disk — again, on this request, not at startup.
   Default path is `./resources/manifest.toml`, overridable via
   `SASK_MANIFEST_PATH`. It returns a `dict[(kind, id), ResourceEntry]`; the
   full manifest is rebuilt every time even though the handler only needs one
   entry.
7. `(kind, resource_id)` lookup miss → `404` with a JSON error naming the
   missing kind/id pair.
8. `translators.resource_to_bytes` (`translators.py:33`) reads the file named
   in the matched `ResourceEntry.path` and returns raw bytes; a missing file
   on disk (manifest says it should exist, but it doesn't) is caught
   separately and also turns into a `404`, distinct in wording from "unknown
   resource id" even though both are 404s.
9. Success: `200`, `Content-Type` set from `ResourceEntry.content_type` (a
   manifest field, not derived from the file extension or sniffed content),
   body is the raw bytes.

`/health` bypasses all of this — no auth, no config, no file I/O — and
already has a structurally identical counterpart in `sask-calendar`'s own
`src/sask/web/routes.py:150` (added independently, for DD-0014's acceptance
checks). There's nothing to port for health; the two projects converged on
the same shape on their own.

## The kind/id addressing model

A resource is addressed by two independent strings: `kind` (a closed set,
enforced in code, currently `image`/`json`/`audio`) and `id` (an open string,
unique only within a kind, enforced implicitly by the manifest being a dict
keyed on `(kind, id)`). `content_type` is a third, independently-set field —
the manifest entry for `ambient-video.mp4` has `kind = "audio"` but
`content_type = "video/mp4"` (`resources/manifest.toml:23-26`), which the
project's own PR-002 notes call out deliberately: "Content-Type should be
derived from the manifest entry, not from the file extension alone." Kind,
in other words, is a routing/grouping concept; content-type is a wire-format
concept; and the two are allowed to disagree about what the same file "is."

A single kind can hold multiple ids (the two `audio` entries are the
project's own demonstration of this), but there is no notion of a resource
having multiple representations under one id, no versioning, and no listing
endpoint — a client has to already know a valid `(kind, id)` pair; nothing in
the service exposes the manifest's contents as a directory.

## The auth model

One global, undifferentiated trust tier: a request either presents a token
that matches some entry in the tokens file, or it doesn't. There is no
per-token scope (e.g. "this token can only fetch `audio` kind"), no expiry
field, no issuance or revocation endpoint — revocation means editing the
tokens file by hand. `hmac.compare_digest` (`auth.py:66`) is used correctly
for the one comparison that matters (the token value itself); this is
explicitly called out in `docs/notes/lessons.md` as "a one-line decision but
the right one." The auth check is entirely orthogonal to the resource lookup
— a request can be unauthenticated-and-would-have-hit-a-real-resource, or
authenticated-and-asking-for-nothing-real, and the code path for each is
independent (auth is checked first, unconditionally, before kind/id are even
inspected).

## The error model

Every failure path returns a JSON body shaped `{"error": "<message>"}` via
`translators.error_to_json`, with a status code that distinguishes
"unauthenticated" (401) from "not found" (404, used for both "unknown kind,"
"unknown id," and "file present in manifest but missing on disk" — three
different failure causes collapsed into one status code with three different
message strings). This is a machine-readable error convention aimed at a
non-browser client.

`sask-calendar`'s current routes (`src/sask/web/routes.py`) have no
JSON-error convention at all — error conditions (e.g. an unparseable `pulse`
query parameter) are caught and passed into `render_template(...,
error=error, ...)` as a plain string, to be displayed inline in an HTML page
for a person. The two error models exist for two different audiences and
neither subsumes the other; see `integration-seams.md` and
open-questions.md item 8.

## What's notably absent

No logging beyond Flask/Werkzeug defaults, no metrics, no rate limiting, no
streaming/chunked responses (every resource is read fully into memory and
returned in one `Response`), no content negotiation, no caching headers
(`ETag`, `Cache-Control`, conditional `GET`) on resource responses despite
the underlying files being static and content-addressable by nature. PR-002's
own `scope.out` names several of these explicitly as deferred, not
overlooked.
