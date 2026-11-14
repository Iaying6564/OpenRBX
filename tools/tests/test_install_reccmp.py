import difflib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "install_reccmp.py"
SPEC = importlib.util.spec_from_file_location("install_reccmp", SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="openrbx-installer-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "package" / installer.SOURCE
        self.source.parent.mkdir(parents=True)
        self.before = b"original = 1\n"
        self.after = b"original = 1\nmetadata = True\n"
        self.source.write_bytes(self.before)
        self.patch = self.root / "metadata.patch"
        self.patch.write_bytes(
            "".join(
                difflib.unified_diff(
                    self.before.decode().splitlines(True),
                    self.after.decode().splitlines(True),
                    fromfile="a/" + installer.SOURCE.as_posix(),
                    tofile="b/" + installer.SOURCE.as_posix(),
                )
            ).encode()
        )

    def apply(self, after_hash=None):
        return installer.apply_metadata_patch(
            self.source,
            self.patch,
            installer.digest(self.before),
            after_hash or installer.digest(self.after),
        )

    def distribution(self, commit=None, version=None):
        metadata = {
            "url": installer.ORIGIN,
            "vcs_info": {"vcs": "git", "commit_id": commit or installer.COMMIT},
        }
        return SimpleNamespace(
            version=version or installer.VERSION,
            read_text=lambda name: json.dumps(metadata),
        )

    def test_patch_is_idempotent(self):
        self.assertTrue(self.apply())
        self.assertEqual(self.source.read_bytes(), self.after)
        self.assertFalse(self.apply())

    def test_crlf_source_is_guarded_and_preserved(self):
        self.source.write_bytes(self.before.replace(b"\n", b"\r\n"))
        self.assertTrue(self.apply())
        self.assertEqual(self.source.read_bytes(), self.after.replace(b"\n", b"\r\n"))

    def test_unexpected_source_is_not_changed(self):
        changed = self.before + b"local_change = True\n"
        self.source.write_bytes(changed)
        with self.assertRaisesRegex(RuntimeError, "unexpected reccmp source"):
            self.apply()
        self.assertEqual(self.source.read_bytes(), changed)

    def test_bad_patch_result_does_not_change_installed_file(self):
        with self.assertRaisesRegex(RuntimeError, "expected SHA256"):
            self.apply(after_hash="0" * 64)
        self.assertEqual(self.source.read_bytes(), self.before)

    def test_pinned_distribution_is_accepted(self):
        installer.verify_distribution(self.distribution())

    def test_wrong_commit_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "commit"):
            installer.verify_distribution(self.distribution(commit="0" * 40))

    def test_wrong_version_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Expected reccmp"):
            installer.verify_distribution(self.distribution(version="different"))

    def test_requirements_pin_matches_guard(self):
        self.assertIn("@" + installer.COMMIT, installer.REQUIREMENTS.read_text())

    @patch.object(installer, "patch_installed_reccmp", return_value=False)
    @patch.object(installer.subprocess, "run")
    def test_patch_only_skips_pip(self, run, apply):
        self.assertEqual(installer.main(["--patch-only"]), 0)
        run.assert_not_called()
        apply.assert_called_once_with()

    @patch.object(installer, "patch_installed_reccmp", return_value=True)
    @patch.object(installer.subprocess, "run")
    def test_default_installs_pinned_requirements(self, run, apply):
        self.assertEqual(installer.main([]), 0)
        run.assert_called_once_with(
            [installer.sys.executable, "-m", "pip", "install", "-r", str(installer.REQUIREMENTS)],
            check=True,
        )
        apply.assert_called_once_with()


class PatchSetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="openrbx-patch-set-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.patch = self.root / "set.patch"
        self.specs = []
        hunks = []
        for index in range(2):
            relative = Path(f"reccmp/file{index}.py")
            source = self.root / "installed" / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            before = f"before{index} = True\n".encode()
            after = before + b"patched = True\n"
            source.write_bytes(before)
            self.specs.append(
                (source, self.patch, relative, installer.digest(before), installer.digest(after))
            )
            hunks.extend(
                difflib.unified_diff(
                    before.decode().splitlines(True),
                    after.decode().splitlines(True),
                    fromfile="a/" + relative.as_posix(),
                    tofile="b/" + relative.as_posix(),
                )
            )
        self.patch.write_text("".join(hunks))
        self.originals = [spec[0].read_bytes() for spec in self.specs]

    def test_multifile_patch_and_idempotence(self):
        self.assertTrue(installer.apply_guarded_patch_files(self.specs))
        self.assertFalse(installer.apply_guarded_patch_files(self.specs))

    def test_mixed_already_patched_and_pristine(self):
        self.assertTrue(installer.apply_guarded_patch_files(self.specs[:1]))
        first = self.specs[0][0].read_bytes()
        self.assertTrue(installer.apply_guarded_patch_files(self.specs))
        self.assertEqual(self.specs[0][0].read_bytes(), first)

    def test_all_inputs_validated_before_any_replacement(self):
        self.specs[1][0].write_bytes(b"unexpected\n")
        with self.assertRaisesRegex(RuntimeError, "unexpected reccmp source"):
            installer.apply_guarded_patch_files(self.specs)
        self.assertEqual(self.specs[0][0].read_bytes(), self.originals[0])

    def test_all_outputs_validated_before_any_replacement(self):
        bad = list(self.specs)
        bad[1] = (*bad[1][:4], "0" * 64)
        with self.assertRaisesRegex(RuntimeError, "expected SHA256"):
            installer.apply_guarded_patch_files(bad)
        self.assertEqual([s[0].read_bytes() for s in self.specs], self.originals)

    def test_missing_input_does_not_change_earlier_file(self):
        self.specs[1][0].unlink()
        with self.assertRaises(FileNotFoundError):
            installer.apply_guarded_patch_files(self.specs)
        self.assertEqual(self.specs[0][0].read_bytes(), self.originals[0])

    def test_backup_preparation_failure_does_not_change_files(self):
        mkstemp = installer.tempfile.mkstemp
        calls = 0
        def fail_third(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("injected preparation failure")
            return mkstemp(*args, **kwargs)
        with patch.object(installer.tempfile, "mkstemp", side_effect=fail_third):
            with self.assertRaisesRegex(OSError, "injected preparation"):
                installer.apply_guarded_patch_files(self.specs)
        self.assertEqual([s[0].read_bytes() for s in self.specs], self.originals)
        self.assertEqual(len(list((self.root / "installed/reccmp").iterdir())), 2)

    def test_second_replacement_failure_rolls_back_first(self):
        replace = installer.os.replace
        calls = []
        def fail_second(source, destination):
            calls.append(destination)
            if len(calls) == 2:
                raise OSError("injected replacement failure")
            return replace(source, destination)
        with patch.object(installer.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "injected replacement"):
                installer.apply_guarded_patch_files(self.specs)
        self.assertEqual([s[0].read_bytes() for s in self.specs], self.originals)
        self.assertEqual(len(list((self.root / "installed/reccmp").iterdir())), 2)

    def test_backup_retained_if_rollback_also_fails(self):
        replace = installer.os.replace
        count = 0
        def fail_after_first(source, destination):
            nonlocal count
            count += 1
            if count > 1:
                raise OSError("injected replacement failure")
            return replace(source, destination)
        with patch.object(installer.os, "replace", side_effect=fail_after_first):
            with self.assertRaisesRegex(RuntimeError, "backup retained"):
                installer.apply_guarded_patch_files(self.specs)
        backups = [
            p for p in (self.root / "installed/reccmp").iterdir()
            if p.name.startswith("file0.py.")
        ]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.originals[0])

    def test_multifile_crlf_preserved(self):
        for spec in self.specs:
            spec[0].write_bytes(spec[0].read_bytes().replace(b"\n", b"\r\n"))
        installer.apply_guarded_patch_files(self.specs)
        for spec in self.specs:
            self.assertIn(b"\r\n", spec[0].read_bytes())
            self.assertEqual(installer.digest(spec[0].read_bytes()), spec[4])

    def test_duplicate_and_traversal_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Invalid or duplicate"):
            installer.apply_guarded_patch_files([self.specs[0], self.specs[0]])
        bad = list(self.specs[0])
        bad[2] = Path("../outside.py")
        with self.assertRaisesRegex(RuntimeError, "Invalid or duplicate"):
            installer.apply_guarded_patch_files([bad])
        duplicate_relative = list(self.specs[1])
        duplicate_relative[2] = self.specs[0][2]
        with self.assertRaisesRegex(RuntimeError, "Invalid or duplicate"):
            installer.apply_guarded_patch_files([self.specs[0], duplicate_relative])
        rooted = list(self.specs[0])
        rooted[2] = Path("/outside.py")
        with self.assertRaisesRegex(RuntimeError, "Invalid or duplicate"):
            installer.apply_guarded_patch_files([rooted])



if __name__ == "__main__":
    unittest.main()
