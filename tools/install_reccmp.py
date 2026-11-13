#!/usr/bin/env python3
"""Install the pinned reccmp fork and its guarded PUBLICS and pointer comparison fixes."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


TOOLS = Path(__file__).resolve().parent
REQUIREMENTS = TOOLS / "requirements.txt"
PATCH = TOOLS / "reccmp-patches" / "anonymous-publics.patch"
SOURCE = Path("reccmp/cvdump/analysis.py")
VERSION = "0.1.8"
COMMIT = "37a49c8e8b024b0f275bd1ae0f36a73b5de37797"
ORIGIN = "https://github.com/Asphaltian/reccmp"
BEFORE_SHA256 = "73fd75fb1d223c6d81cb53159075d62482381b48acfbfd94b6ea2438bb475394"
AFTER_SHA256 = "6b4500a8e631756dd42fdfc973dfb25d028670179ab52e18f9e78f056cc91ef6"


COMPARATOR_PATCH = TOOLS / "reccmp-patches" / "pointer-cmp.patch"
COMPARATOR_FILES = (
    (
        "compare/asm/replacement.py",
        "84e214875b1b77bb0e16f745242c2fd3b4fcca444b1c9c3c019fabadc93ed148",
        "b1374a792a62c01a463115d811e11b150f3dcd1d85993f590fc241d5120fdf49",
    ),
    (
        "compare/asm/parse.py",
        "0f41a634ba590b2a78174082bce7819d9d32dd2faf062a1fab9c1b60c54b53fa",
        "cf2b87abee52f43c763c72866ebbb6365c647b7b6647f841f5c94f80413755c3",
    ),
    (
        "compare/functions.py",
        "d8b05a315297737f26c932d65b1771ec4076aba709138e9ca9602bf761bd2479",
        "175e0ce929809ddff1378af5db0919a5d758d65eaf5604a7dc09188e9f5e3fb2",
    ),
    (
        "formats/pe.py",
        "61df8e719053638a23eca0695b937408237ba251368395611f076c6c3d58e0b8",
        "14077fa46000f747233f07231e8f1aeacc8aee403dbd98c25215f0ed632a832a",
    ),
)

def lf_bytes(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def digest(data: bytes) -> str:
    return hashlib.sha256(lf_bytes(data)).hexdigest()


def verify_distribution(distribution) -> None:
    """Require the precise VCS build that the checked-in patch was tested on."""
    if distribution.version != VERSION:
        raise RuntimeError(f"Expected reccmp {VERSION}; found {distribution.version}")
    direct_url = json.loads(distribution.read_text("direct_url.json") or "{}")
    vcs = direct_url.get("vcs_info", {})
    origin = direct_url.get("url", "").rstrip("/").removesuffix(".git")
    if (
        origin.lower() != ORIGIN.lower()
        or vcs.get("vcs") != "git"
        or vcs.get("commit_id") != COMMIT
    ):
        raise RuntimeError(f"Expected reccmp from {ORIGIN} at commit {COMMIT}")


def apply_guarded_patch_files(specifications) -> bool:
    """Stage a guarded patch set, then replace files with runtime rollback.

    Entries are (installed path, patch path, patch-relative path, before hash,
    after hash). Already patched files are accepted independently, allowing a
    PUBLICS-only installation to upgrade without reverting its metadata fix.
    """
    pending = []
    seen = set()
    relative_paths = set()
    with tempfile.TemporaryDirectory(prefix="openrbx-reccmp-") as directory:
        work = Path(directory).resolve()
        if not work.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise RuntimeError("Patch staging directory is outside the temporary directory")
        for source, patch, relative, before, after in specifications:
            source, patch, relative = Path(source), Path(patch), Path(relative)
            if (
                relative.anchor
                or ".." in relative.parts
                or source.resolve() in seen
                or relative in relative_paths
            ):
                raise RuntimeError("Invalid or duplicate patch source")
            seen.add(source.resolve())
            relative_paths.add(relative)
            original = source.read_bytes()
            actual = digest(original)
            if actual == after:
                continue
            if actual != before:
                raise RuntimeError(f"Refusing to patch unexpected reccmp source {source}: SHA256 {actual}")
            staged = work / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(lf_bytes(original))
            pending.append((source, patch, relative, original, after))
        for source, patch, relative, original, after in pending:
            staged_patch = work / "patch.diff"
            staged_patch.write_bytes(lf_bytes(patch.read_bytes()))
            for options in (["--check"], []):
                subprocess.run(
                    ["git", "apply", *options, "--include=" + relative.as_posix(), str(staged_patch)],
                    cwd=work,
                    check=True,
                )
            if digest((work / relative).read_bytes()) != after:
                raise RuntimeError("Patched reccmp source failed the expected SHA256 check")
        prepared = []
        replaced = []
        try:
            # Prepare both replacements and exact backups before mutating any file.
            for source, patch, relative, original, after in pending:
                paths = []
                prepared.append((source, original, paths))
                patched = lf_bytes((work / relative).read_bytes())
                if b"\r\n" in original:
                    patched = patched.replace(b"\n", b"\r\n")
                for contents in (patched, original):
                    descriptor, filename = tempfile.mkstemp(prefix=source.name + ".", dir=source.parent)
                    temporary = Path(filename)
                    paths.append(temporary)
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(contents)
                    shutil.copymode(source, temporary)
            for source, original, paths in prepared:
                if source.read_bytes() != original:
                    raise RuntimeError(f"Source changed during patch staging: {source}")
            for source, original, paths in prepared:
                os.replace(paths[0], source)
                replaced.append((source, paths[1]))
        except BaseException as error:
            failures = []
            for source, backup in reversed(replaced):
                try:
                    os.replace(backup, source)
                except OSError as rollback_error:
                    failures.append(f"{source}: {rollback_error}; backup retained at {backup}")
            if failures:
                # Preserve any backup that could not be restored for manual recovery.
                retained = {backup for source, backup in replaced if backup.exists()}
                for source, original, paths in prepared:
                    for path in paths:
                        if path not in retained:
                            path.unlink(missing_ok=True)
                prepared.clear()
                raise RuntimeError("Patch failed and rollback needs recovery: " + "; ".join(failures)) from error
            raise
        finally:
            for source, original, paths in prepared:
                for path in paths:
                    path.unlink(missing_ok=True)
    return bool(pending)


def apply_metadata_patch(
    source: Path,
    patch: Path = PATCH,
    before_sha256: str = BEFORE_SHA256,
    after_sha256: str = AFTER_SHA256,
) -> bool:
    """Keep the original single-file PUBLICS patch API."""
    return apply_guarded_patch_files([(source, patch, SOURCE, before_sha256, after_sha256)])


def patch_installed_reccmp() -> bool:
    distribution = importlib.metadata.distribution("reccmp")
    verify_distribution(distribution)
    specs = [
        (Path(distribution.locate_file(SOURCE)), PATCH, SOURCE, BEFORE_SHA256, AFTER_SHA256)
    ]
    for relative, before, after in COMPARATOR_FILES:
        source = Path("reccmp") / relative
        specs.append(
            (Path(distribution.locate_file(source)), COMPARATOR_PATCH, source, before, after)
        )
    return apply_guarded_patch_files(specs)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--patch-only",
        action="store_true",
        help="skip pip and patch an existing installation of the pinned fork",
    )
    args = parser.parse_args(argv)
    try:
        if not args.patch_only:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)],
                check=True,
            )
        changed = patch_installed_reccmp()
    except (
        OSError,
        ValueError,
        RuntimeError,
        importlib.metadata.PackageNotFoundError,
        subprocess.CalledProcessError,
    ) as error:
        parser.exit(1, f"reccmp installation failed: {error}\n")
    print("Applied guarded reccmp patches" if changed else "reccmp patches already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
