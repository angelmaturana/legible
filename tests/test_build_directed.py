#!/usr/bin/env python3
"""Directed tests of the four functions of `build.py` that G4b/G4c split: `_nav_items` (and its inner `check`),
`print_report` and `parse_args`. In process, standard library only.

    python3 -B -m unittest tests.test_build_directed

They fix the CURRENT behaviour, texts included (exact messages, not fragments), so that a refactor that only moves
code cannot change what the user sees. The inputs go straight to the function: no project on disk.
"""
import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'legible'))
sys.path.insert(0, str(HERE))
import build  # noqa: E402
import report_cases as G  # noqa: E402

USAGE = build.USAGE
SRC = 'src/data/site.json'


def entry(label='A', url='/a/', **extra):
    return {'label': label, 'url': url, **extra}


class TestNavItems(unittest.TestCase):
    def items(self, value, key='nav', children=True, action=True):
        return build._nav_items({key: value}, key, children, action)

    def message(self, value, **kwargs):
        with self.assertRaises(build.BuildError) as ctx:
            self.items(value, **kwargs)
        self.assertEqual(ctx.exception.label, 'BUILD FAILED')
        return str(ctx.exception)

    def test_valid_menus_come_back_untouched(self):
        for value in ([], [entry()], [entry(), entry('B', '/b/')],
                      [entry(children=[entry('B', '/b/')])],
                      [entry(action=True), entry('B', '/b/', action=False)],
                      [entry(children=[entry('B', '/b/'), entry('C', '/c/')], action=True)]):
            with self.subTest(value=value):
                self.assertIs(self.items(value), value)

    def test_a_missing_or_null_key_is_an_empty_menu(self):
        self.assertEqual(build._nav_items({}, 'nav', True, True), [])
        self.assertEqual(build._nav_items({'nav': None}, 'nav', True, True), [])

    def test_exact_messages(self):
        cases = [
            ('Home', f'{SRC} › nav must be a list (found str)'),
            ({'label': 'A'}, f'{SRC} › nav must be a list (found dict)'),
            (3, f'{SRC} › nav must be a list (found int)'),
            (['Home'], f'{SRC} › nav[0] must be an object {{"label": "...", "url": "/page/"}}'),
            ([entry(), None], f'{SRC} › nav[1] must be an object {{"label": "...", "url": "/page/"}}'),
            ([{'url': '/a/'}], f'{SRC} › nav[0]: missing "label" (a non-empty text)'),
            ([{'label': 'A'}], f'{SRC} › nav[0]: missing "url" (a non-empty text)'),
            ([{'label': ' ', 'url': '/a/'}], f'{SRC} › nav[0]: missing "label" (a non-empty text)'),
            ([{'label': 'A', 'url': ''}], f'{SRC} › nav[0]: missing "url" (a non-empty text)'),
            ([{'label': 3, 'url': '/a/'}], f'{SRC} › nav[0]: missing "label" (a non-empty text)'),
            ([{'label': 'A', 'url': None}], f'{SRC} › nav[0]: missing "url" (a non-empty text)'),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(self.message(value), expected)

    def test_the_url_must_be_internal_with_slashes_and_no_spaces(self):
        for url in ('a/', '/a', 'a', '/', '//', '//example.com/', 'https://example.com/', '/a b/', '/a/ ', 'mailto:x'):
            if url == '/':
                with self.subTest(url=url):  # the home page is valid
                    self.assertEqual(len(self.items([entry(url=url)])), 1)
                continue
            with self.subTest(url=url):
                self.assertEqual(
                    self.message([entry(url=url)]),
                    f'{SRC} › nav[0]: url {url!r} must be an internal address that starts and ends with "/" '
                    '(for example "/contact/")')

    def test_a_repeated_url_names_where_it_was_first_used(self):
        self.assertEqual(self.message([entry(), entry('B', '/b/'), entry('C', '/a/')]),
                         f"{SRC} › nav[2]: url '/a/' is repeated (already used by {SRC} › nav[0])")
        self.assertEqual(
            self.message([entry(children=[entry('B', '/b/')]), entry('C', '/b/')]),
            f"{SRC} › nav[1]: url '/b/' is repeated (already used by {SRC} › nav[0] › children[0])")
        self.assertEqual(
            self.message([entry(children=[entry('B', '/a/')])]),
            f"{SRC} › nav[0] › children[0]: url '/a/' is repeated (already used by {SRC} › nav[0])")

    def test_repeated_urls_are_checked_per_menu(self):
        self.items([entry()], key='nav')
        self.items([entry()], key='legal_nav')

    def test_action_rules(self):
        self.assertEqual(self.message([entry(action='yes')]),
                         f'{SRC} › nav[0]: "action" must be true or false (found \'yes\')')
        self.assertEqual(self.message([entry(action=1)]),
                         f'{SRC} › nav[0]: "action" must be true or false (found 1)')
        self.assertEqual(self.message([entry(action=True)], action=False),
                         f'{SRC} › nav[0]: "action" is only allowed on a top-level entry of nav')
        self.assertEqual(self.message([entry(action=False)], action=False, key='nav'),
                         f'{SRC} › nav[0]: "action" is only allowed on a top-level entry of nav')
        self.assertEqual(self.message([entry(children=[entry('B', '/b/', action=True)])]),
                         f'{SRC} › nav[0] › children[0]: "action" is only allowed on a top-level entry of nav')

    def test_children_rules(self):
        self.assertEqual(self.message([entry(children='x')]), f'{SRC} › nav[0]: "children" must be a list')
        self.assertEqual(self.message([entry(children=None)]), f'{SRC} › nav[0]: "children" must be a list')
        self.assertEqual(
            self.message([entry(children=[])], children=False),
            f'{SRC} › nav[0]: "children" is only allowed in one level of nav (no submenus inside a submenu)')
        self.assertEqual(
            self.message([entry(children=[entry('B', '/b/', children=[])])]),
            f'{SRC} › nav[0] › children[0]: "children" is only allowed in one level of nav '
            '(no submenus inside a submenu)')
        self.assertEqual(self.message([entry(children=[entry('B', '/b/'), 'x'])]),
                         f'{SRC} › nav[0] › children[1] must be an object {{"label": "...", "url": "/page/"}}')

    def test_the_first_problem_wins_in_the_order_of_the_checks(self):
        both = {'label': '', 'url': 'x', 'action': 'no', 'children': 'x'}
        self.assertIn('missing "label"', self.message([both]))
        self.assertIn('missing "url"', self.message([{**both, 'label': 'A', 'url': ''}]))
        self.assertIn('must be an internal address', self.message([{**both, 'label': 'A'}]))
        self.assertIn('"action" must be true or false', self.message([{**both, 'label': 'A', 'url': '/a/'}]))
        self.assertIn('"children" must be a list', self.message([{**both, 'label': 'A', 'url': '/b/', 'action': True}]))
        self.assertIn('is repeated', self.message([entry(), {**both, 'label': 'B', 'url': '/a/'}]))
        # an earlier entry fails before a later one is looked at
        self.assertIn('nav[0]', self.message([{'label': 'A'}, 'x']))

    def test_the_key_names_the_menu_in_every_message(self):
        self.assertEqual(self.message('x', key='legal_nav'), f'{SRC} › legal_nav must be a list (found str)')
        self.assertEqual(self.message([{'label': 'A'}], key='legal_nav'),
                         f'{SRC} › legal_nav[0]: missing "url" (a non-empty text)')

    def test_two_levels_are_walked_in_order(self):
        value = [entry(children=[entry('B', '/b/'), entry('C', '/c/')]),
                 entry('D', '/d/', children=[entry('E', '/b/')])]
        self.assertEqual(self.message(value),
                         f"{SRC} › nav[1] › children[0]: url '/b/' is repeated "
                         f"(already used by {SRC} › nav[0] › children[0])")


def run_args(*args, **environ):
    return build.parse_args(list(args), environ)


class TestParseArgs(unittest.TestCase):
    DEFAULTS = dict(out_dir=None, minify=False, no_validate=False, strict=False, all=False)

    def test_each_option_alone(self):
        cases = [
            ((), {}),
            (('--all',), dict(all=True, minify=True, strict=True)),
            (('--no-validate',), dict(no_validate=True)),
            (('--strict',), dict(strict=True)),
            (('--out', 'x'), dict(out_dir='x')),
            (('--minify', 'true'), dict(minify=True)),
            (('--minify', 'false'), dict(minify=False)),
            (('--minify', 'TRUE'), dict(minify=True)),
            (('--minify', 'False'), dict(minify=False)),
        ]
        for args, changes in cases:
            with self.subTest(args=args):
                self.assertEqual(run_args(*args), {**self.DEFAULTS, **changes})

    def test_combinations(self):
        cases = [
            (('--no-validate', '--strict', '--out', 'o', '--minify', 'true'),
             dict(no_validate=True, strict=True, out_dir='o', minify=True)),
            (('--out', 'o', '--all'), dict(out_dir='o', all=True, minify=True, strict=True)),
            (('--all', '--minify', 'false'), dict(all=True, minify=False, strict=True)),
            (('--all', '--strict', '--minify', 'true'), dict(all=True, minify=True, strict=True)),
            (('--out', 'a', '--out', 'b'), dict(out_dir='b')),
            (('--minify', 'true', '--minify', 'false'), dict(minify=False)),
            (('--out', '--all'), dict(out_dir='--all')),  # the value of --out is whatever follows it
            (('--strict', '--strict'), dict(strict=True)),
        ]
        for args, changes in cases:
            with self.subTest(args=args):
                self.assertEqual(run_args(*args), {**self.DEFAULTS, **changes})

    def test_the_variables_only_count_with_all(self):
        self.assertEqual(run_args(CSS_MINIFY='FALSE', CHECK_STRICT='FALSE'), self.DEFAULTS)
        off = run_args('--all', CSS_MINIFY='FALSE', CHECK_STRICT='FALSE')
        self.assertEqual((off['minify'], off['strict']), (False, False))
        half = run_args('--all', CSS_MINIFY='FALSE')
        self.assertEqual((half['minify'], half['strict']), (False, True))
        half = run_args('--all', CHECK_STRICT=' false ')
        self.assertEqual((half['minify'], half['strict']), (True, False))
        explicit = run_args('--all', '--strict', '--minify', 'true', CSS_MINIFY='FALSE', CHECK_STRICT='FALSE')
        self.assertEqual((explicit['minify'], explicit['strict']), (True, True))

    def test_without_environ_it_reads_os_environ(self):
        with mock.patch.dict(os.environ, {'CSS_MINIFY': 'FALSE', 'CHECK_STRICT': 'TRUE'}):
            options = build.parse_args(['--all'])
        self.assertEqual((options['minify'], options['strict']), (False, True))
        with mock.patch.dict(os.environ, {}, clear=True):
            options = build.parse_args(['--all'])
        self.assertEqual((options['minify'], options['strict']), (True, True))

    def test_the_result_has_exactly_these_keys_and_plain_booleans(self):
        options = run_args('--all')
        self.assertEqual(sorted(options), ['all', 'minify', 'no_validate', 'out_dir', 'strict'])
        for key in ('all', 'minify', 'no_validate', 'strict'):
            self.assertIsInstance(options[key], bool)

    def test_errors_have_the_exact_text_and_no_label(self):
        cases = [
            (('--out',), f'missing value for --out\n{USAGE}'),
            (('--minify',), f'missing value for --minify\n{USAGE}'),
            (('a', '--out'), f'unknown argument: a\n{USAGE}'),
            (('--minify', 'maybe'), f"--minify accepts true or false (got: 'maybe')\n{USAGE}"),
            (('--minify', ''), f"--minify accepts true or false (got: '')\n{USAGE}"),
            (('--bogus',), f'unknown argument: --bogus\n{USAGE}'),
            (('--ALL',), f'unknown argument: --ALL\n{USAGE}'),
            (('--all', '--no-validate'), f'--all always validates: drop --no-validate\n{USAGE}'),
            (('--no-validate', '--all'), f'--all always validates: drop --no-validate\n{USAGE}'),
            (('--strict', '--bogus', '--all'), f'unknown argument: --bogus\n{USAGE}'),
        ]
        for args, message in cases:
            with self.subTest(args=args):
                with self.assertRaises(build.BuildError) as ctx:
                    run_args(*args)
                self.assertEqual(str(ctx.exception), message)
                self.assertEqual(ctx.exception.label, '')

    def test_the_usage_line_names_every_option(self):
        for option in ('--all', '--out FOLDER', '--minify true|false', '--no-validate', '--strict'):
            self.assertIn(option, USAGE)
        self.assertTrue(USAGE.startswith('usage: build.py'))


class TestPrintReport(unittest.TestCase):
    def report(self, case):
        return G.console_of(case)

    def rows(self, case):
        return {line[3:18].strip(): line[20:70].strip() for line in self.report(case).splitlines()
                if line.startswith('║  ') and line[18:20] == ': '}

    def test_every_line_has_the_same_width(self):
        for case in G.CONSOLE_CASES:
            if case == 'LONG_PATH':
                continue  # a value longer than its column is not cut: the box widens (fixed by the golden)
            with self.subTest(case=case):
                widths = {len(line) for line in self.report(case).splitlines()}
                self.assertEqual(widths, {71})

    def test_the_box_is_closed_by_its_corners(self):
        for case in ('SUCCESS_CLEAN', 'FAILED_ERRORS'):
            with self.subTest(case=case):
                lines = self.report(case).splitlines()
                self.assertEqual(lines[0], '╔' + '═' * 69 + '╗')
                self.assertEqual(lines[-1], '╚' + '═' * 69 + '╝')

    def test_a_long_value_is_not_cut(self):
        self.assertIn(G.LONG_OUT, self.report('LONG_PATH'))
        self.assertIn('feature/' + 'b' * 40, self.report('LONG_PATH'))

    def test_success_and_failure_headers(self):
        self.assertIn('✓  BUILD SUCCESS', self.report('SUCCESS_CLEAN'))
        self.assertIn('Site ready for deployment', self.report('SUCCESS_CLEAN'))
        self.assertNotIn('BUILD FAILED', self.report('SUCCESS_CLEAN'))
        for case in ('FAILED_ERRORS', 'STRICT_WARNINGS'):
            text = self.report(case)
            self.assertIn('✗  BUILD FAILED', text)
            self.assertIn('Build aborted — fix errors above', text)
            self.assertNotIn('SIZE BREAKDOWN', text)
            self.assertNotIn('Site ready for deployment', text)
        self.assertEqual(self.rows('FAILED_ERRORS')['Status'], '✗  FAILED')
        self.assertEqual(self.rows('SUCCESS_CLEAN')['Status'], '✓  SUCCESS')

    def test_the_fixed_rows(self):
        rows = self.rows('SUCCESS_CLEAN')
        self.assertEqual({k: rows[k] for k in ('Branch', 'Commit', 'Build Time', 'Pages Generated', 'Total Size',
                                               'Output Dir', 'Minify')},
                         {'Branch': 'main', 'Commit': 'abc1234', 'Build Time': '2026-01-01 12:00:00',
                          'Pages Generated': '7', 'Total Size': '12,345 bytes', 'Output Dir': 'dist',
                          'Minify': 'True'})

    def test_size_breakdown_and_percentages(self):
        rows = self.rows('SUCCESS_CLEAN')
        self.assertEqual(rows['HTML Saved'], '2,000 bytes (20.0%)')
        self.assertEqual(rows['CSS Saved'], '1,000 bytes (25.0%)')
        self.assertEqual(rows['TOTAL Before'], '14,000 bytes')
        self.assertEqual(rows['TOTAL After'], '11,000 bytes')
        self.assertEqual(rows['TOTAL Saved'], '3,000 bytes (21.4%)')
        empty = self.rows('EMPTY_SIZES')
        self.assertEqual((empty['HTML Saved'], empty['CSS Saved'], empty['TOTAL Saved']),
                         ('0 bytes (0%)', '0 bytes (0%)', '0 bytes (0%)'))
        self.assertEqual(self.rows('EMPTY_SIZES')['Minify'], 'False')
        grew = self.rows('GREW')
        self.assertEqual(grew['HTML Saved'], '-1,000 bytes (-10.0%)')

    def test_warnings_and_errors_sections(self):
        self.assertIn('✓  No warnings', self.report('SUCCESS_CLEAN'))
        warned = self.report('SUCCESS_WARNINGS')
        self.assertIn('⚠  Warnings', warned)
        self.assertNotIn('treated as errors', warned)
        self.assertNotIn('✓  No warnings', warned)
        self.assertNotIn('✗  Errors', warned)
        self.assertIn('• index.html → title is short', warned)
        strict = self.report('STRICT_WARNINGS')
        self.assertIn('⚠  Warnings (treated as errors)', strict)
        failed = self.report('FAILED_ERRORS')
        self.assertIn('✗  Errors', failed)
        self.assertIn('• index.html → broken link /nowhere/', failed)
        self.assertNotIn('No warnings', failed)  # a failed build never says "No warnings"
        both = self.report('FAILED_ERRORS_AND_WARNINGS')
        self.assertLess(both.index('✗  Errors'), both.index('⚠  Warnings'))

    def test_it_prints_to_stdout_only_and_returns_nothing(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            result = build.print_report(banner='B', **{**G.REPORT_ARGS, 'success': True, 'errors': [], 'warnings': []})
        self.assertIsNone(result)
        self.assertEqual(err.getvalue(), '')

    def test_the_banner_comes_from_the_argument(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            build.print_report(banner='Another banner', **{**G.REPORT_ARGS, 'success': True, 'errors': [],
                                                           'warnings': []})
        self.assertIn('Another banner', out.getvalue())
        self.assertNotIn(build.REPORT_BANNER, out.getvalue())


if __name__ == '__main__':
    unittest.main()
