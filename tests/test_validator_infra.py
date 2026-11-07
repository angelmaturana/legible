#!/usr/bin/env python3
"""Infrastructure of `check_site.py`: `Findings`, `PageCtx`, the JSON-LD parsed once (`p.ld_docs`) (F5) and `PAGE_RULES` (F6).

    python3 -B -m unittest tests.test_validator_infra
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_validator_rules as T  # noqa: E402  (also puts legible/ in sys.path)

check_site = T.check_site

LD_OK = '{"@context": "https://schema.org", "@type": "WebSite"}'
LD_BAD = '{"@context": '
PAGE = '<html lang="en"><head><title>T</title>{blocks}</head><body><h1>H</h1></body></html>'


def ld_script(text):
    return f'<script type="application/ld+json">{text}</script>'


def parse(*blocks):
    p = check_site.PageParser()
    p.feed(PAGE.replace('{blocks}', ''.join(ld_script(b) for b in blocks)))
    return p


class TestFindings(unittest.TestCase):
    def test_starts_empty(self):
        f = check_site.Findings()
        self.assertEqual(f.errors, [])
        self.assertEqual(f.warnings, [])

    def test_error_and_warn_record_file_and_message_in_order(self):
        f = check_site.Findings()
        f.error('a.html', 'first')
        f.warn('b.html', 'second')
        f.error('c.html', 'third')
        self.assertEqual(f.errors, [('a.html', 'first'), ('c.html', 'third')])
        self.assertEqual(f.warnings, [('b.html', 'second')])

    def test_as_tuple_returns_errors_then_warnings(self):
        f = check_site.Findings()
        f.error('a.html', 'e')
        f.warn('a.html', 'w')
        errors, warnings = f.as_tuple()
        self.assertEqual(errors, [('a.html', 'e')])
        self.assertEqual(warnings, [('a.html', 'w')])

    def test_instances_do_not_share_lists(self):
        a, b = check_site.Findings(), check_site.Findings()
        a.error('x', 'y')
        self.assertEqual(b.errors, [])

    def test_wraps_the_lists_it_is_given_even_when_empty(self):
        errors, warnings = [], []
        f = check_site.Findings(errors, warnings)
        f.error('a.html', 'e')
        f.warn('a.html', 'w')
        self.assertIs(f.errors, errors)
        self.assertIs(f.warnings, warnings)
        self.assertEqual(errors, [('a.html', 'e')])
        self.assertEqual(warnings, [('a.html', 'w')])


class TestPageCtx(unittest.TestCase):
    def make(self):
        findings = check_site.Findings()
        ctx = check_site.PageCtx(rel_file='about/index.html', p=parse(), out=Path('dist'), site_url=T.URL,
                                 url=T.URL + '/about/', title='T', desc='D', indexable=True, is404=False,
                                 findings=findings)
        return ctx, findings

    def test_fields_are_kept(self):
        ctx, findings = self.make()
        self.assertEqual(ctx.rel_file, 'about/index.html')
        self.assertEqual(ctx.out, Path('dist'))
        self.assertEqual(ctx.site_url, T.URL)
        self.assertEqual(ctx.url, T.URL + '/about/')
        self.assertEqual((ctx.title, ctx.desc), ('T', 'D'))
        self.assertTrue(ctx.indexable)
        self.assertFalse(ctx.is404)
        self.assertIs(ctx.findings, findings)

    def test_E_and_W_record_a_finding_for_this_page(self):
        ctx, findings = self.make()
        ctx.E('an error')
        ctx.W('a warning')
        self.assertEqual(findings.errors, [('about/index.html', 'an error')])
        self.assertEqual(findings.warnings, [('about/index.html', 'a warning')])


class TestLdDocs(unittest.TestCase):
    def test_valid_block_is_parsed_without_error(self):
        p = parse(LD_OK)
        self.assertEqual(p.ld_docs, [(json.loads(LD_OK), None)])

    def test_invalid_block_keeps_the_error_and_no_data(self):
        (data, error), = parse(LD_BAD).ld_docs
        self.assertIsNone(data)
        self.assertIsInstance(error, ValueError)
        with self.assertRaises(ValueError) as expected:
            json.loads(LD_BAD)
        self.assertEqual(str(error), str(expected.exception))

    def test_null_is_valid_json_and_has_no_error(self):
        self.assertEqual(parse('null').ld_docs, [(None, None)])

    def test_one_entry_per_block_in_page_order(self):
        docs = parse(LD_OK, LD_BAD, '[1]').ld_docs
        self.assertEqual([error is None for _, error in docs], [True, False, True])
        self.assertEqual(docs[2][0], [1])

    def test_no_blocks_means_no_docs(self):
        p = parse()
        self.assertEqual(p.ld_raw, [])
        self.assertEqual(p.ld_docs, [])

    def test_ld_raw_is_kept_for_the_tests_that_read_it(self):
        self.assertEqual(parse(LD_OK, LD_BAD).ld_raw, [LD_OK, LD_BAD])

    def test_works_when_the_html_is_fed_without_close(self):
        p = check_site.PageParser()
        p.feed(PAGE.replace('{blocks}', ld_script(LD_OK)))
        self.assertEqual(len(p.ld_docs), 1)

    def test_each_block_is_parsed_once_however_many_times_it_is_read(self):
        p = parse(LD_OK, LD_BAD)
        with mock.patch.object(check_site.json, 'loads', wraps=json.loads) as loads:
            first = p.ld_docs
            second = p.ld_docs
            p.load_ld()
        self.assertEqual(loads.call_count, 2)
        self.assertIs(first, second)

    def test_a_change_in_ld_raw_is_noticed(self):
        p = parse(LD_OK)
        self.assertEqual(len(p.ld_docs), 1)
        p.ld_raw.append(LD_BAD)
        self.assertEqual(len(p.ld_docs), 2)

    def test_parse_page_parses_at_once(self):
        path = Path(T.tempfile.mkdtemp()) / 'x.html'
        path.write_text(PAGE.replace('{blocks}', ld_script(LD_OK)), encoding='utf-8')
        p = check_site.parse_page(path)
        with mock.patch.object(check_site.json, 'loads', wraps=json.loads) as loads:
            self.assertEqual(len(p.ld_docs), 1)
        self.assertEqual(loads.call_count, 0)


class TestRunChecksParsesJsonLdOnce(T._CleanBase):
    def test_every_block_of_the_site_is_parsed_exactly_once(self):
        blocks = []
        for path in sorted(self.clean_out.rglob('*.html')):
            blocks += check_site.parse_page(path).ld_raw
        self.assertTrue(blocks)
        real = json.loads
        seen = []

        def spy(text, *args, **kwargs):
            if text in blocks:
                seen.append(text)
            return real(text, *args, **kwargs)

        with mock.patch.object(check_site.json, 'loads', side_effect=spy):
            errors, warnings = check_site.run_checks(self.clean_out, T.URL)
        self.assertEqual((errors, warnings), ([], []))
        self.assertEqual(sorted(seen), sorted(blocks))


class TestFaqEntryPoints(T._CleanBase):
    def faq_page(self):
        html = ('<html lang="en"><body><details><summary>Q1</summary>A1</details></body></html>'
                '<script type="application/ld+json">'
                '{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "Q1", '
                '"acceptedAnswer": {"@type": "Answer", "text": "Other"}}]}</script>')
        p = check_site.PageParser()
        p.feed(html)
        return p

    def test_public_function_keeps_the_old_order_warnings_then_errors(self):
        errors, warnings = [], []
        check_site.check_faq_matches_schema('x.html', self.faq_page(), warnings, errors)
        self.assertEqual(errors, [('x.html', 'FAQ answer differs between JSON-LD and visible text: "Q1"')])
        self.assertEqual(warnings, [])

    def test_aligned_function_takes_errors_then_warnings(self):
        errors, warnings = [], []
        check_site._faq_matches_schema('x.html', self.faq_page(), errors, warnings)
        self.assertEqual(len(errors), 1)
        self.assertEqual(warnings, [])


class TestPageRules(unittest.TestCase):
    """F6: the order of `PAGE_RULES` is the order of the messages."""

    EXPECTED = (
        'rules_head', 'rules_canonical', 'rules_social', 'rules_headings', 'rules_images',
        'rules_link_safety', 'rules_sample_domains', 'rules_aria', 'rules_leftovers', 'rules_content',
        'rules_jsonld',
    )

    def test_page_rules_names_and_order(self):
        self.assertEqual(tuple(rule.__name__ for rule in check_site.PAGE_RULES), self.EXPECTED)

    def test_check_page_runs_every_rule_in_order_with_one_context(self):
        calls = []
        spies = tuple(lambda ctx, n=name: calls.append((n, ctx)) for name in self.EXPECTED)
        errors, warnings = [], []
        with mock.patch.object(check_site, 'PAGE_RULES', spies):
            check_site.check_page('about/index.html', parse(LD_OK), Path('.'), 'https://x.test', errors, warnings)
        self.assertEqual([name for name, _ in calls], list(self.EXPECTED))
        ctx = calls[0][1]
        self.assertTrue(all(c is ctx for _, c in calls))
        self.assertEqual((ctx.rel_file, ctx.url, ctx.title, ctx.is404), ('about/index.html', 'https://x.test/about/', 'T', False))
        self.assertIs(ctx.findings.errors, errors)
        self.assertIs(ctx.findings.warnings, warnings)

    def test_rules_write_through_the_context(self):
        errors, warnings = [], []
        check_site.check_page('404.html', parse(LD_OK), Path('.'), 'https://x.test', errors, warnings)
        self.assertIn(('404.html', 'missing meta description'), errors)
        self.assertTrue(all(f == '404.html' for f, _ in errors + warnings))


if __name__ == '__main__':
    unittest.main()
