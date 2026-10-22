"""Offline preprocessor/integration tests, NOT an arm64 kernel build.
Run: python3 -m unittest discover -s tests -v
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "kernel"
HEADER = KERNEL / "include/bakasu_susfs_compat.h"


class SelinuxPreprocessorTests(unittest.TestCase):
    def preprocess(self, major=5, minor=10, susfs=True):
        source = (KERNEL / "feature/selinux_hide.c").read_text()
        # Keep all real conditional compilation, but drop includes. This is
        # strictly a preprocessor test; the vendor object build tests C types.
        source = re.sub(r"^\s*#\s*include[^\n]*", "", source, flags=re.M)
        prefix = ("#define KERNEL_VERSION(a,b,c) (((a)<<16)+((b)<<8)+(c))\n"
                  f"#define LINUX_VERSION_CODE KERNEL_VERSION({major},{minor},110)\n"
                  "#define CONFIG_KALLSYMS_ALL 1\n")
        if susfs:
            prefix += "#define KSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE 1\n"
        return subprocess.run(["gcc", "-E", "-P", "-undef", "-nostdinc", "-x", "c", "-"],
                              input=prefix + source, text=True, capture_output=True)

    def test_510_susfs_exports_real_handlers(self):
        result = self.preprocess()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("my_write_context", "my_write_access"):
            self.assertRegex(result.stdout, r"(?m)^\s*ssize_t\s+" + name + r"\(")
            self.assertNotRegex(result.stdout, r"static\s+ssize_t\s+" + name + r"\(")
        self.assertRegex(result.stdout, r"int\s+__nocfi\s+my_setprocattr\(")

    def test_510_fake_state_not_lost_by_widening_guard(self):
        result = self.preprocess()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(re.findall(r"struct selinux_state fake_state;", result.stdout)), 1)
        self.assertIn("fake_state.policy = backup_sepolicy;", result.stdout)
        self.assertIn("fake_state.initialized = true;", result.stdout)

    def test_susfs_handler_does_not_call_uninstalled_auto_hook(self):
        result = self.preprocess()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("selinux_setprocattr_hook.original", result.stdout)

    def test_non_susfs_keeps_static_handlers_and_original_hook(self):
        result = self.preprocess(susfs=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"static\s+ssize_t\s+my_write_context\(")
        self.assertIn("selinux_setprocattr_hook.original", result.stdout)
        self.assertNotRegex(result.stdout, r"int\s+__nocfi\s+my_setprocattr\(")

    def test_nongki_susfs_is_rejected(self):
        result = self.preprocess(5, 4)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does NOT support", result.stderr)


class ProfileTests(unittest.TestCase):
    def test_profile_is_explicit_not_stubbed_preinit(self):
        text = HEADER.read_text()
        self.assertIn("#define BAKASU_SUSFS_COMPAT_VERSION 1", text)
        self.assertRegex(text, r"#ifdef CONFIG_KSU_SUSFS\n#define KSU_NO_PREINIT 1\n#endif")
        for path in KERNEL.rglob("*.c"):
            self.assertNotRegex(path.read_text(), r"(?m)^(?:int|bool)\s+ksu_(?:setup_preinit_file|preinit_handle_post_execveat)\(")

    def test_userspace_and_uapi_unchanged_from_manager_base(self):
        base = (KERNEL / "tools/susfs_manager_commit").read_text().strip()
        self.assertRegex(base, r"^[0-9a-f]{40}$")
        result = subprocess.run(["git", "diff", "--exit-code", base, "--", "manager", "userspace", "uapi"],
                                cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def run_gate(self, minor="10", header=True, tamper=False, include=True, preinit=True):
        with tempfile.TemporaryDirectory() as tmp:
            common = Path(tmp)
            (common / "security/selinux").mkdir(parents=True)
            (common / "fs").mkdir()
            (common / "include/linux").mkdir(parents=True)
            (common / "security/selinux/hooks.c").write_text("bool ksu_selinux_hide_running;\n")
            text = "#include <linux/bakasu_susfs_compat.h>\n" if include else ""
            if preinit:
                text += "extern int ksu_setup_preinit_file(void);\n"
            (common / "fs/exec.c").write_text(text)
            if header:
                shutil.copyfile(HEADER, common / "include/linux" / HEADER.name)
                if tamper:
                    (common / "include/linux" / HEADER.name).write_text("#define KSU_NO_PREINIT 1\n")
            wrapper = common / "gate.mk"
            wrapper.write_text(f"include {KERNEL}/tools/susfs_compat.mk\nall:\n\t@echo gate-ok\n")
            return subprocess.run(["make", "--no-print-directory", "-f", str(wrapper),
                                   "VERSION=5", "PATCHLEVEL=" + minor, "CONFIG_KSU=y",
                                   "REPO_NAME=BakaSU", "KSU_SRC=" + str(KERNEL), "srctree=" + tmp],
                                  text=True, capture_output=True)

    def test_gate_accepts_exact_bridge(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("gate-ok", result.stdout)

    def test_gate_rejects_missing_or_foreign_header(self):
        for kwargs in ({"header": False}, {"tamper": True}):
            with self.subTest(kwargs=kwargs):
                result = self.run_gate(**kwargs)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("matching BakaSU compatibility header", result.stderr)

    def test_gate_rejects_missing_include(self):
        result = self.run_gate(include=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must include", result.stderr)

    def test_gate_rejects_old_exec_patch(self):
        result = self.run_gate(preinit=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current SUSFS", result.stderr)

    def test_gate_rejects_other_kernel_series(self):
        result = self.run_gate(minor="15")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only supports android12-5.10", result.stderr)


if __name__ == "__main__":
    unittest.main()
