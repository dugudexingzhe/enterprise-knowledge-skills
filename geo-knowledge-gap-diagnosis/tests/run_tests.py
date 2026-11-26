"""Run the real unittest suite and save machine-readable results + full log."""
import argparse
import io
import json
import platform
import sys
import unittest
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, help='新建测试结果目录')
    args = parser.parse_args()
    output = Path(args.out).resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit('测试结果目录非空，请换新目录，防止覆盖旧记录')
    output.mkdir(parents=True, exist_ok=True)
    log = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern='test_*.py')
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = {'started_platform': platform.platform(), 'python': platform.python_version(),
              'completed_at_utc': datetime.now(timezone.utc).isoformat(),
              'dependencies': {p: version(p) for p in ['pypdf', 'openpyxl']},
              'tests_run': result.testsRun,
              'passed': result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
              'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': [{'test': str(t), 'reason': reason} for t, reason in result.skipped],
              'successful': result.wasSuccessful()}
    (output / '自动测试日志.txt').write_text(log.getvalue(), encoding='utf-8')
    (output / '自动测试结果.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
