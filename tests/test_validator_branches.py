#!/usr/bin/env python3
"""Defensive branches of `check_site.py` that no rule row reaches (G2).

    python3 -B -m unittest tests.test_validator_branches

Each test pins what the code does today in a case that was never exercised (an empty `srcset` entry, a stylesheet
URL that is a folder, a missing sitemap...). Nothing here changes a message. Rows that fit the rule tables of
`test_validator_rules.py` are there; the rest are direct tests of the helper function.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'legible'))
import check_site  # noqa: E402
from test_validator_rules import URL, _CleanBase, _main  # noqa: E402


def parse(html):
    p = check_site.PageParser()
    p.feed(html)
    p.close()
    return p


class TestParserBranches(unittest.TestCase):
    def test_script_with_src_is_a_resource(self):
        self.assertEqual(parse('<script src="/js/a.js"></script>').resources, [('/js/a.js', 'script')])

    def test_srcset_candidates_are_resources_and_empty_ones_are_skipped(self):
        p = parse('<img src="/a.png" srcset="/b.png 1x, /c.png 2x,, ">')
        self.assertEqual(p.resources, [('/a.png', 'img'), ('/b.png', 'img'), ('/c.png', 'img')])
        self.assertEqual(parse('<source srcset="/d.webp">').resources, [('/d.webp', 'img')])

    def test_badly_nested_end_tag_closes_up_to_the_tag(self):
        p = parse('<div><span><b>x</div><p>y</p>')
        self.assertEqual(p._stack, [])

    def test_unmatched_end_tag_leaves_the_stack_alone(self):
        p = parse('<div>x</span>')
        self.assertEqual(p._stack, ['div'])

    def test_style_block_is_closed_and_its_text_is_not_page_text(self):
        p = parse('<style>body { color: red }</style><main><p>Hello</p></main>')
        self.assertFalse(p._in_style)
        self.assertNotIn('color', ' '.join(p.all_text))


class TestHelperBranches(unittest.TestCase):
    def test_unclosed_comment_hides_the_rest_and_reports_nothing(self):
        self.assertIsNone(check_site.find_broken_markup('<p>ok</p><!-- never closed <a href="x'))

    def test_same_page_anchor_has_no_file(self):
        self.assertEqual(check_site.resolve_internal('#top', Path('/nonexistent'), URL), (None, 'top', None))
        self.assertEqual(check_site.resolve_internal(URL + '#top', Path('/nonexistent'), URL), (None, 'top', None))

    def test_unparseable_url_is_not_a_sample_url(self):
        self.assertFalse(check_site._is_sample_url('http://[::1', 'fixture.test'))

    def test_graph_that_is_an_object_is_one_node(self):
        node = {'@type': 'Thing'}
        problems = []
        self.assertEqual(check_site._ld_nodes({'@graph': node}, problems), [node])
        self.assertEqual(problems, [])

    def test_protocol_relative_href_has_its_own_class(self):
        self.assertEqual(check_site._classify_href('//cdn.other.test/x', URL), 'protocol_relative')


class TestRunChecksBranches(_CleanBase):
    def test_protocol_relative_link_reports_nothing(self):
        out = self.mutated_files(_main('<a href="//other.test/">x</a>'))
        self.assertEqual(check_site.run_checks(out, URL), ([], []))

    def test_script_without_file_is_a_missing_resource(self):
        out = self.mutated_files(_main('<script src="/js/missing.js"></script>'))
        self.assertEqual(self.findings(out), [('E', 'index.html', 'missing resource (script): /js/missing.js')])

    def test_resource_that_is_a_folder_is_skipped(self):
        """`/css` is a folder of the output: `resolve_internal` answers with an error and the resource is not
        reported as missing (the same URL as a link would be reported by the link rule instead)."""
        out = self.mutated_files([('index.html', 'href="/css/site.css"', 'href="/css"')])
        self.assertEqual(check_site.run_checks(out, URL), ([], []))

    def test_without_sitemap_the_check_returns_in_silence(self):
        out = self.mutated('sitemap.xml', '', '')
        (out / 'sitemap.xml').unlink()
        # the sitemap check itself returns in silence; what is reported is the file and the <link rel="sitemap"> of each page
        expected = [('E', page, 'missing resource (link:sitemap): /sitemap.xml')
                    for page in ('404.html', 'about/index.html', 'index.html', 'legal/index.html')]
        self.assertEqual(self.findings(out), sorted(expected + [('E', 'sitemap.xml', 'required file missing')]))

    def test_another_user_agent_group_resets_disallow_all(self):
        robots = 'User-agent: *\nAllow: /\nUser-agent: BadBot\nDisallow: /\nSitemap: ' + URL + '/sitemap.xml\n'
        out = self.mutated('robots.txt', '', '')
        (out / 'robots.txt').write_text(robots, encoding='utf-8')
        self.assertEqual(check_site.run_checks(out, URL), ([], []))

    def test_disallow_all_with_spaces_is_still_an_error(self):
        robots = 'User-agent: *\nDisallow:   /   # all\nSitemap: ' + URL + '/sitemap.xml\n'
        out = self.mutated('robots.txt', '', '')
        (out / 'robots.txt').write_text(robots, encoding='utf-8')
        self.assertEqual(self.findings(out), [('E', 'robots.txt', 'Disallow: / for all crawlers (blocks the whole site)')])

    def test_page_that_cannot_be_reread_keeps_its_errors_without_a_cause(self):
        out = self.mutated('index.html', ' lang="en"', '')
        p = check_site.parse_page(out / 'index.html')
        (out / 'index.html').unlink()
        errors, warnings = [], []
        check_site._check_one_page('index.html', p, out, URL, errors, warnings)
        self.assertIn(('index.html', '<html> without lang attribute'), errors)
        self.assertFalse([e for e in errors if e[1].startswith('broken markup')])

    def test_site_url_comes_from_the_project_when_not_given(self):
        with mock.patch.object(check_site, 'REPO', self.clean_out.parent):
            self.assertEqual(check_site.run_checks(self.clean_out), ([], []))

    def test_missing_output_folder(self):
        gone = Path(self._tmp.name) / 'does-not-exist'
        self.assertEqual(check_site.run_checks(gone, URL),
                         ([(str(gone), 'the output folder does not exist: build first')], []))

    def test_output_folder_without_pages(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check_site.run_checks(d, URL), ([(d, 'no .html page found: the build is empty')], []))


if __name__ == '__main__':
    unittest.main()
