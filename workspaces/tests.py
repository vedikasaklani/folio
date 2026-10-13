from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import TeamMember, Workspace

User = get_user_model()
R = TeamMember.Roles


def make_workspace_with_roles(name='Acme'):
    """Returns (workspace, {'owner': user, 'admin': user, 'editor': user, 'viewer': user, 'outsider': user})."""
    ws = Workspace.objects.create(name=name)
    users = {}
    for label, role in [('owner', R.OWNER), ('admin', R.ADMIN), ('editor', R.EDITOR), ('viewer', R.VIEWER)]:
        users[label] = User.objects.create_user(f'{name}-{label}')
        TeamMember.objects.create(member=users[label], workspace=ws, role=role)
    users['outsider'] = User.objects.create_user(f'{name}-outsider')
    return ws, users


class WorkspaceApiTests(APITestCase):
    def setUp(self):
        self.ws, self.u = make_workspace_with_roles()
        self.url = f'/api/workspaces/{self.ws.id}/'

    def as_(self, label):
        self.client.force_authenticate(self.u[label])

    def test_create_makes_caller_owner(self):
        self.as_('outsider')
        r = self.client.post('/api/workspaces/', {'name': 'Mine'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['role'], R.OWNER)
        self.assertTrue(TeamMember.objects.filter(
            workspace_id=r.data['id'], member=self.u['outsider'], role=R.OWNER).exists())

    def test_outsider_sees_nothing_and_gets_404(self):
        self.as_('outsider')
        self.assertEqual(self.client.get('/api/workspaces/').data, [])
        for call in (self.client.get, self.client.delete):
            self.assertEqual(call(self.url).status_code, 404)
        self.assertEqual(self.client.patch(self.url, {'name': 'x'}).status_code, 404)

    def test_every_member_can_read_with_own_role(self):
        for label, role in [('owner', R.OWNER), ('admin', R.ADMIN), ('editor', R.EDITOR), ('viewer', R.VIEWER)]:
            self.as_(label)
            r = self.client.get(self.url)
            self.assertEqual((r.status_code, r.data['role']), (200, role), label)

    def test_update_owner_and_admin_only(self):
        for label, expected in [('owner', 200), ('admin', 200), ('editor', 403), ('viewer', 403)]:
            self.as_(label)
            r = self.client.patch(self.url, {'name': f'by-{label}'})
            self.assertEqual(r.status_code, expected, label)

    def test_delete_owner_only(self):
        for label in ('admin', 'editor', 'viewer'):
            self.as_(label)
            self.assertEqual(self.client.delete(self.url).status_code, 403, label)
        self.as_('owner')
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertFalse(Workspace.objects.filter(id=self.ws.id).exists())

    def test_list_query_count_is_constant_and_includes_members(self):
        for i in range(3):
            w = Workspace.objects.create(name=f'extra{i}')
            TeamMember.objects.create(member=self.u['viewer'], workspace=w)
        self.as_('viewer')
        with self.assertNumQueries(2):  # workspaces + one prefetch for all members
            data = self.client.get('/api/workspaces/').data
        self.assertEqual(len(data), 4)
        self.assertEqual([(m['username'], m['role'], m['is_you']) for m in data[0]['members']],
                         [('Acme-owner', R.OWNER, False), ('Acme-admin', R.ADMIN, False),
                          ('Acme-editor', R.EDITOR, False), ('Acme-viewer', R.VIEWER, True)])
        self.assertEqual(data[1]['members'], [{'username': 'Acme-viewer', 'role': R.VIEWER, 'is_you': True}])

    def test_create_response_lists_the_owner(self):
        self.as_('outsider')
        r = self.client.post('/api/workspaces/', {'name': 'Mine'})
        self.assertEqual(r.data['members'], [{'username': 'Acme-outsider', 'role': R.OWNER, 'is_you': True}])
