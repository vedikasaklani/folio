from rest_framework.test import APITestCase

from workspaces.models import TeamMember
from workspaces.tests import make_workspace_with_roles

from .models import Page


class PageApiTests(APITestCase):
    def setUp(self):
        self.ws, self.u = make_workspace_with_roles('Acme')
        self.other_ws, self.other_u = make_workspace_with_roles('Beta')
        self.root = Page.objects.create(workspace=self.ws, name='Root')
        self.child = Page.objects.create(workspace=self.ws, name='Child', parent=self.root)
        self.url = f'/api/pages/{self.root.id}/'

    def as_(self, label):
        self.client.force_authenticate(self.u[label])

    def new_page(self, **extra):
        return self.client.post('/api/pages/', {'workspace': self.ws.id, 'name': 'New', **extra})

    def test_create_roles(self):
        for label, expected in [('owner', 201), ('admin', 201), ('editor', 201), ('viewer', 403), ('outsider', 400)]:
            self.as_(label)
            self.assertEqual(self.new_page().status_code, expected, label)

    def test_author_is_caller_not_client_supplied(self):
        self.as_('editor')
        r = self.new_page(author=self.u['owner'].id)
        self.assertEqual(r.data['author'], self.u['editor'].id)

    def test_read_all_members_outsider_404(self):
        for label in ('owner', 'admin', 'editor', 'viewer'):
            self.as_(label)
            self.assertEqual(self.client.get(self.url).status_code, 200, label)
        self.as_('outsider')
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_update_and_delete_roles(self):
        for label, expected in [('owner', 200), ('admin', 200), ('editor', 200), ('viewer', 403), ('outsider', 404)]:
            self.as_(label)
            self.assertEqual(self.client.patch(self.url, {'text': label}).status_code, expected, label)
        for label, expected in [('viewer', 403), ('outsider', 404), ('editor', 204)]:
            self.as_(label)
            self.assertEqual(self.client.delete(self.url).status_code, expected, label)
        self.assertFalse(Page.objects.filter(id=self.child.id).exists())  # CASCADE takes the subtree

    def names(self, **params):
        return [p['name'] for p in self.client.get('/api/pages/', params).data['results']]

    def test_list_is_one_level_scoped_and_one_query(self):
        Page.objects.create(workspace=self.other_ws, name='Secret')
        self.as_('viewer')
        with self.assertNumQueries(1):
            r = self.client.get('/api/pages/', {'workspace': self.ws.id, 'parent': 'null'})
        self.assertEqual([(p['name'], p['has_children']) for p in r.data['results']], [('Root', True)])
        self.assertNotIn('text', r.data['results'][0])
        r = self.client.get('/api/pages/', {'workspace': self.ws.id, 'parent': self.root.id})
        self.assertEqual([(p['name'], p['has_children'], p['parent']) for p in r.data['results']],
                         [('Child', False, self.root.id)])
        self.assertEqual(self.names(), ['Root', 'Child'])  # never sees Beta's page
        self.assertEqual(self.names(workspace=self.other_ws.id), [])
        for bad in ({'workspace': 'abc'}, {'parent': 'abc'}):
            self.assertEqual(self.client.get('/api/pages/', bad).status_code, 400)

    def test_list_is_cursor_paginated(self):
        Page.objects.bulk_create(Page(workspace=self.ws, name=f'p{i}') for i in range(25))
        self.as_('viewer')
        first = self.client.get('/api/pages/', {'workspace': self.ws.id, 'parent': 'null'}).data
        self.assertEqual(len(first['results']), 20)
        second = self.client.get(first['next']).data
        self.assertEqual(len(second['results']), 6)  # 26 roots in total
        self.assertIsNone(second['next'])
        ids = [p['id'] for p in first['results'] + second['results']]
        self.assertEqual(len(set(ids)), 26)

    def test_cannot_create_in_workspace_you_are_not_in(self):
        self.client.force_authenticate(self.other_u['owner'])
        self.assertEqual(self.new_page().status_code, 400)
        self.assertEqual(Page.objects.filter(workspace=self.ws).count(), 2)

    def test_bad_parents_are_400_not_500(self):
        self.as_('editor')
        foreign = Page.objects.create(workspace=self.other_ws, name='Foreign')
        self.assertEqual(self.new_page(parent=foreign.id).status_code, 400)  # parent not visible to caller
        # now visible to the caller, but in a different workspace than the new page
        TeamMember.objects.create(member=self.u['editor'], workspace=self.other_ws, role='ED')
        self.assertEqual(self.new_page(parent=foreign.id).status_code, 400)
        self.assertEqual(self.client.patch(self.url, {'parent': self.root.id}).status_code, 400)  # own parent
        self.assertEqual(self.client.patch(self.url, {'parent': self.child.id}).status_code, 400)  # cycle
        self.root.refresh_from_db()
        self.assertIsNone(self.root.parent)

    def test_cannot_move_page_to_another_workspace(self):
        self.as_('editor')
        TeamMember.objects.create(member=self.u['editor'], workspace=self.other_ws, role='ED')
        r = self.client.patch(self.url, {'workspace': self.other_ws.id})
        self.assertEqual(r.status_code, 400)


def doc(title='Plan', *blocks):
    return {'type': 'doc', 'content': [
        {'type': 'title', 'content': [{'type': 'text', 'text': title}] if title else []}, *blocks]}


def para(text, *marks):
    return {'type': 'paragraph', 'content': [{'type': 'text', 'text': text, 'marks': [{'type': m} for m in marks]}]}


class PageContentTests(APITestCase):
    def setUp(self):
        self.ws, self.u = make_workspace_with_roles('Acme')
        self.page = Page.objects.create(workspace=self.ws, name='Old')
        self.url = f'/api/pages/{self.page.id}/'
        self.client.force_authenticate(self.u['editor'])

    def save(self, content):
        return self.client.patch(self.url, {'content': content}, format='json')

    def test_save_derives_name_and_text_from_the_document(self):
        body = [para('hello', 'bold'), {'type': 'heading', 'attrs': {'level': 2}, 'content': [{'type': 'text', 'text': 'H'}]},
                {'type': 'bulletList', 'content': [{'type': 'listItem', 'content': [para('x')]}]}]
        r = self.save(doc('Plan', *body))
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['name'], r.data['text']), ('Plan', 'hello\nH\nx'))
        self.page.refresh_from_db()
        self.assertEqual(self.page.content['content'][1]['content'][0]['marks'], [{'type': 'bold'}])

    def test_formatting_marks_are_saved_as_names(self):
        def mark(kind, tone):
            return {'type': kind, 'attrs': {'tone': tone}}
        styled = {'type': 'paragraph', 'content': [
            {'type': 'text', 'text': 'x', 'marks': [mark('highlight', 'yellow'), mark('textColor', 'plum'),
                                                    mark('fontSize', 'huge'), {'type': 'bold'}]}]}
        r = self.save(doc('T', styled))
        self.assertEqual(r.status_code, 200, r.data)
        self.page.refresh_from_db()
        self.assertEqual(self.page.content['content'][1], styled)  # stored exactly as sent
        self.assertEqual(self.page.text, 'x')

    def test_rejects_bad_formatting_values(self):
        def marked(*marks):
            return doc('T', {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'x', 'marks': list(marks)}]})
        bad = {
            'tone from another mark': {'type': 'highlight', 'attrs': {'tone': 'red'}},
            'hex instead of a name': {'type': 'highlight', 'attrs': {'tone': '#f6d868'}},
            'css instead of a name': {'type': 'textColor', 'attrs': {'tone': 'red; position: fixed'}},
            'unknown size': {'type': 'fontSize', 'attrs': {'tone': 'tiny'}},
            'missing attrs': {'type': 'highlight'},
            'empty attrs': {'type': 'textColor', 'attrs': {}},
            'null tone': {'type': 'fontSize', 'attrs': {'tone': None}},
            'tone is a list': {'type': 'highlight', 'attrs': {'tone': ['yellow']}},
            'extra attribute': {'type': 'highlight', 'attrs': {'tone': 'yellow', 'style': 'x'}},
            'attrs on a plain mark': {'type': 'bold', 'attrs': {'tone': 'yellow'}},
            'attrs not an object': {'type': 'highlight', 'attrs': 'yellow'},
            'mark is a string': 'bold',
        }
        for label, mark in bad.items():
            r = self.save(marked(mark))
            self.assertEqual(r.status_code, 400, label)
            self.assertIn('content', r.data, label)
        self.page.refresh_from_db()
        self.assertEqual(self.page.content, {})

    def test_code_blocks_keep_every_character(self):
        code = 'def f(x):\n\tif x:\n        return "caf\u00e9"  \n\n\n    pass\n'
        block = {'type': 'codeBlock', 'attrs': {'language': 'python'}, 'content': [{'type': 'text', 'text': code}]}
        inline = {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'run '},
                                                    {'type': 'text', 'text': 'ls -la', 'marks': [{'type': 'code'}]}]}
        r = self.save(doc('Snippets', block, inline, {'type': 'codeBlock', 'attrs': {'language': None}}))
        self.assertEqual(r.status_code, 200, r.data)
        self.page.refresh_from_db()
        self.assertEqual(self.page.content['content'][1]['content'][0]['text'], code)  # tabs, blank lines, trailing spaces
        self.assertEqual(self.page.text.split('\n')[:2], ['def f(x):', '\tif x:'])  # lines survive in the plain-text copy

    def test_code_language_is_a_plain_name(self):
        def block(language):
            return doc('T', {'type': 'codeBlock', 'attrs': {'language': language}, 'content': [{'type': 'text', 'text': 'x'}]})
        for ok in ('python', 'typescriptreact', 'c++', 'c#', 'objective-c', 'plaintext', None):
            self.assertEqual(self.save(block(ok)).status_code, 200, ok)
        for bad in ('Python', 'py thon', '"><script>', 'a' * 31, '', ['python'], 7, '../x'):
            r = self.save(block(bad))
            self.assertEqual(r.status_code, 400, repr(bad))
            self.assertIn('content', r.data, repr(bad))

    def test_rejects_malformed_code_blocks(self):
        text = {'type': 'text', 'text': 'x'}
        bad = {
            'paragraph inside': {'type': 'codeBlock', 'content': [{'type': 'paragraph', 'content': [text]}]},
            'bold inside': {'type': 'codeBlock', 'content': [{'type': 'text', 'text': 'x', 'marks': [{'type': 'bold'}]}]},
            'extra attribute': {'type': 'codeBlock', 'attrs': {'language': 'python', 'class': 'x'}, 'content': [text]},
            'marks on the block': {'type': 'codeBlock', 'marks': [{'type': 'bold'}], 'content': [text]},
            'code mark with attrs': {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'x', 'marks': [{'type': 'code', 'attrs': {'a': 1}}]}]},
        }
        for label, node in bad.items():
            r = self.save(doc('T', node))
            self.assertEqual(r.status_code, 400, label)
            self.assertIn('content', r.data, label)

    def test_title_wins_over_name_and_empty_title_is_untitled(self):
        r = self.client.patch(self.url, {'name': 'Ignored', 'content': doc('Real')}, format='json')
        self.assertEqual(r.data['name'], 'Real')
        self.assertEqual(self.save(doc('')).data['name'], 'Untitled')

    def test_text_is_not_client_writable(self):
        self.client.patch(self.url, {'text': 'forged'}, format='json')
        self.page.refresh_from_db()
        self.assertEqual(self.page.text, '')

    def test_viewer_cannot_save_content(self):
        self.client.force_authenticate(self.u['viewer'])
        self.assertEqual(self.save(doc()).status_code, 403)

    def test_rejects_anything_outside_the_whitelist(self):
        deep = para('x')
        for _ in range(25):
            deep = {'type': 'blockquote', 'content': [deep]}
        bad = {
            'unknown node': doc('T', {'type': 'script', 'content': []}),
            'unknown mark': doc('T', para('x', 'link')),
            'mark attrs': doc('T', {'type': 'paragraph', 'content': [
                {'type': 'text', 'text': 'x', 'marks': [{'type': 'bold', 'attrs': {'style': 'x'}}]}]}),
            'node attrs': doc('T', {'type': 'paragraph', 'attrs': {'onclick': 'x'}}),
            'h1 body heading': doc('T', {'type': 'heading', 'attrs': {'level': 1}, 'content': []}),
            'no title first': {'type': 'doc', 'content': [para('x')]},
            'empty doc': {'type': 'doc', 'content': []},
            'second title': doc('T', {'type': 'title', 'content': []}),
            'marked title': {'type': 'doc', 'content': [{'type': 'title', 'content': [
                {'type': 'text', 'text': 'x', 'marks': [{'type': 'bold'}]}]}]},
            'too deep': doc('T', deep),
            'too large': doc('T', para('x' * 600_000)),
            'not a doc': {'type': 'paragraph'},
            'list not object': ['x'],
        }
        for label, content in bad.items():
            r = self.save(content)
            self.assertEqual(r.status_code, 400, label)
            self.assertIn('content', r.data, label)
        self.page.refresh_from_db()
        self.assertEqual(self.page.content, {})

    def test_absurdly_nested_json_is_400_not_500(self):
        r = self.client.patch(self.url, '{"content":' + '[' * 20000 + ']' * 20000 + '}', content_type='application/json')
        self.assertEqual(r.status_code, 400)
