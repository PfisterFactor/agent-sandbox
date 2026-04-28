#!/usr/bin/env python3
"""
Render ghostty's terminfo source from upstream ghostty.zig.

Ghostty stores its terminfo definitions as Zig data (src/terminfo/ghostty.zig)
and renders them with a Zig program at build time. We don't want a Zig
toolchain in the Docker image, so we re-implement the encoder in Python
against the same data file. The output is consumed by `tic -x`.

Refresh by running this script and committing the resulting terminfo file.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

UPSTREAM = (
    "https://raw.githubusercontent.com/ghostty-org/ghostty/main/"
    "src/terminfo/ghostty.zig"
)

# Match `.{ .name = "X", .value = .{ .KIND = VALUE } },` where KIND is one of
# boolean / canceled / numeric / string. We capture across newlines because
# some string literals are very long but always live on a single source line.
CAP_RE = re.compile(
    r'\.\{\s*'
    r'\.name\s*=\s*"(?P<name>[^"]+)"\s*,\s*'
    r'\.value\s*=\s*\.\{\s*'
    r'\.(?P<kind>boolean|canceled|numeric|string)\s*=\s*'
    r'(?P<val>\{\s*\}|\d+|"(?:\\.|[^"\\])*")\s*'
    r'\}\s*,?\s*\}',
    re.DOTALL,
)

# The names array is an array of string literals between
# `.names = &.{` ... `},`. Strip line comments first, then collect literals.
NAMES_BLOCK_RE = re.compile(
    r'\.names\s*=\s*&\.\{(?P<body>.*?)\}\s*,', re.DOTALL
)
CAPS_BLOCK_RE = re.compile(
    r'\.capabilities\s*=\s*&\.\{(?P<body>.*?)\n\s*\}\s*,', re.DOTALL
)
STRING_LITERAL_RE = re.compile(r'"((?:\\.|[^"\\])*)"')
LINE_COMMENT_RE = re.compile(r'//[^\n]*')


def unescape_zig_string(s: str) -> str:
    """
    Convert a Zig string literal body into its raw byte sequence.
    Zig strings are a subset of C-style: \\n, \\r, \\t, \\\\, \\", \\'
    plus \\xNN. Ghostty also uses \\E (literal backslash-E) for ESC,
    which terminfo source format expects unchanged.
    """
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != '\\':
            out.append(ch)
            i += 1
            continue
        nxt = s[i + 1]
        if nxt == 'n':
            out.append('\n'); i += 2
        elif nxt == 'r':
            out.append('\r'); i += 2
        elif nxt == 't':
            out.append('\t'); i += 2
        elif nxt == '"':
            out.append('"'); i += 2
        elif nxt == "'":
            out.append("'"); i += 2
        elif nxt == '\\':
            # \\\\ in Zig is a single literal backslash.
            out.append('\\'); i += 2
        elif nxt == 'x' and i + 3 < len(s):
            out.append(chr(int(s[i + 2 : i + 4], 16))); i += 4
        else:
            # Anything else (e.g., \\E, \\,, \\007) is a backslash-prefixed
            # terminfo metasymbol — keep it verbatim so tic sees \E, \,, \007.
            out.append('\\' + nxt); i += 2
    return ''.join(out)


def parse(source: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    # Strip line comments so they don't fool the regexes.
    source = LINE_COMMENT_RE.sub('', source)

    names_match = NAMES_BLOCK_RE.search(source)
    caps_match = CAPS_BLOCK_RE.search(source)
    if not names_match or not caps_match:
        sys.exit('error: could not locate .names or .capabilities block')

    names = [
        unescape_zig_string(m.group(1))
        for m in STRING_LITERAL_RE.finditer(names_match.group('body'))
    ]

    caps: list[tuple[str, str, str]] = []
    for m in CAP_RE.finditer(caps_match.group('body')):
        name, kind, raw = m.group('name'), m.group('kind'), m.group('val')
        if kind == 'string':
            caps.append((name, kind, unescape_zig_string(raw[1:-1])))
        elif kind == 'numeric':
            caps.append((name, kind, raw))
        else:  # boolean | canceled
            caps.append((name, kind, ''))

    if not names:
        sys.exit('error: parsed zero names')
    if not caps:
        sys.exit('error: parsed zero capabilities')
    return names, caps


def encode(names: list[str], caps: list[tuple[str, str, str]]) -> str:
    # Mirror Source.zig's encode(): pipe-joined names, then tab-indented
    # capabilities, each followed by ',\n'. tic accepts this directly.
    out = ['|'.join(names) + ',\n']
    for name, kind, value in caps:
        if kind == 'boolean':
            out.append(f'\t{name},\n')
        elif kind == 'canceled':
            out.append(f'\t{name}@,\n')
        elif kind == 'numeric':
            out.append(f'\t{name}#{value},\n')
        elif kind == 'string':
            out.append(f'\t{name}={value},\n')
    return ''.join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        '--source',
        help='Path to a local ghostty.zig (default: fetch upstream main)',
    )
    ap.add_argument(
        '-o', '--output', default='ghostty.terminfo',
        help='Output terminfo source file (default: ghostty.terminfo)',
    )
    args = ap.parse_args()

    if args.source:
        zig = Path(args.source).read_text()
    else:
        with urllib.request.urlopen(UPSTREAM) as r:
            zig = r.read().decode()

    names, caps = parse(zig)
    Path(args.output).write_text(encode(names, caps))
    print(f'wrote {args.output}: {len(names)} name(s), {len(caps)} capability(ies)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
