#!/usr/bin/env python3
"""Validator tests (in process, standard library only): the og:image size warning and `--prelaunch`.

    python3 -B -m unittest discover tests

They use the fixture of `fixtures.py`, not the template in `src/`. The classes at the end (broken markup, sample
domains, nulls) build a copy of the template.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ.pop('SITE_URL', None)
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / 'legible'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import check_site  # noqa: E402
import fixtures  # noqa: E402


class FixtureProject(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        fixtures.make_project(self.root)

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(build.build(self.root, no_validate=True))
        return self.root / 'dist'


class TestOgImageSizeWarning(FixtureProject):
    def og_warnings(self, png):
        if png is not None:
            fixtures.write_bytes(self.root, 'src/static/images/og-image.png', png)
        out = self.build()
        _errors, warnings = check_site.run_checks(out, 'https://fixture.test')
        return [msg for rel, msg in warnings if rel == 'index.html' and msg.startswith('og:image')]

    def test_a_1200_by_630_image_gives_no_warning(self):
        self.assertEqual(self.og_warnings(fixtures.png_header(1200, 630)), [])

    def test_a_larger_image_with_the_same_ratio_gives_no_warning(self):
        self.assertEqual(self.og_warnings(fixtures.png_header(1600, 840)), [])

    def test_a_square_image_warns_about_the_ratio(self):
        warnings = self.og_warnings(fixtures.png_header(1200, 1200))
        self.assertEqual(len(warnings), 1)
        self.assertIn('1200x1200', warnings[0])

    def test_a_narrow_image_warns_even_with_the_right_ratio(self):
        warnings = self.og_warnings(fixtures.png_header(800, 420))
        self.assertEqual(len(warnings), 1)
        self.assertIn('800x420', warnings[0])

    def test_a_size_the_engine_could_not_read_warns_once(self):
        warnings = self.og_warnings(None)  # the fixture has no og-image.png: the markers are empty
        self.assertEqual(len(warnings), 1)
        self.assertIn('not numbers', warnings[0])


class TestPrelaunch(FixtureProject):
    def findings(self, build_first=True):
        out = self.build() if build_first else self.root / 'dist'
        return check_site.prelaunch_findings(self.root, out)

    def text_of(self, findings):
        return '\n'.join(' | '.join(f) for f in findings)

    def test_a_site_with_real_data_is_ready(self):
        self.assertEqual(self.findings(), [])

    def test_every_finding_has_a_file_a_description_and_an_action(self):
        fixtures.make_project(self.root, site={'site_name': 'Your Business', 'city': 'Your City'})
        findings = self.findings()
        self.assertTrue(findings)
        for finding in findings:
            self.assertEqual(len(finding), 3)
            self.assertTrue(all(isinstance(part, str) and part.strip() for part in finding), finding)

    def test_example_values_of_site_json_are_named_by_key(self):
        fixtures.make_project(self.root, site={'site_name': 'Your Business', 'contact_email': 'hello@example.com'})
        text = self.text_of(self.findings())
        self.assertIn('src/data/site.json | "site_name"', text)
        self.assertIn('src/data/site.json | "contact_email"', text)
        self.assertNotIn('"city"', text)

    def test_an_unmistakable_string_in_the_output_is_reported_once_with_its_files(self):
        fixtures.make_project(self.root, site={'site_name': 'Your Business'})
        text = self.text_of(self.findings())
        self.assertEqual(text.count('the output contains "Your Business"'), 1)
        self.assertIn('index.html', text)

    def test_the_sample_copy_comment_is_reported_with_its_page(self):
        fixtures.write(self.root, 'src/pages/about/index.html',
                       fixtures.page('About page of the fixture', '<!-- SAMPLE COPY: replace me -->'))
        text = self.text_of(self.findings())
        self.assertIn('src/pages/about/index.html', text)
        self.assertIn('SAMPLE COPY', text)

    def test_todo_and_confirm_in_the_visible_text_are_reported(self):
        fixtures.write(self.root, 'src/pages/about/index.html',
                       fixtures.page('About page of the fixture', '<p>TODO write this</p><p>Open at [CONFIRM hours]</p>'))
        text = self.text_of(self.findings())
        self.assertIn('visible text contains "TODO"', text)
        self.assertIn('visible text contains "[CONFIRM"', text)

    def test_todo_that_is_not_visible_is_not_reported(self):
        fixtures.write(self.root, 'src/pages/about/index.html',
                       fixtures.page('About page of the fixture', '<!-- TODO later --><script>var x = "TODO";</script>'
                                                                  '<p>Todos los derechos y TODOS los casos.</p>'))
        self.assertEqual(self.findings(), [])

    def test_a_missing_output_folder_is_a_finding_that_says_to_build(self):
        findings = self.findings(build_first=False)
        self.assertEqual(len(findings), 1)
        self.assertIn('build', findings[0][2])


class TestPrelaunchSiteUrl(FixtureProject):
    """Decision 7: with SITE_URL set (or `--site-url`), the `site_url` of site.json is not an example value."""

    SAMPLE = 'https://YOUR-DOMAIN.com'

    def findings(self, site_url_env=None, override=None):
        fixtures.make_project(self.root, site={'site_url': self.SAMPLE})
        env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
        if site_url_env:
            env['SITE_URL'] = site_url_env
        with mock.patch.dict(os.environ, env, clear=True):
            out = self.build()
            return '\n'.join(' | '.join(f) for f in check_site.prelaunch_findings(self.root, out, override))

    def test_without_the_variable_the_example_site_url_is_a_finding(self):
        self.assertIn('"site_url"', self.findings())

    def test_with_the_variable_the_site_url_of_site_json_is_not_a_finding(self):
        text = self.findings(site_url_env='https://real.example.org')
        self.assertNotIn('"site_url"', text)
        self.assertNotIn('YOUR-DOMAIN', text)

    def test_with_the_command_line_option_the_site_url_of_site_json_is_not_a_finding(self):
        self.assertNotIn('"site_url"', self.findings(site_url_env='https://real.example.org', override='https://real.example.org'))

    def test_the_other_example_values_are_still_findings_with_the_variable(self):
        fixtures.make_project(self.root, site={'site_url': self.SAMPLE, 'city': 'Your City'})
        with mock.patch.dict(os.environ, {'SITE_URL': 'https://real.example.org'}):
            out = self.build()
            text = '\n'.join(' | '.join(f) for f in check_site.prelaunch_findings(self.root, out))
        self.assertIn('"city"', text)
        self.assertNotIn('"site_url"', text)


class TemplateBuild(unittest.TestCase):
    """A copy of the template's `src/` and an output folder; `build_ok()` builds it in process (these tests need the
    template's JSON-LD and scripts, which the minimal fixture does not have)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.project = Path(tmp.name) / 'project'
        self.out = Path(tmp.name) / 'output'
        shutil.copytree(REPO / 'src', self.project / 'src', ignore=shutil.ignore_patterns('dist'))

    def build_ok(self):
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            ok = build.build(self.project, out_dir=self.out, minify=True, no_validate=True)
        self.assertTrue(ok, stdout.getvalue())


class TestBrokenMarkupDiagnosis(TemplateBuild):
    """Regression: a missing quote in `<script type="application/ld+json>` produced "0 h1", "no JSON-LD", "anchor
    #main not found" and "0 words", and none of them named the cause. A page that already fails now also gets
    an error that names the broken tag (first, the others stay). A page that does not fail gets nothing."""

    def setUp(self):
        super().setUp()
        import check_site
        self.check_site = check_site
        self.build_ok()
        self.home = self.out / 'index.html'
        self.original = self.home.read_text(encoding='utf-8')

    def _home_errors(self):
        errors, _ = self.check_site.run_checks(self.out, build.load_site(REPO).site_url)
        return [msg for rel, msg in errors if rel == 'index.html']

    def _break(self, old, new):
        self.assertIn(old, self.original)
        self.home.write_text(self.original.replace(old, new, 1), encoding='utf-8')

    def test_a_clean_page_gets_no_diagnosis(self):
        self.assertEqual(self._home_errors(), [])

    def test_a_quote_left_open_is_named_first_and_the_other_errors_stay(self):
        self._break('<script type="application/ld+json">', '<script type="application/ld+json>')
        errors = self._home_errors()
        self.assertGreater(len(errors), 1, 'the usual symptoms are still reported')
        self.assertIn('broken markup', errors[0])
        self.assertIn('<script>', errors[0])
        self.assertIn('application/ld+json', errors[0], 'the message shows the tag')
        self.assertEqual(sum('broken markup' in e for e in errors), 1)

    def test_a_script_with_no_closing_tag_is_named(self):
        self._break('<main', '<script>var b = 2;\n<main')
        errors = self._home_errors()
        self.assertIn('broken markup', errors[0])
        self.assertIn('no closing </script>', errors[0])

    def test_a_style_with_no_closing_tag_is_named(self):
        self._break('<main', '<style>p { color: red }\n<main')
        errors = self._home_errors()
        self.assertIn('broken markup', errors[0])
        self.assertIn('no closing </style>', errors[0])

    def test_a_page_with_no_other_error_is_never_given_the_diagnosis(self):
        """A `<` inside an attribute value looks like a broken tag but breaks nothing: the page must still pass."""
        self._break('</main>', '<p title="a <b c">x</p></main>')
        self.assertEqual(self._home_errors(), [])

    def test_the_finder_ignores_comments_and_script_bodies(self):
        find = self.check_site.find_broken_markup
        self.assertIsNone(find('<p>a</p><!-- <div class="x --><script>if (a<b && c>d) {}</script><p>b</p>'))
        self.assertIsNone(find('<a href="x" title="a > b">t</a>'))
        self.assertIn('never closes', find('<p>x</p><a href="x>link</a>'))


class TestSampleDomainUrls(TemplateBuild):
    """A link, image, canonical or JSON-LD URL that points to example.com, example.org or example.net is a copied
    example that was never replaced: a warning. Never the visible text, `mailto:` or `tel:`, nor the site's own
    domain (the tests build sites at example.org)."""

    def setUp(self):
        super().setUp()
        import check_site
        self.check_site = check_site

    def _urls(self, html, site='https://my-site.test'):
        page = self.check_site.PageParser()
        page.feed(html)
        page.close()
        return self.check_site.sample_domain_urls(page, site)

    def test_a_link_to_a_sample_domain_is_found(self):
        self.assertEqual(self._urls('<main><a href="https://example.com/x">x</a></main>'), ['https://example.com/x'])

    def test_every_place_a_url_can_live_is_looked_at(self):
        html = ('<head><link rel="canonical" href="https://example.org/"><meta property="og:url" content="https://www.example.net/a">'
                '<meta property="og:image" content="http://example.com/i.png"></head>'
                '<main><img src="https://example.com/p.png" alt="a"></main>'
                '<script type="application/ld+json">{"@graph": [{"@id": "https://example.org/#x", "url": "https://sub.example.com/u", '
                '"sameAs": "https://example.com/not-checked"}]}</script>')
        found = self._urls(html)
        for url in ('https://example.org/', 'https://www.example.net/a', 'http://example.com/i.png',
                    'https://example.com/p.png', 'https://example.org/#x', 'https://sub.example.com/u'):
            self.assertIn(url, found)
        self.assertNotIn('https://example.com/not-checked', found)

    def test_text_mailto_tel_and_look_alike_domains_are_ignored(self):
        html = ('<main><p>Write to https://example.com/x or info@example.com</p>'
                '<a href="mailto:info@example.com">m</a><a href="tel:+15550100">t</a>'
                '<a href="https://notexample.com/">n</a><a href="https://example.com.evil.test/">e</a></main>')
        self.assertEqual(self._urls(html), [])

    def test_the_sites_own_domain_is_not_a_sample(self):
        html = '<main><a href="https://example.org/about/">a</a></main>'
        self.assertEqual(self._urls(html, site='https://example.org'), [])
        self.assertEqual(self._urls(html, site='https://other.test'), ['https://example.org/about/'])

    def test_the_validator_warns_once_per_page_and_the_template_is_clean(self):
        self.build_ok()
        warnings = self.check_site.run_checks(self.out, build.load_site(REPO).site_url)[1]
        self.assertFalse([w for w in warnings if 'sample domain' in w[1]])
        home = self.out / 'index.html'
        text = home.read_text(encoding='utf-8')
        self.assertIn('</main>', text)
        home.write_text(text.replace('</main>', '<a href="https://example.com/x">x</a></main>', 1), encoding='utf-8')
        warnings = self.check_site.run_checks(self.out, build.load_site(REPO).site_url)[1]
        mine = [w for w in warnings if 'sample domain' in w[1]]
        self.assertEqual([w[0] for w in mine], ['index.html'])
        self.assertIn('https://example.com/x', mine[0][1])


class TestExplicitNullSettings(unittest.TestCase):
    """Regression: an explicit `null` used to stop the build with
    `AttributeError: 'NoneType' object has no attribute 'get'`. The `ui` null of site.json is tested in
    test_engine.py; here the validator keeps walking nulls."""

    def test_check_site_get_walks_nulls(self):
        import check_site
        self.assertIsNone(check_site._get({'a': None}, 'a', 'b'))
        self.assertIsNone(check_site._get(None, 'a'))
        self.assertEqual(check_site._get({'a': {'b': 'x'}}, 'a', 'b'), 'x')
        self.assertEqual(check_site._get({'a': {'b': 'x'}}, 'a', 'c'), None)

    def test_faq_with_a_null_accepted_answer_is_reported_not_a_crash(self):
        import check_site

        def errors_for(accepted):
            html = ('<main><details><summary>Q?</summary><p>Cats and dogs.</p></details></main>'
                    '<script type="application/ld+json">%s</script>' % json.dumps(
                        {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': 'Q?',
                                                              'acceptedAnswer': accepted}]}))
            page = check_site.PageParser()
            page.feed(html)
            page.close()
            errors = []
            check_site.check_faq_matches_schema('x.html', page, [], errors)
            return errors

        self.assertEqual(errors_for({'@type': 'Answer', 'text': 'Cats and dogs.'}), [])
        for accepted in (None, {'@type': 'Answer', 'text': None}, {}):
            errors = errors_for(accepted)
            self.assertEqual(len(errors), 1, accepted)
            self.assertIn('differs', errors[0][1])


if __name__ == '__main__':
    unittest.main()
