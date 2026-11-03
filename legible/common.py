"""legible: code shared by build.py and check_site.py (settings, errors, file I/O, git, report).

It imports nothing from the other modules, so neither of them needs a circular import.
Keep the syntax of this file old on purpose: that way a Python older than MIN_PYTHON reaches
the clear message below instead of a SyntaxError.
"""
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

# Single place that says which Python the project supports. Raising it (for example to 3.11 when 3.10
# stops being supported) means changing this tuple.
MIN_PYTHON = (3, 10)

if sys.version_info < MIN_PYTHON:
    sys.exit('Python %d.%d or newer is required (found %s).'
             % (MIN_PYTHON[0], MIN_PYTHON[1], '.'.join(str(n) for n in sys.version_info[:3])))


class BuildError(Exception):
    """A problem the user can fix (bad data, bad option). `main()` prints it and exits with code 1.

    `label` is the word shown after the cross: "BUILD FAILED" by default, "BUILD ABORTED" when the build
    refuses to start (an unsafe output folder), none ('') for a bad option or a bad SITE_URL.
    """

    def __init__(self, message, label='BUILD FAILED'):
        super().__init__(message)
        self.label = label


def read_text(path):
    return Path(path).read_text(encoding='utf-8')


def write_text(path, text):
    """Write UTF-8 with LF line endings on every platform."""
    Path(path).write_text(text, encoding='utf-8', newline='\n')


# Settings of site.json that no longer exist -> what replaces them. A site that still writes one fails with a
# clear message instead of silently losing the behaviour it expected.
REMOVED_SETTINGS = {
    'sitemap_base_order': 'the sitemap is now sorted by URL, with the home page first (the menu order only rules llms.txt)',
    'generated_content': 'the texts of the interface are now the `ui` object of site.json (its keys are the UI table of legible/build.py)',
}


def load_site_config(root):
    """Load `<root>/src/data/site.json`; a missing file is an empty configuration."""
    path = Path(root) / 'src' / 'data' / 'site.json'
    try:
        config = json.loads(read_text(path)) if path.exists() else {}
    except (OSError, ValueError) as exc:
        raise BuildError(f'could not read src/data/site.json: {exc}')
    if not isinstance(config, dict):
        raise BuildError('src/data/site.json must contain a JSON object')
    for key, why in REMOVED_SETTINGS.items():
        if key in config:
            raise BuildError(f'src/data/site.json: "{key}" was removed: {why}. Delete it.')
    return config


def resolve_site_url(config, override=None):
    """Public URL of the site, without a trailing slash.

    Precedence: `override` (a command-line option), the SITE_URL environment variable, `site_url` in
    site.json. An empty value counts as not set. Raises BuildError if the result is not an https URL.
    """
    url = (override or os.environ.get('SITE_URL') or config.get('site_url', '')).strip().rstrip('/')
    if not re.fullmatch(r'https://[^\s/]+(?::\d+)?(?:/[^\s]*)?', url):
        raise BuildError(f'SITE_URL must start with https:// (current value: {url!r}); check src/data/site.json', label='')
    return url


def get_git_info(root):
    """(branch, commit) for the reports. Git is optional: any failure gives 'unknown'."""
    git_branch = os.environ.get('RENDER_GIT_BRANCH')
    git_commit = os.environ.get('RENDER_GIT_COMMIT')
    if not git_branch:
        try:
            git_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=root, text=True,
                                                 stderr=subprocess.DEVNULL).strip()
            if git_branch == 'HEAD':
                git_branch = None
        # Git metadata is optional; any Git failure must not abort the build.
        except Exception:
            pass
    if not git_branch:
        git_branch = 'unknown'
    if not git_commit:
        try:
            git_commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=root, text=True,
                                                 stderr=subprocess.DEVNULL).strip()
        # Git metadata is optional; fall back to 'unknown' on any Git failure.
        except Exception:
            git_commit = 'unknown'
    else:
        git_commit = git_commit[:7]
    return git_branch, git_commit


def report_lines(items, width):
    """Lines of a boxed report: each message is wrapped to `width` columns (not truncated) so the whole error is readable."""
    out = []
    for where, msg in items:
        out.extend(textwrap.wrap(f'• {where} → {msg}', width=width, subsequent_indent='  ',
                                 break_long_words=True, break_on_hyphens=False) or [''])
    return out


def fail(error):
    """Print a BuildError the way every command does and return the exit code."""
    print(f'✗ {error.label}: {error}' if error.label else f'✗ {error}', file=sys.stderr)
    return 1
