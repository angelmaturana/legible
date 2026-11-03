#!/usr/bin/env python3
"""CSS and HTML minifiers used by build.py. Pure functions with no project knowledge (standard library only).
Moved out of build.py as they were (plan S2: the minifiers are not rewritten)."""
import json
import re


# What minify_css must not touch: comments (dropped), strings, unquoted url() and unicode-range.
_CSS_PROTECT = re.compile(
    r'/\*[\s\S]*?\*/'
    r'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''
    r'|\burl\([^)\'"]*\)'
    r'|(?<![\w-])[uU]\+[0-9A-Fa-f?]+(?:-[0-9A-Fa-f]+)?'
)
# Full CSS number (with sign and unit): so 0.0px, -0.50em or 1.0 are normalised in one pass.
_CSS_NUMBER = re.compile(r'(?<![\w.#])(-?)(\d*\.\d+|\d+\.?)([a-zA-Z%]*)')
# Length units that can be dropped after a 0. Excludes s, ms, deg, %, fr...: a unitless 0 is invalid there.
_CSS_ZERO_UNITS = frozenset('px em rem vh vw cm mm in pt pc ex ch vmin vmax'.split())

def _css_number(m):
    sign, num, unit = m.groups()
    ip, _, fp = num.partition('.')
    ip, fp = ip.lstrip('0'), fp.rstrip('0')
    if not ip and not fp:  # zero
        # In a custom property (--x: 0px) the unit may be needed inside a later calc().
        s = m.string
        ini = max(s.rfind(c, 0, m.start()) for c in '{};') + 1
        if unit.lower() in _CSS_ZERO_UNITS and not s[ini:m.start()].lstrip().startswith('--'):
            unit = ''
        return '0' + unit
    return sign + ip + ('.' + fp if fp else '') + unit

def minify_css(css_text: str) -> str:
    # 1) Protect strings, url() and unicode-range; drop comments (one pass: a "/*" inside a string is not a comment)
    protected = []
    def protect(m):
        if m.group(0).startswith('/*'):
            return ''
        protected.append(m.group(0))
        return f'__STR_{len(protected)-1}__'
    css = _CSS_PROTECT.sub(protect, css_text)

    # 2) Basic spacing
    css = re.sub(r'\s+', ' ', css)
    css = css.replace(' }', '}').replace(' {', '{').replace(': ', ':').replace(' ;', ';')
    css = re.sub(r';\s*}', '}', css)

    # 3) Math functions: inside calc()/min()/max()/clamp() only what is safe is compacted.
    #    "+" and "-" are left alone (CSS requires spaces around the operators, and "--x" or "-1px" are not operators).
    maths = []
    def extract_math(match):
        inner = re.sub(r'\s+', ' ', match.group(2))
        inner = re.sub(r'\s*,\s*', ',', inner)
        inner = re.sub(r'\(\s+', '(', inner)
        inner = re.sub(r'\s+\)', ')', inner).strip()
        maths.append(f'{match.group(1)}({inner})')
        return f'__MATH_{len(maths)-1}__'
    pattern = r'\b(calc|min|max|clamp)\(([^()]*(?:\([^()]*\)[^()]*)*)\)'
    while re.search(pattern, css):
        css = re.sub(pattern, extract_math, css)

    # 4) Numbers: 0px -> 0, 0.5 -> .5, 1.0 -> 1, 1.50 -> 1.5, 0.0px -> 0
    css = _CSS_NUMBER.sub(_css_number, css)

    # 5) Short hex colours: #AABBCC -> #ABC, #AABBCCDD -> #ABCD
    css = re.sub(
        r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3(?![0-9a-fA-F])',
        r'#\1\2\3', css
    )
    css = re.sub(
        r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3([0-9a-fA-F])\4(?![0-9a-fA-F])',
        r'#\1\2\3\4', css
    )

    # 6) Compact !important
    css = re.sub(r'\s*!\s*important\b', '!important', css)

    # 7) Spacing around punctuation. A space after ")" or before ":" can be significant
    #    (descendant combinator in "a:not(.b) .c" or "a :hover"; "and" in "(a) and (b)"), so it is kept.
    css = re.sub(r'\s*([{};,>~])\s*', r'\1', css)
    css = re.sub(r'\(\s+', '(', css)
    css = re.sub(r'\s+\)', ')', css)
    css = re.sub(r'\[\s+', '[', css)
    css = re.sub(r'\s+\]', ']', css)
    css = re.sub(r'\s*\+\s*', '+', css)

    # 8) Restore math functions (they can be nested) and strings
    while '__MATH_' in css:
        css = re.sub(r'__MATH_(\d+)__', lambda m: maths[int(m.group(1))], css)
    css = re.sub(r'__STR_(\d+)__', lambda m: protected[int(m.group(1))], css)

    # 9) Final cleanup
    css = re.sub(r';;+', ';', css)
    return css.strip()

# Inline elements: the space between two of them is part of the visible text.
INLINE_TAGS = frozenset('a abbr b bdi bdo br button cite code data del dfn em i img input ins kbd label mark q s '
                        'samp small span strong sub sup svg time u var wbr'.split())

VOID_INLINE_TAGS = frozenset(['br', 'img', 'input', 'wbr'])

def minify_html(html_text: str) -> str:
    protected = []

    def is_ld_json(tag_text: str) -> bool:
        return bool(
            re.match(r'<script[^>]*>', tag_text, re.IGNORECASE)
            and re.search(r'type\s*=\s*["\']application/ld\+json["\']', tag_text, re.IGNORECASE)
        )

    def protect(pattern, flags=0, json_checker=None):
        def replacer(m):
            idx = len(protected)
            original = m.group(0)
            is_json = bool(json_checker and json_checker(original))
            protected.append((original, is_json))
            # \x00 does not appear in normal HTML: a collision is practically impossible
            return f'\x00P{idx}\x00'
        return re.sub(pattern, replacer, html_text, flags=flags)

    # 1) Protect sensitive blocks (scripts, styles, pre, textarea)
    html_text = protect(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE, is_ld_json)
    html_text = protect(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
    html_text = protect(r'<pre[^>]*>.*?</pre>', re.DOTALL | re.IGNORECASE)
    html_text = protect(r'<textarea[^>]*>.*?</textarea>', re.DOTALL | re.IGNORECASE)

    # 2) Comments
    html_text = re.sub(r'<!--[\s\S]*?-->', '', html_text)

    # 3) Protect quoted attribute values BEFORE collapsing whitespace
    #    This fixes the bug: alt="a  b", content="x   y", title="z  w" stay intact.
    attr_strings = []
    def protect_attr(m):
        attr_strings.append(m.group(0))
        return f'\x00A{len(attr_strings)-1}\x00'
    html_text = re.sub(r'="[^"]*"|=\'[^\']*\'', protect_attr, html_text)

    # 4) Collapse whitespace between tags. Between two sibling inline elements
    #    (<strong>a</strong> <small>b</small>) the space is visible on screen: a single one is kept
    #    (temporary \x01). Between blocks, or between a container and its content, it is removed.
    html_text = re.sub(
        r'(<(/?)([a-zA-Z][\w-]*)[^<>]*>)\s+(?=<(/?)([a-zA-Z][\w-]*))',
        lambda m: m.group(1) + ('\x01' if (m.group(3).lower() in INLINE_TAGS and m.group(5).lower() in INLINE_TAGS
                                           and not m.group(4)
                                           and (m.group(2) or m.group(3).lower() in VOID_INLINE_TAGS)) else ''),
        html_text)
    html_text = re.sub(r'>\s+<', '><', html_text)
    html_text = html_text.replace('\x01', ' ')

    # 5) Collapse repeated spaces (now safe: only structural spaces between attributes remain)
    html_text = re.sub(r'\s{2,}', ' ', html_text)

    # 6) Remove spaces before > (leaving self-closing /> alone)
    html_text = re.sub(r'\s+>', '>', html_text)

    html_text = html_text.strip()

    # 7) Restore attribute values (single pass)
    html_text = re.sub(r'\x00A(\d+)\x00', lambda m: attr_strings[int(m.group(1))], html_text)

    # 8) Restore protected blocks (with JSON-LD minified, single pass)
    def _restore_block(m):
        original, is_json = protected[int(m.group(1))]
        if not is_json:
            return original
        match = re.match(r'<script[^>]*>(.*?)</script>', original, re.DOTALL | re.IGNORECASE)
        if not match:
            return original
        try:
            parsed = json.loads(match.group(1))
            minified_inner = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
            gt_pos = original.find('>')
            close_pos = original.rfind('</script>')
            if gt_pos != -1 and close_pos != -1:
                return original[:gt_pos + 1] + minified_inner + original[close_pos:]
        except ValueError:
            pass  # Preserve the original block when JSON-LD cannot be parsed.
        return original

    html_text = re.sub(r'\x00P(\d+)\x00', _restore_block, html_text)

    return html_text