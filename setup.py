"""Build hook only; all package metadata is in pyproject.toml.

Copies the sandbox build files (divergence/sandbox_files.py: BUNDLE) into the wheel
under divergence/_sandbox/, so `pip install` alone gives `divergence setup-sandbox`
everything it needs. The repo keeps a single copy of each file in sandbox/ and vendor/.
"""

import runpy
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

HERE = Path(__file__).resolve().parent
_files = runpy.run_path(str(HERE / "divergence" / "sandbox_files.py"))


class BuildPyWithSandbox(build_py):
    def run(self):
        super().run()
        dest_root = Path(self.build_lib) / "divergence" / _files["BUNDLE_DIR"]
        for rel in _files["BUNDLE"]:
            src = HERE / rel
            if not src.exists():
                raise FileNotFoundError(f"sandbox bundle file missing: {rel}")
            dst = dest_root / rel
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)


setup(cmdclass={"build_py": BuildPyWithSandbox})
