# Commit rules

- Read `skill://openrbx-commit` before writing any commit message.
- Subject: imperative verb + exact object, sentence case, one line, aim for 72 columns, no `type:` prefix, no trailing period, no addresses.
- One verified unit per commit. Code and its `reccmp/` markers and CSV rows land together; docs and CI land separately with ` [skip ci]`.
- Body only when the diff cannot explain why. Plain paragraphs wrapped at 72 columns, no bullets, trailers, or attribution.
- Run the checks in `CLAUDE.md` before committing. Never demote a `FUNCTION:` to `STUB:` to move the score, and never add `effective` without a byte-level reason.
- No AI attribution, no `Generated with`, no co-author trailers.