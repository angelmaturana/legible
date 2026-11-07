#!/usr/bin/env python3
"""Console and CLI of `check_site.py`: `print_check_report`, `print_prelaunch_report`, `_Box`, `_report_issues`
and `main` (G3 of docs/PLAN-fases-restantes.md).

    python3 -B -m unittest tests.test_validator_console

GOLDEN. `tests/golden/console.txt` stores the exact stdout of `print_check_report` and `print_prelaunch_report`
for 5 cases (see `TestConsoleGolden.cases`): a clean build, the same build with 1 warning only (non-strict and
--strict, since they print differently), the same build with 1 error + 1 warning, and `--prelaunch` with no
findings / with findings. Regenerate only by hand, reviewing the diff:

    UPDATE_GOLDEN=1 python3 -B -m unittest tests.test_validator_console.TestConsoleGolden.test_console_matches_golden

Found while writing this (not a bug introduced here; documented, not changed -- the plan keeps G3 text/behaviour
exactly as is): in non-strict mode, `success` is True whenever there are no *errors*, even if there are
warnings; `_report_issues` then takes its `if success:` branch and prints "No issues", so warnings never appear
in the console report unless `--strict` is on. `CASE_WARNING_ONLY_NOT_STRICT` below pins this down on purpose.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
os.environ.pop('SITE_URL', None)
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / 'legible'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import check_site  # noqa: E402
import fixtures  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / 'golden' / 'console.txt'
URL = fixtures.CLEAN_SITE_URL
HEADER_RE = '### '


def captured(func, *a, **kw):
    """stdout of `func(*a, **kw)`, as text."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        func(*a, **kw)
    return buf.getvalue()


def _split_golden(text):
    """`{case name: body}` from a file written as `### NAME\\n<body>\\n` blocks, one per case."""
    sections = {}
    name, body = None, []
    for line in text.splitlines(keepends=True):
        if line.startswith(HEADER_RE):
            if name is not None:
                sections[name] = ''.join(body)
            name, body = line[len(HEADER_RE):].strip(), []
        else:
            body.append(line)
    if name is not None:
        sections[name] = ''.join(body)
    return sections


class _CleanBuild(unittest.TestCase):
    """A clean build (`fixtures.make_clean_project`, on which `run_checks` reports nothing) plus two copies
    of it that give exactly the findings each golden case needs: deleting `llms.txt` is R86 (1 warning, nothing
    else: `test_missing_files` in `test_validator_rules.py` already pins this down alone), deleting both
    `llms.txt` and `robots.txt` adds R85 (1 error) on top, still nothing else."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        root = fixtures.make_clean_project(Path(cls._tmp.name) / 'clean')
        with contextlib.redirect_stdout(io.StringIO()):
            ok = build.build(root, no_validate=True)
        assert ok, 'the clean project does not build'
        cls.clean_out = root / 'dist'
        cls.n_pages = len(list(cls.clean_out.rglob('*.html')))

        cls.warning_only_out = Path(cls._tmp.name) / 'warning-only'
        shutil.copytree(cls.clean_out, cls.warning_only_out)
        (cls.warning_only_out / 'llms.txt').unlink()

        cls.error_and_warning_out = Path(cls._tmp.name) / 'error-and-warning'
        shutil.copytree(cls.warning_only_out, cls.error_and_warning_out)
        (cls.error_and_warning_out / 'robots.txt').unlink()

    def findings(self, out):
        return check_site.run_checks(out, URL)


class TestConsoleGolden(_CleanBuild):
    def report(self, errors, warnings, strict=False):
        success = not errors and (not strict or not warnings)
        return captured(check_site.print_check_report, success, errors, warnings, self.n_pages,
                        '2026-01-01 00:00:00', 'main', 'abc1234', 'dist', strict)

    def cases(self):
        clean_errors, clean_warnings = self.findings(self.clean_out)
        self.assertEqual((clean_errors, clean_warnings), ([], []))
        warning_errors, warning_warnings = self.findings(self.warning_only_out)
        self.assertEqual((len(warning_errors), len(warning_warnings)), (0, 1))
        both_errors, both_warnings = self.findings(self.error_and_warning_out)
        self.assertEqual((len(both_errors), len(both_warnings)), (1, 1))
        return {
            'CLEAN': self.report(clean_errors, clean_warnings),
            # see the module docstring: non-strict + warnings only still reports "No issues"
            'WARNING_ONLY_NOT_STRICT': self.report(warning_errors, warning_warnings, strict=False),
            'WARNING_ONLY_STRICT': self.report(warning_errors, warning_warnings, strict=True),
            'ERROR_AND_WARNING': self.report(both_errors, both_warnings, strict=False),
            'PRELAUNCH_CLEAN': captured(check_site.print_prelaunch_report, []),
            'PRELAUNCH_FINDINGS': captured(check_site.print_prelaunch_report, [
                ('src/data/site.json', '"site_name" still has the example value "Your Business"',
                 'write the real value of "site_name"'),
                ('dist/', 'the output contains "YOUR-DOMAIN" (in index.html, about/index.html and 1 more)',
                 'fix it in src/ (data or page) and rebuild'),
            ]),
        }

    def test_console_matches_golden(self):
        current = self.cases()
        if os.environ.get('UPDATE_GOLDEN') == '1':
            text = ''.join(f'### {name}\n{current[name]}\n' for name in sorted(current))
            GOLDEN.write_text(text, encoding='utf-8')
            self.skipTest(f'golden regenerated: {GOLDEN} (review the diff by hand)')
        self.assertTrue(GOLDEN.exists(), 'tests/golden/console.txt is missing; generate it with UPDATE_GOLDEN=1')
        golden = _split_golden(GOLDEN.read_text(encoding='utf-8'))
        self.assertEqual(sorted(current), sorted(golden), 'the cases and the golden file have different names')
        for name in sorted(current):
            with self.subTest(case=name):
                self.assertEqual(current[name] + '\n', golden[name])

    def test_box_rows_share_one_fixed_width(self):
        """Every bordered line of `print_check_report`'s output is exactly `_Box.W + 2` characters (the two
        vertical border characters plus the interior): a label or a wrapped message that overflowed `_Box.W`
        would break the box silently, which the golden text alone would not point at directly."""
        box = check_site._Box()
        for text in self.cases().values():
            for line in text.splitlines():
                if line.startswith('║'):  # a bordered row, not a '╔...╗' frame line
                    self.assertEqual(len(line), box.W + 2, line)


class TestMainRunChecks(_CleanBuild):
    """`main(argv)` end to end, with temporary folders, for the exit-code matrix of docs/PLAN-fases-restantes.md
    G3: 0 clean, 1 with errors, `--strict` turns warnings into a failing exit code too."""

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_site.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_clean_project_exits_0(self):
        code, out, err = self.run_main(['--dir', str(self.clean_out), '--site-url', URL])
        self.assertEqual(code, 0)
        self.assertIn('CHECK PASSED', out)
        self.assertEqual(err, '')

    def test_errors_exit_1_even_without_strict(self):
        code, out, _err = self.run_main(['--dir', str(self.error_and_warning_out), '--site-url', URL])
        self.assertEqual(code, 1)
        self.assertIn('CHECK FAILED', out)

    def test_warnings_only_without_strict_exit_0(self):
        code, _out, _err = self.run_main(['--dir', str(self.warning_only_out), '--site-url', URL])
        self.assertEqual(code, 0)

    def test_warnings_only_with_strict_exits_1(self):
        code, out, _err = self.run_main(['--dir', str(self.warning_only_out), '--site-url', URL, '--strict'])
        self.assertEqual(code, 1)
        self.assertIn('CHECK FAILED', out)

    def test_n_pages_counts_the_html_files_of_the_output(self):
        code, out, _err = self.run_main(['--dir', str(self.clean_out), '--site-url', URL])
        self.assertEqual(code, 0)
        self.assertIn(f'Pages Checked  : {self.n_pages}', out)


class TestMainPrelaunch(unittest.TestCase):
    """`--prelaunch` branches on `main` itself (the exit code and which report is printed), independent of what
    `prelaunch_findings` returns: that function already has its own tests in `test_validator.py`."""

    def run_prelaunch(self, findings):
        out = io.StringIO()
        with mock.patch.object(check_site, 'prelaunch_findings', return_value=findings) as mocked, \
             contextlib.redirect_stdout(out):
            code = check_site.main(['--prelaunch', '--dir', 'ignored-by-the-mock', '--site-url', URL])
        mocked.assert_called_once_with(check_site.REPO, Path('ignored-by-the-mock'), URL)
        return code, out.getvalue()

    def test_no_findings_exits_0_and_says_ready(self):
        code, out = self.run_prelaunch([])
        self.assertEqual(code, 0)
        self.assertIn('Ready to publish', out)
        self.assertNotIn('Not ready', out)

    def test_findings_exit_1_and_list_them(self):
        code, out = self.run_prelaunch([('a.html', 'still says "example"', 'fix it')])
        self.assertEqual(code, 1)
        self.assertIn('Not ready to publish', out)
        self.assertIn('a.html', out)


class TestCliSmoke(unittest.TestCase):
    """The one subprocess test the plan allows (in-process `main(argv)` calls cover the exit codes above; this
    one instead catches anything only a real process run would show: the shebang, running as `__main__`,
    `sys.exit(main())`, argument parsing from a real argv)."""

    def test_runs_as_a_standalone_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixtures.make_clean_project(Path(tmp) / 'clean')
            with contextlib.redirect_stdout(io.StringIO()):
                assert build.build(root, no_validate=True)
            out = root / 'dist'
            env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
            r = subprocess.run([sys.executable, str(REPO / 'legible' / 'check_site.py'),
                                '--dir', str(out), '--site-url', URL],
                               capture_output=True, text=True, env=env, cwd=REPO)
            self.assertEqual(r.returncode, 0, f'{r.stdout}\n{r.stderr}')
            self.assertIn('CHECK PASSED', r.stdout)
            self.assertEqual(r.stderr, '')


if __name__ == '__main__':
    unittest.main()
