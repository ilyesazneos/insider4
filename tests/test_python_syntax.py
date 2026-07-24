import py_compile
import unittest
from pathlib import Path


class PythonSyntaxRegressionTests(unittest.TestCase):
    def test_all_audit_modules_compile(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("audit_common.py", "design_audit.py", "code_audit.py", "reuse_audit.py"):
            with self.subTest(name=name):
                py_compile.compile(str(root / name), doraise=True)


if __name__ == "__main__":
    unittest.main()
