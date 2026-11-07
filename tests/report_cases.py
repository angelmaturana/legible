#!/usr/bin/env python3
"""Cases of the console report of `build.py` (standard library only): the arguments and the 8 situations that
`tests/test_build_directed.py` checks line by line (box, columns, percentages, errors, warnings, strict, long paths,
empty sizes)."""
import contextlib
import io
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'legible'))
import build  # noqa: E402

REPORT_ARGS = dict(generated=7, total_bytes=12345, out='dist', minify=True, git_branch='main', git_commit='abc1234',
                   build_time='2026-01-01 12:00:00', total_html_before=10000, total_html_after=8000,
                   css_size_before=4000, css_size_after=3000)
WARNINGS = [('index.html', 'title is short'), ('src/static/images/og-image.png', 'the image is not 1200x630')]
ERRORS = [('index.html', 'broken link /nowhere/'), ('', 'no sitemap')]
LONG_OUT = '/very/long/folder/' + 'x' * 60 + '/dist'

CONSOLE_CASES = {
    'SUCCESS_CLEAN': dict(success=True, errors=[], warnings=[]),
    'SUCCESS_WARNINGS': dict(success=True, errors=[], warnings=WARNINGS),
    'STRICT_WARNINGS': dict(success=False, errors=[], warnings=WARNINGS, strict=True),
    'FAILED_ERRORS': dict(success=False, errors=ERRORS, warnings=[]),
    'FAILED_ERRORS_AND_WARNINGS': dict(success=False, errors=ERRORS, warnings=WARNINGS),
    'EMPTY_SIZES': dict(success=True, errors=[], warnings=[], total_html_before=0, total_html_after=0,
                        css_size_before=0, css_size_after=0, minify=False),
    'LONG_PATH': dict(success=True, errors=[], warnings=[], out=LONG_OUT, git_branch='feature/' + 'b' * 40),
    'GREW': dict(success=True, errors=[], warnings=[], total_html_after=11000, css_size_after=5000),
}


def console_of(case):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        build.print_report(banner=build.REPORT_BANNER, **{**REPORT_ARGS, **CONSOLE_CASES[case]})
    return buffer.getvalue()


def console_text():
    return ''.join(f'=== {case} ===\n{console_of(case)}' for case in CONSOLE_CASES)
