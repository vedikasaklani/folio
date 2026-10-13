"""Page body = a ProseMirror (TipTap) JSON document. Clients are untrusted, so the server only accepts
a whitelisted subset of the schema; everything else is rejected, never stripped silently.
The first node is the page title (`title`), and `name` / `text` are derived from the document."""

MAX_BYTES = 500_000
MAX_DEPTH = 20

# node type -> allowed attrs (name -> validator).
_int = lambda lo, hi: lambda v: isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi
NODES = {
    'paragraph': {},
    'heading': {'level': _int(2, 3)},
    'bulletList': {},
    'orderedList': {'start': _int(1, 1_000_000), 'type': lambda v: v is None},
    'listItem': {},
    'blockquote': {},
    'hardBreak': {},
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
    'bold': {}, 'italic': {}, 'underline': {}, 'strike': {},
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
