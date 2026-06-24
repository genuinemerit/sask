# analysis/functionality/

Research output, not design. This directory captures what was learned from
reviewing the sibling `sask` project's **application-functional** code — the
small authenticated resource server it built and then never extended — with a
view to informing a later design session about merging an improved version of
that asset-serving capability into `sask-calendar`. Nothing here is a DD,
REQ, or SPEC, and nothing here proposes a solution shape. It is homework, the
same way `analysis/deployment/` was homework for the deploy-port effort.

## Why this exists

This analysis was not triggered by an existing backlog item the way
`analysis/deployment/` was (that one had DD-0001/DD-0003 followups and
SPEC-005 already pointing at "reuse the sask deploy pattern"). `sask-calendar`
has no DD, REQ, or SPEC today that names asset-serving, an asset catalog,
or application-level authentication as planned work — DD-0014's decision
explicitly defers application authentication ("Access: public, no
authentication... auth is deferred, not designed out") without naming what it
would be deferred *to*. This analysis exists because the user asked for it
directly, as preparatory material for a design session that has not happened
yet. Treat the absence of an existing hook as itself a fact worth carrying
into that session, not an oversight in this document.

## Scope

Source material is the `sask` project (`~/Code/sask`), filtered to
**application-functional code**: the Flask resource server's routes,
authentication, resource manifest, and serialization, plus the
requirements/decisions/PR-spec/tests/docs that describe and constrain that
code. Deployment, provisioning, and orchestration are explicitly **out of
scope** here — that material is already covered in `analysis/deployment/` and
is not revisited except where a deployment-layer fact (e.g. how app secrets
reach the droplet) is needed to explain a functional-layer decision (e.g. why
the token model has no rotation).

The comparison side is `sask-calendar`'s own current engine and web layer —
not because it's being ported *from*, but because the whole point of this
analysis is to locate where sask's resource-service code would have to touch
`sask-calendar`'s existing config loading, message-unit seam, and
Flask/Jinja presentation layer if it were merged in.

## Reading order

1. [source-inventory.md](source-inventory.md) — what was reviewed in `sask`,
   file by file, scored in/out/redesign-candidate, plus a dedicated section on
   what should be left behind rather than ported.
2. [functional-architecture.md](functional-architecture.md) — how the
   resource service actually works end to end: request lifecycle, the
   kind/id addressing model, the auth model, the error model.
3. [persistence.md](persistence.md) — a dedicated, careful look at what sask's
   resource service stores, how, and how that's accessed, set against
   `sask-calendar`'s current no-database, load-once-at-startup engine config.
   This is the single largest architectural divergence between the two
   functional areas.
4. [integration-seams.md](integration-seams.md) — the four shared-concern
   touch-points (config loading, the message-unit seam, the Flask/Jinja
   presentation layer, persistence) where a port's delineation decisions will
   actually live.
5. [open-questions.md](open-questions.md) — decisions and ambiguities this
   analysis surfaced but does not resolve. High-value output by design: read
   this even if nothing else.

## What this is not

- Not a DD, REQ, or SPEC.
- Not code, and not a design. No solution shape — module layout, blueprint
  structure, schema for a future asset table, auth mechanism — is proposed
  anywhere in this directory. That work happens in a later, separate design
  session, off-line from this one.
- Not a verdict that sask's resource-service code is good or bad. It is
  characterized precisely enough to support a design decision, including
  naming the places where the existing implementation is a poor fit for
  `sask-calendar`'s established conventions — but the replacement is not
  drafted here.
- Not exhaustive on sask's deployment material — see `analysis/deployment/`
  for that.
