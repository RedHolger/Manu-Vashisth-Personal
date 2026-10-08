"""A small corpus of public project documentation, with provenance.

P05-04 needs a corpus that is *licensed*, not merely synthetic: every document
here is a verbatim excerpt of a public documentation file, stored under
`corpus/raw/` exactly as fetched, together with the license file of
the project it came from. `manifest()` records where each file came from, when,
under which license, and the sha256 of the raw file, the license file and the
extracted prose — so anyone can re-fetch, re-hash and confirm that the text the
evaluation ran on is the text those licenses cover.

Sources (all fetched 2026-10-06):

* **FastAPI** — MIT, copyright Sebastián Ramírez.
* **uvicorn**, **httpx**, **Starlette** — BSD 3-Clause, copyright Encode OSS Ltd.

Both licenses permit redistribution of the documentation with the copyright
notice retained; `corpus/licenses/` keeps the notice files verbatim.

The raw Markdown is *not* what gets ingested: documentation is mostly code
fences, tables and directives. `extract_prose()` strips those and keeps the
sentences, which is the text that reaches the store. The extraction is
deterministic and its output is hashed in the manifest, so the step is auditable
even though it is a transformation of the licensed source.
"""
import hashlib
import json
import re
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent / 'corpus'
RAW_DIR = CORPUS_DIR / 'raw'
LICENSE_DIR = CORPUS_DIR / 'licenses'
MANIFEST_PATH = CORPUS_DIR / 'manifest.json'
NOTICE_PATH = CORPUS_DIR / 'NOTICE.md'

BASE = 'https://raw.githubusercontent.com/'
SOURCES = (
    {
        'id': 'fastapi-path-params',
        'project': 'FastAPI',
        'copyright': 'Copyright (c) 2018 Sebastián Ramírez',
        'license_id': 'MIT',
        'license_name': 'The MIT License (MIT)',
        'license_url': 'https://github.com/tiangolo/fastapi/blob/master/LICENSE',
        'license_file': 'fastapi-MIT.txt',
        'retrieved_utc': '2026-10-06T08:06:24Z',
        'source_url': BASE + 'tiangolo/fastapi/master/docs/en/docs/tutorial/path-params.md',
        'raw': 'fastapi-path-params.md',
    },
    {
        'id': 'uvicorn-settings',
        'project': 'uvicorn',
        'copyright': 'Copyright © 2017-present, Encode OSS Ltd',
        'license_id': 'BSD-3-Clause',
        'license_name': 'BSD 3-Clause License',
        'license_url': 'https://github.com/encode/uvicorn/blob/master/LICENSE.md',
        'license_file': 'encode-uvicorn-BSD-3-Clause.txt',
        'retrieved_utc': '2026-10-06T08:05:12Z',
        'source_url': BASE + 'encode/uvicorn/master/docs/settings.md',
        'raw': 'uvicorn-settings.md',
    },
    {
        'id': 'uvicorn-server-behavior',
        'project': 'uvicorn',
        'copyright': 'Copyright © 2017-present, Encode OSS Ltd',
        'license_id': 'BSD-3-Clause',
        'license_name': 'BSD 3-Clause License',
        'license_url': 'https://github.com/encode/uvicorn/blob/master/LICENSE.md',
        'license_file': 'encode-uvicorn-BSD-3-Clause.txt',
        'retrieved_utc': '2026-10-06T08:08:21Z',
        'source_url': BASE + 'encode/uvicorn/master/docs/server-behavior.md',
        'raw': 'uvicorn-server-behavior.md',
    },
    {
        'id': 'httpx-quickstart',
        'project': 'httpx',
        'copyright': 'Copyright © 2019, Encode OSS Ltd',
        'license_id': 'BSD-3-Clause',
        'license_name': 'BSD 3-Clause License',
        'license_url': 'https://github.com/encode/httpx/blob/master/LICENSE.md',
        'license_file': 'encode-httpx-BSD-3-Clause.txt',
        'retrieved_utc': '2026-10-06T08:05:13Z',
        'source_url': BASE + 'encode/httpx/master/docs/quickstart.md',
        'raw': 'httpx-quickstart.md',
    },
    {
        'id': 'httpx-troubleshooting',
        'project': 'httpx',
        'copyright': 'Copyright © 2019, Encode OSS Ltd',
        'license_id': 'BSD-3-Clause',
        'license_name': 'BSD 3-Clause License',
        'license_url': 'https://github.com/encode/httpx/blob/master/LICENSE.md',
        'license_file': 'encode-httpx-BSD-3-Clause.txt',
        'retrieved_utc': '2026-10-06T08:08:21Z',
        'source_url': BASE + 'encode/httpx/master/docs/troubleshooting.md',
        'raw': 'httpx-troubleshooting.md',
    },
    {
        'id': 'starlette-requests',
        'project': 'Starlette',
        'copyright': 'Copyright © 2018, Encode OSS Ltd',
        'license_id': 'BSD-3-Clause',
        'license_name': 'BSD 3-Clause License',
        'license_url': 'https://github.com/encode/starlette/blob/master/LICENSE.md',
        'license_file': 'encode-starlette-BSD-3-Clause.txt',
        'retrieved_utc': '2026-10-06T08:05:13Z',
        'source_url': BASE + 'encode/starlette/master/docs/requests.md',
        'raw': 'starlette-requests.md',
    },
    {
        'id': 'starlette-responses',
        'project': 'Starlette',
        'copyright': 'Copyright © 2018, Encode OSS Ltd',
        'license_id': 'BSD-3-Clause',
        'license_name': 'BSD 3-Clause License',
        'license_url': 'https://github.com/encode/starlette/blob/master/LICENSE.md',
        'license_file': 'encode-starlette-BSD-3-Clause.txt',
        'retrieved_utc': '2026-10-06T08:07:44Z',
        'source_url': BASE + 'encode/starlette/master/docs/responses.md',
        'raw': 'starlette-responses.md',
    },
)

_HTML_COMMENT = re.compile(r'<!--.*?-->', re.S)
_FENCE = re.compile(r'```.*?```', re.S)
_OPEN_FENCE = re.compile(r'^\s*```.*$', re.M)
_SNIPPET = re.compile(r'^\s*\{.*\}\s*$', re.M)
_LINK_DEF = re.compile(r'^\[[^\]]+\]:\s+\S.*$', re.M)
_HTML_WRAPPER = re.compile(
    r'</?(?:a|span|dfn|abbr|code|em|strong|b|i|kbd|samp)\b[^>]*>', re.I)
_INLINE_ANCHOR = re.compile(r'\s*\{\s*#[^}]*\}\s*$')
_BLOCKQUOTE = re.compile(r'^>\s?')
_IMG_LINE = re.compile(r'^\s*<img\b.*$', re.M)
_INLINE_IMG = re.compile(r'!\[[^\]]*\]\([^)]*\)')
_MD_LINK_TEXT = re.compile(r'\[([^\]]+)\]\([^)]*\)')
_MD_REF_LINK = re.compile(r'\[([^\]]+)\]\[[^\]]*\]')
_BACKTICKS = re.compile(r'`([^`]*)`')
_BOLD = re.compile(r'\*\*([^*]+)\*\*')
_ITALIC = re.compile(r'(?<![\w])\*([^*\n]+)\*(?![\w])')
_LIST_BULLET = re.compile(r'^\s*[-*+]\s+')
_LIST_NUMBER = re.compile(r'^\s*\d+\.\s+')
_HEADING = re.compile(r'^\s*#{1,6}\s*')
_SETEXT = re.compile(r'^\s*(?:-{3,}|\*{3,}|={3,})\s*$')
_ADMONITION = re.compile(r'^\s*(?:!!!|\?\?\?|///)')
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'(\[])')
_LABEL_MAX_CHARS = 60
_LABEL_MAX_WORDS = 6
_LABEL_END = ('.', '!', '?', ';', ':', ',', ')', '"', "'", '`')


def _is_label(line):
    """A section heading: short, few words, no sentence-ending punctuation.

    Labels break a paragraph so that "Recap" does not get glued onto the
    sentence that follows it. Anything longer, or anything that ends in
    punctuation, is ordinary prose and belongs to its paragraph — a wrapped
    sentence such as "…we can inspect the / resulting URL … request:" must not
    be split in half.
    """
    return (len(line) <= _LABEL_MAX_CHARS
            and len(line.split()) <= _LABEL_MAX_WORDS
            and not line.endswith(_LABEL_END))


def _sha256(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def _inline(text):
    for pattern, replacement in ((_MD_LINK_TEXT, r'\1'),
                                 (_MD_REF_LINK, r'\1'),
                                 (_BACKTICKS, r'\1'),
                                 (_HTML_WRAPPER, ''),
                                 (_BOLD, r'\1'),
                                 (_ITALIC, r'\1')):
        text = pattern.sub(replacement, text)
    return re.sub(r'[ \t]+', ' ', text).strip()


def extract_prose(raw):
    """Deterministically turn a documentation file into prose lines.

    Code fences, snippet placeholders, admonition and mkdocstrings directives,
    tables, headings, images and link markup are removed first. What is left is
    assembled into paragraphs on blank-line boundaries, short trailing labels
    ("Recap", "Proxies") are kept on their own line, and every paragraph is then
    broken into sentences — one sentence per line.

    One sentence per line matters: the store splits chunks on sentence *and*
    newline boundaries, so emitting whole sentences means a sentence is never
    cut in half, and a claim lifted from a chunk is a real sentence of the
    licensed source rather than a fragment.
    """
    text = _HTML_COMMENT.sub(' ', raw)
    text = _FENCE.sub('\n', text)
    text = _OPEN_FENCE.sub('', text)
    text = _SNIPPET.sub('', text)
    text = _LINK_DEF.sub('', text)
    text = _IMG_LINE.sub('', text)
    text = _INLINE_IMG.sub('', text)

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append('')
            continue
        if _SETEXT.match(stripped) or _ADMONITION.match(stripped):
            continue
        if stripped.startswith(':::') or stripped == ':docstring:':
            continue
        if stripped.startswith('|') and stripped.endswith('|'):
            continue
        stripped = _HEADING.sub('', stripped)
        stripped = _BLOCKQUOTE.sub('', stripped)
        stripped = _LIST_NUMBER.sub('', stripped)
        stripped = _LIST_BULLET.sub('', stripped)
        stripped = _INLINE_ANCHOR.sub('', stripped).strip()
        if not stripped:
            continue
        lines.append(stripped)

    out = []
    buffer = []

    def flush():
        paragraph = ' '.join(buffer)
        del buffer[:]
        if not paragraph:
            return
        paragraph = _inline(paragraph)
        for sentence in _SENTENCE_SPLIT.split(paragraph):
            sentence = sentence.strip()
            if sentence:
                out.append(sentence)

    for line in lines:
        if not line:
            flush()
            continue
        if _is_label(line):
            flush()
            line = _inline(line)
            if line:
                out.append(line)
            continue
        buffer.append(line)
    flush()
    return '\n'.join(out)


def raw_text(source_id):
    source = _by_id(source_id)
    return (RAW_DIR / source['raw']).read_text(encoding='utf-8')


def _by_id(source_id):
    for source in SOURCES:
        if source['id'] == source_id:
            return source
    raise KeyError(source_id)


def documents():
    """The corpus as it will be ingested: one document per source file."""
    return [{'id': source['id'],
             'project': source['project'],
             'text': extract_prose(raw_text(source['id']))}
            for source in SOURCES]


def manifest():
    """Provenance plus hashes of raw source, license file and extracted prose."""
    entries = []
    for source in SOURCES:
        raw = (RAW_DIR / source['raw']).read_text(encoding='utf-8')
        license_text = (LICENSE_DIR / source['license_file']).read_text(
            encoding='utf-8')
        prose = extract_prose(raw)
        entries.append({
            'id': source['id'],
            'project': source['project'],
            'copyright': source['copyright'],
            'license_id': source['license_id'],
            'license_name': source['license_name'],
            'license_url': source['license_url'],
            'license_file': 'licenses/' + source['license_file'],
            'license_sha256': _sha256(license_text),
            'source_url': source['source_url'],
            'retrieved_utc': source['retrieved_utc'],
            'raw_file': 'raw/' + source['raw'],
            'raw_sha256': _sha256(raw),
            'raw_bytes': len(raw.encode('utf-8')),
            'extracted_sha256': _sha256(prose),
            'extracted_chars': len(prose),
            'extracted_lines': len(prose.splitlines()),
        })
    licenses = sorted({(entry['license_id'], entry['license_name'],
                        entry['license_url'], entry['license_file'],
                        entry['license_sha256'], entry['copyright'])
                       for entry in entries})
    return {
        'corpus_id': 'p05-04-licensed-documentation-v1',
        'purpose': 'held-out evaluation of retrieval recall, citation support '
                   'and abstention on a corpus that is not the synthetic '
                   'development fixture',
        'retrieval_method': 'HTTP GET of the raw file at source_url, stored '
                            'byte-for-byte under raw/',
        'extraction': 'licensed_corpus.extract_prose (deterministic; hashed)',
        'documents': entries,
        'licenses': [{'license_id': row[0], 'license_name': row[1],
                      'license_url': row[2], 'file': row[3],
                      'sha256': row[4], 'copyright': row[5]}
                     for row in licenses],
        'counts': {'documents': len(entries),
                   'projects': len({entry['project'] for entry in entries}),
                   'licenses': len(licenses),
                   'extracted_chars': sum(entry['extracted_chars']
                                          for entry in entries)},
    }


def verify(recorded=None):
    """Re-hash the on-disk corpus against a previously written manifest."""
    recorded = recorded or json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    current = manifest()
    problems = []
    by_id = {entry['id']: entry for entry in current['documents']}
    ids = [entry['id'] for entry in recorded['documents']]
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        problems.append('manifest document inventory differs from corpus')
    for entry in recorded['documents']:
        fresh = by_id.get(entry['id'])
        if fresh is None:
            problems.append('document %s is missing' % entry['id'])
            continue
        for key in ('raw_sha256', 'license_sha256', 'extracted_sha256'):
            if entry[key] != fresh[key]:
                problems.append('%s: %s changed' % (entry['id'], key))
    return problems


def write_manifest():
    MANIFEST_PATH.write_text(
        json.dumps(manifest(), indent=2, sort_keys=True) + '\n',
        encoding='utf-8')
    return MANIFEST_PATH


def write_notice():
    """The attribution file the two licenses require redistribution to carry."""
    lines = [
        '# Licensed corpus — attribution and provenance',
        '',
        'Every file under `raw/` was fetched verbatim from the URL recorded in',
        '`manifest.json` on the date recorded there, and is used under the',
        'license of the project it belongs to. The license texts are kept in',
        '`licenses/` and their sha256 is recorded in the manifest.',
        '',
        '| Document | Project | License | Copyright |',
        '|---|---|---|---|',
    ]
    for source in SOURCES:
        lines.append('| `%s` | %s | %s ([%s](%s)) | %s |' % (
            source['raw'], source['project'], source['license_id'],
            source['license_name'], source['license_url'],
            source['copyright']))
    lines += [
        '',
        'The MIT and BSD 3-Clause licenses both require the above copyright',
        'notice and this permission notice to be included in copies or',
        'substantial portions of the software; they are retained in',
        '`licenses/`. This folder redistributes documentation excerpts for',
        'evaluation purposes with attribution, which both licenses permit.',
        '',
        'Nothing else in this repository is derived from these files: the',
        'synthetic fixture in `labeled_corpus.py` is original work.',
        '',
    ]
    NOTICE_PATH.write_text('\n'.join(lines), encoding='utf-8')
    return NOTICE_PATH


if __name__ == '__main__':
    print('wrote', write_manifest())
    print('wrote', write_notice())
    print('verify:', verify() or 'clean')
