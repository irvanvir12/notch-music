"""Expose test failures as Actions annotations as well as runner logs."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
for test, detail in result.errors + result.failures:
    message = f'{test}\n{detail}'.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::error::{message}')
raise SystemExit(not result.wasSuccessful())
