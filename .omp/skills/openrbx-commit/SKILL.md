---
name: openrbx-commit
description: Use when preparing, reviewing, or amending a commit in OpenRBX. Encodes this repository's commit grammar, domain verb taxonomy, body policy, one-unit granularity, and the checks that must pass before committing.
---

# OpenRBX commit standard

Derived from the repository's own history on 2026-11-06: 1,138 commits, linear (zero merges), zero conventional-commit prefixes, zero trailing periods, zero addresses in subjects. The current style (2026-10-24 onward, 537 commits) has no bodies at all; the 15 bodies in the corpus are all from 2026-08-01 through 08-07, when a body carried a non-obvious codegen explanation. Copy the current style, not the early one.

## Subject

`<Imperative verb> <exact object>`

- Sentence case, one line, aim for 72 columns. Median is 56; 15 of 537 recent subjects exceed 72, all enumerating one coherent batch. Never a paragraph.
- No `feat:`/`fix:`/`chore:` prefix. No subsystem prefix (`Primitive:`, `WebService:`) — that style exists only on 2026-08-01 and was abandoned.
- No trailing period (0/1,138). No address (0/1,138). No file paths. No issue numbers.
- Imperative present: "Match", "Pair", "Recover" — not "Matched", "Matches", "Matching".
- Name the exact class, function, file, or data shape. "Update files" is not a subject.
- Use "the client's ..." for entities that exist only in `Roblox.exe`. Shared engine code needs no possessive. Join 2–3 related items with "and"; commas are fine when the object is a list.
- Append ` [skip ci]` only to docs/CI commits that need no build (26 in the corpus, 13 recent).

## Verb taxonomy

The verb states what kind of change the commit makes. Profiles below are measured on the 537 recent commits: whether they touch code, `reccmp/`, median added code lines.

| Verb | Meaning | Profile |
|---|---|---|
| `Match` | body is now byte-identical to the original | code 167/167, CSV 106, +59 |
| `Write` | implement a missing body | code 87/87, CSV 68, +95 |
| `Recover` | reconstruct layout, interface, names, or PDB shape | code 36/36, CSV 24, +95 |
| `Pair` | claim annotations, aliases, or vtable slots that already match | code 44/64, CSV 56, +3 |
| `Name` | assign symbols, locals, parameters, or globals | code 12/18, CSV 10, +13 |
| `Claim` | promote an annotation whose body already matched | code 11/11, +3 |
| `Declare` | add declarations or signatures the original declared | code 15/15, CSV 5, +126 |
| `Add` | new file, class, subsystem, or data source | code 19/19, CSV 16, +191 |
| `Decompile` | whole-file or whole-class annotation campaign | code 19/19, CSV 19, +212 |
| `Instantiate` | fix a template instantiation or fold pairing | code 6/6, CSV 5, +15 |
| `Update` | documentation only; pair with `[skip ci]` | docs 6/6 |
| `Port` | bring a client-side implementation across | code 4/4, +532 |
| `Promote` | change `STUB:` to `FUNCTION:` because the body now matches | code 4/4, +20 |

Precise one-off verbs are encouraged when they say exactly what happened: `Uncross`, `Route`, `Override`, `Rebase`, `Restore`, `Drop`, `Size`, `Key`, `Place`, `Hoist`, `Correct`, `Stop`, `Type`, `Rename`, `Move`, `Reorder`, `Split`. Pick the smallest verb that is true; do not inflate a rename into a "Match".

## Body

Default: no body. Add one only when the diff cannot explain the *why* — register assignment, inline budget, fold groups, SEH scope tables, PDB type records, link order.

- One or two plain paragraphs, hard-wrapped at 72 columns.
- No bullets, no checklist, no trailers, no `Signed-off-by`, no co-author or AI-attribution lines.
- The body explains the original's codegen or the PDB evidence; it never restates the subject or lists files.
- Reverts are the exception: `Revert "<original subject>"` with git's standard body.

## Granularity

One verified unit per commit: a function, a small family, a class, an annotation batch, or one data-file change.

- Code and its `reccmp/` markers/CSV rows land together. `Match` commits touch `reccmp/` 106/167 times; `Pair` commits 56/64 times.
- Docs and CI changes land separately, with ` [skip ci]`.
- Do not bundle unrelated fixes. Do not leave build artifacts or generated files in the commit.
- No merge commits; history is linear.

## Before committing

1. Verify the unit. `reccmp-reccmp --target WEBSERVICE --nolib --verbose 0xADDRESS` (or `--target ROBLOX`). Read the diff; probe absence with `--verbose` before treating a folded address as missing.
2. Run the checks in `CLAUDE.md`: score, `reccmp-decomplint ... --warnfail`, `reccmp-vtable`, `reccmp-datacmp`, `tools/check_folded.py`, `tools/reccmp_addr_padding.py`, and the build.
3. Do not raise the number by reclassification. Never turn a `FUNCTION:` into a `STUB:` to move the score; never add `effective` without a byte-level explanation. If the body is genuinely equivalent but reordered, say so in the body.
4. If the commit changes code shared by both targets, score both before committing.

## Self-check

- Subject starts with one of the verbs above or an equally precise imperative.
- No prefix, no period, no address, no issue number, one line.
- The unit is singular and its annotations/CSV rows are included.
- Body is absent, or explains causality in plain wrapped prose.
- Checks ran; no `STUB:` demotion; no attribution trailers.

## Examples

```
Match the wedge mesh front and top deforms
Pair the client's IDREFItem vector insert and two boost callees
Recover the client's CRobloxWnd layout and constructor
Write the client's scene manager model registration
Route LevelBuilder's face builders through an inline uvwToObject
Promote ten matched client stubs
Update README.md [skip ci]
```

## Anti-patterns

```
feat: match wedge mesh                 # conventional prefix
WEBSERVICE: updates                     # abandoned subsystem prefix
Fixed the wedge mesh.                   # past tense, trailing period
Match the wedge mesh (fixes #12)        # issue number in subject
Update files                            # no object
Match the client's Codejock list destructors and shared_count constructors and the report allocator and ...
                                        # rambling; split the unit instead
```