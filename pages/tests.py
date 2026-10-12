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

    def test_list_is_flat_scoped_and_one_query(self):
        Page.objects.create(workspace=self.other_ws, name='Secret')
        self.as_('viewer')
        with self.assertNumQueries(1):
            r = self.client.get('/api/pages/', {'workspace': self.ws.id})
        self.assertEqual([p['name'] for p in r.data], ['Root', 'Child'])
        self.assertEqual(r.data[1]['parent'], self.root.id)
        self.assertEqual(len(self.client.get('/api/pages/').data), 2)  # never sees Beta's page
        self.assertEqual(self.client.get('/api/pages/', {'workspace': self.other_ws.id}).data, [])
        self.assertEqual(self.client.get('/api/pages/', {'workspace': 'abc'}).status_code, 400)

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
