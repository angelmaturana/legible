#!/usr/bin/env python3
"""Golden test and public API test of the validator (standard library only).

    python3 -B -m unittest tests.test_validator_golden

GOLDEN. `tests/golden/check_site.json` stores, for the clean project and for every row of the rule tables of
`test_validator_rules.py` (`RULES`, `LD_RULES`, `SITE_RULES`, `MISSING_FILES`), the EXACT pair
`{"errors": [...], "warnings": [...]}` that `run_checks` returns: same texts, same order, no sorting. Keys are the rule
ids (R01...), plus `CLEAN` (the clean project) and `FAQ_OK` (a consistent FAQ). The file was generated from the
original code, before any refactor. If this test fails during the refactor it is a REGRESSION: restore the last green
copy of `check_site.py`; do not regenerate the file "to make it pass".

Regenerating (only when a rule or a row is added or changed ON PURPOSE, and reviewing the diff by hand):

    UPDATE_GOLDEN=1 python3 -B -m unittest tests.test_validator_golden.TestGolden.test_golden_matches

API. The public contract of `check_site.py` (the names `build.py` and the tests use) must stay importable and keep
its signature.
"""
import inspect
import json
import os
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_validator_rules as T  # noqa: E402  (also puts legible/ in sys.path)

check_site = T.check_site
GOLDEN = Path(__file__).resolve().parent / 'golden' / 'check_site.json'

# the 9 public names of docs/PLAN-refactor-check-site.md §1.4 and the parameters each one takes, in order
PUBLIC_API = {
    'run_checks': ['out_dir', 'site_url'],
    'prelaunch_findings': ['root', 'out', 'site_url_override'],
    'main': ['argv'],
    'PageParser': [],
    'find_broken_markup': ['text'],
    'sample_domain_urls': ['p', 'site_url'],
    'check_faq_matches_schema': ['rel_file', 'p', 'warnings', 'errors'],
    '_get': ['node', 'keys'],
}


class TestGolden(T._CleanBase):
    def raw(self, out):
        """What `run_checks` returns, as JSON-able lists, untouched (no sorting)."""
        errors, warnings = check_site.run_checks(out, T.URL)
        return {'errors': [list(e) for e in errors], 'warnings': [list(w) for w in warnings]}

    def collect(self):
        result = {'CLEAN': self.raw(self.clean_out)}
        for rule_id, page, old, new, *_ in T.RULES:
            result[rule_id] = self.raw(self.mutated(page, old, new))
        for rule_id, change, html, *_ in T.LD_RULES:
            result[rule_id] = self.raw(self.with_jsonld('index.html', change, html))
        for rule_id, changes, _expected in T.SITE_RULES:
            result[rule_id] = self.raw(self.mutated_files(changes))
        for rule_id, name, *_ in T.MISSING_FILES:
            out = self.mutated(name, '', '')
            (out / name).unlink()
            result[rule_id] = self.raw(out)
        result['FAQ_OK'] = self.raw(self.with_jsonld('index.html', T._faq(T.QUESTION), T.VISIBLE_FAQ))
        return result

    def test_golden_matches(self):
        current = self.collect()
        if os.environ.get('UPDATE_GOLDEN') == '1':
            GOLDEN.write_text(json.dumps(current, indent=1, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
            self.skipTest(f'golden regenerated: {GOLDEN} (review the diff by hand)')
        self.assertTrue(GOLDEN.exists(), 'tests/golden/check_site.json is missing; generate it with UPDATE_GOLDEN=1')
        golden = json.loads(GOLDEN.read_text(encoding='utf-8'))
        self.assertEqual(sorted(current), sorted(golden), 'the rule tables and the golden have different ids')
        for key in sorted(golden):
            with self.subTest(rule=key):
                self.assertEqual(current[key], golden[key])

    def test_golden_covers_every_row(self):
        golden = json.loads(GOLDEN.read_text(encoding='utf-8'))
        ids = {row[0] for table in (T.RULES, T.LD_RULES, T.SITE_RULES, T.MISSING_FILES) for row in table}
        self.assertEqual(set(golden), ids | {'CLEAN', 'FAQ_OK'})

    def test_golden_of_the_clean_project_is_empty(self):
        golden = json.loads(GOLDEN.read_text(encoding='utf-8'))
        self.assertEqual(golden['CLEAN'], {'errors': [], 'warnings': []})
        self.assertEqual(golden['FAQ_OK'], {'errors': [], 'warnings': []})

    def test_every_other_entry_reports_something(self):
        golden = json.loads(GOLDEN.read_text(encoding='utf-8'))
        for key, value in golden.items():
            if key not in ('CLEAN', 'FAQ_OK'):
                with self.subTest(rule=key):
                    self.assertTrue(value['errors'] or value['warnings'])

    def test_output_is_deterministic(self):
        self.assertEqual(self.raw(self.mutated('index.html', T.ROBOTS, '')),
                         self.raw(self.mutated('index.html', T.ROBOTS, '')))


class TestPublicApi(unittest.TestCase):
    def test_the_nine_public_names_exist(self):
        for name in list(PUBLIC_API) + ['SAMPLE_VALUES']:
            with self.subTest(name=name):
                self.assertTrue(hasattr(check_site, name))

    def test_functions_are_callable_with_the_expected_parameters(self):
        for name, params in PUBLIC_API.items():
            with self.subTest(name=name):
                obj = getattr(check_site, name)
                self.assertTrue(callable(obj))
                if name == 'PageParser':
                    self.assertTrue(inspect.isclass(obj))
                    continue
                found = [p.name for p in inspect.signature(obj).parameters.values()]
                # `_get(node, *keys)`: the variadic one is listed by name too
                self.assertEqual(found[:len(params)], params)

    def test_page_parser_is_an_html_parser_that_parses(self):
        from html.parser import HTMLParser
        p = check_site.PageParser()
        self.assertIsInstance(p, HTMLParser)
        p.feed('<html lang="en"><head><title>T</title></head><body><h1>H</h1></body></html>')
        self.assertEqual(p.lang, 'en')

    def test_sample_values_is_a_dict_of_text(self):
        self.assertIsInstance(check_site.SAMPLE_VALUES, dict)
        self.assertTrue(check_site.SAMPLE_VALUES)
        for key, value in check_site.SAMPLE_VALUES.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)

    def test_find_broken_markup_and_get_behave(self):
        self.assertIsNone(check_site.find_broken_markup('<p>fine</p>'))
        self.assertIn('never closes', check_site.find_broken_markup('<p>x</p>\n<a href="/x>y</a>'))
        self.assertEqual(check_site._get({'a': {'b': 'x'}}, 'a', 'b'), 'x')

    def test_run_checks_returns_two_lists_of_pairs(self):
        self.assertEqual(check_site.run_checks.__name__, 'run_checks')
        self.assertEqual(sorted(inspect.signature(check_site.run_checks).parameters), ['out_dir', 'site_url'])


if __name__ == '__main__':
    unittest.main()
