`python tools/install_reccmp.py` installs the pinned reccmp fork and applies the
patches below. Use `--patch-only` for an existing pinned installation.

`anonymous-publics.patch` supplies demangled names for anonymous-namespace
PUBLICS that lack PROC/GDATA names. This preserves matching when original
archive objects were built without debug information. Raw symbols and types
remain unchanged; PROC/GDATA names retain precedence.

`pointer-cmp.patch` extends pointer-immediate naming in a 32-bit CMP only when
its four-byte immediate field has an IMAGE_REL_BASED_HIGHLOW relocation. The new
cases require a matched named identity: the exact endpoint of a DATA/OFFSET
object, or an interior byte of a STRING/WIDECHAR object within its recorded
bounds. Exact entity lookup retains precedence. Ordinary memory lookups keep their existing
bounds; unknown pointers receive no invented placeholder. Other relocation types
are excluded, including the extra adjustment word belonging to HIGHADJ.

These patches correct comparison metadata and address naming. They do not
enlarge object extents, change scoring formulas, or modify native binaries.

The installer checks the package version, Git origin/commit, and every affected
source hash. It stages and validates all pending outputs before replacing any
installed file. Already patched files remain unchanged. If replacement fails,
it restores earlier files; if restoration also fails, it retains and reports
the recovery backup. This provides runtime rollback, not process-crash atomicity.

Run the focused tests after installation:

```sh
python -m unittest discover -s tools/tests -v
```
