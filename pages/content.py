"""Page body = a ProseMirror (TipTap) JSON document. Clients are untrusted, so the server only accepts
a whitelisted subset of the schema; everything else is rejected, never stripped silently.
The first node is the page title (`title`), and `name` / `text` are derived from the document."""

import re

MAX_BYTES = 500_000
MAX_DEPTH = 20

# A code block's language is a short lowercase name ("python", "typescriptreact", "c++"); it only ever becomes a CSS class.
# A pattern rather than a fixed list, because editors send many names and a closed list would turn a paste into a 400.
LANGUAGE = re.compile(r'[a-z0-9][a-z0-9+#._-]{0,29}')

# node type -> allowed attrs (name -> validator).
_int = lambda lo, hi: lambda v: isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi
NODES = {
    'paragraph': {},
    'heading': {'level': _int(2, 3)},
    'bulletList': {},
    'orderedList': {'start': _int(1, 1_000_000), 'type': lambda v: v is None},
    'listItem': {},
    'blockquote': {},
    'codeBlock': {'language': lambda v: v is None or (isinstance(v, str) and LANGUAGE.fullmatch(v) is not None)},
    'hardBreak': {},
    'drawing': {'id': _int(1, 2_000_000_000)},  # the strokes live in the Drawing table, never in the document
    'text': {},
}
# Formatting is stored as a *name* ("yellow"), never a CSS value: the client maps names to design tokens.
# Keep these in step with src/lib/palette.js (frontend/src/lib/palette.test.js fails if they drift).
TONES = {
    'highlight': ('yellow', 'pink', 'blue', 'olive'),
    'textColor': ('red', 'blue', 'olive', 'plum'),
    'fontSize': ('small', 'large', 'huge'),
}
MARKS = {
    'bold': {}, 'italic': {}, 'underline': {}, 'strike': {}, 'code': {},
    **{name: {'tone': tones} for name, tones in TONES.items()},
}


def _check_attrs(attrs, allowed, what):
    if attrs is None:
        return
    if not isinstance(attrs, dict):
        raise ValueError(f'{what}: attrs must be an object.')
    for key, value in attrs.items():
        if key not in allowed or not allowed[key](value):
            raise ValueError(f'{what}: attribute "{key}" is not allowed.')


def _check_mark(mark):
    if not isinstance(mark, dict) or mark.get('type') not in MARKS:
        raise ValueError('Text mark is not allowed.')
    spec = MARKS[mark['type']]
    attrs = mark.get('attrs') or {}
    # exactly the attributes the mark defines, each one of its allowed values
    if not isinstance(attrs, dict) or set(attrs) != set(spec) or any(attrs[k] not in spec[k] for k in spec):
        raise ValueError(f'{mark["type"]}: invalid attributes.')


def _check_node(node, depth):
    if depth > MAX_DEPTH:
        raise ValueError('Document is nested too deeply.')
    if not isinstance(node, dict) or node.get('type') not in NODES:
        raise ValueError(f'Node type "{node.get("type") if isinstance(node, dict) else node}" is not allowed.')
    kind = node['type']
    _check_attrs(node.get('attrs'), NODES[kind], kind)
    if kind == 'text':
        if not isinstance(node.get('text'), str):
            raise ValueError('Text node needs a string.')
        for mark in node.get('marks') or []:
            _check_mark(mark)
    elif node.get('marks'):
        raise ValueError(f'{kind} cannot carry marks.')
    children = node.get('content') or []
    if not isinstance(children, list) or (kind == 'text' and children):
        raise ValueError(f'{kind}: invalid content.')
    if kind == 'drawing' and (children or not (node.get('attrs') or {}).get('id')):
        raise ValueError('A drawing block needs an id and holds no content.')
    if kind == 'codeBlock' and any(c.get('type') != 'text' or c.get('marks') for c in children if isinstance(c, dict)):
        raise ValueError('A code block holds plain text only.')
    for child in children:
        _check_node(child, depth + 1)


def validate_doc(doc):
    """Raises ValueError with a user-facing message; the serializer turns it into a 400."""
    if not isinstance(doc, dict) or doc.get('type') != 'doc':
        raise ValueError('Content must be a document.')
    if len(str(doc)) > MAX_BYTES:
        raise ValueError('Document is too large.')
    blocks = doc.get('content') or []
    if not blocks or not isinstance(blocks[0], dict) or blocks[0].get('type') != 'title':
        raise ValueError('The first node must be the page title.')
    title = blocks[0]
    _check_attrs(title.get('attrs'), {}, 'title')
    for child in title.get('content') or []:
        if not isinstance(child, dict) or child.get('type') != 'text' or child.get('marks'):
            raise ValueError('The title is plain text.')
        _check_node(child, 2)
    for block in blocks[1:]:
        _check_node(block, 1)


def drawing_ids(doc):
    """Every drawing id in the document, in order, repeats kept."""
    found = [doc['attrs']['id']] if doc.get('type') == 'drawing' else []
    for child in doc.get('content') or []:
        found += drawing_ids(child)
    return found


def _text_of(node):
    if node.get('type') == 'text':
        return node['text']
    if node.get('type') == 'hardBreak':
        return '\n'
    return ''.join(_text_of(c) for c in node.get('content') or [])


def title_of(doc):
    return _text_of(doc['content'][0]).strip()[:200] or 'Untitled'


def plain_text(doc):
    """Body text, one block per line, for search / diffs / AI later. Excludes the title."""
    return '\n'.join(_text_of(b) for b in doc['content'][1:])
