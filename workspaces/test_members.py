import threading
import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase

from . import members
from .models import TeamMember
from .tests import make_workspace_with_roles

R = TeamMember.Roles
User = get_user_model()


class MemberTestMixin:
    """URL and role helpers shared by the normal and the concurrent tests."""

    def build(self, name='Acme'):
        self.ws, self.u = make_workspace_with_roles(name)
        self.base = f'/api/workspaces/{self.ws.id}'

    def membership(self, label):
        return TeamMember.objects.get(workspace=self.ws, member=self.u[label])

    def role_of(self, label):
        return self.membership(label).role

    def set_role(self, label, role):
        TeamMember.objects.filter(workspace=self.ws, member=self.u[label]).update(role=role)

    def url(self, label):
        return f'{self.base}/members/{self.membership(label).id}/'


class MemberRulesTests(MemberTestMixin, APITestCase):
    def setUp(self):
        self.build()

    def as_(self, label):
        self.client.force_authenticate(self.u[label])

    def change(self, label, role):
        return self.client.patch(self.url(label), {'role': role}, format='json')

    def remove(self, label):
        return self.client.delete(self.url(label))

    def leave(self):
        return self.client.post(f'{self.base}/leave/')

    def second_owner(self, label='admin'):
        self.set_role(label, R.OWNER)

    # --- changing roles
    def test_only_owners_and_admins_can_change_roles(self):
        for label, expected in [('owner', 200), ('admin', 200), ('editor', 403), ('viewer', 403), ('outsider', 404)]:
            self.as_(label)
            self.assertEqual(self.change('editor', R.VIEWER).status_code, expected, label)
            self.assertEqual(self.role_of('editor'), R.VIEWER if expected == 200 else R.EDITOR, label)
            self.set_role('editor', R.EDITOR)

    def test_changing_a_role_returns_the_updated_member(self):
        self.as_('owner')
        r = self.change('editor', R.ADMIN)
        self.assertEqual((r.data['id'], r.data['username'], r.data['role'], r.data['is_you']),
                         (self.membership('editor').id, 'Acme-editor', R.ADMIN, False))

    def test_an_admin_can_never_touch_an_owner(self):
        self.as_('admin')
        self.assertEqual(self.change('owner', R.EDITOR).status_code, 403)
        self.assertEqual(self.remove('owner').status_code, 403)
        self.assertEqual(self.role_of('owner'), R.OWNER)

    def test_only_an_owner_can_make_an_owner(self):
        self.as_('admin')
        for label in ('editor', 'admin'):  # another member, and the admin promoting themselves
            self.assertEqual(self.change(label, R.OWNER).status_code, 403, label)
        self.assertEqual((self.role_of('editor'), self.role_of('admin')), (R.EDITOR, R.ADMIN))
        self.as_('owner')
        self.assertEqual(self.change('admin', R.OWNER).status_code, 200)
        self.assertEqual(self.role_of('admin'), R.OWNER)

    def test_admins_manage_other_admins_and_can_step_down(self):
        second = User.objects.create_user('Acme-admin2')
        TeamMember.objects.create(member=second, workspace=self.ws, role=R.ADMIN)
        self.u['admin2'] = second
        self.as_('admin')
        self.assertEqual(self.change('admin2', R.EDITOR).status_code, 200)
        self.assertEqual(self.change('admin', R.VIEWER).status_code, 200)  # an admin demoting themselves

    def test_the_role_must_be_a_real_role(self):
        self.as_('owner')
        for body in ({'role': 'god'}, {}, {'role': ''}):
            r = self.client.patch(self.url('editor'), body, format='json')
            self.assertEqual(r.status_code, 400, body)
            self.assertIn('role', r.data, body)
        self.assertEqual(self.role_of('editor'), R.EDITOR)

    def test_the_same_role_again_is_not_an_error(self):
        self.as_('owner')
        self.assertEqual(self.change('editor', R.EDITOR).status_code, 200)

    # --- removing members
    def test_only_owners_and_admins_can_remove_members(self):
        for label, expected in [('editor', 403), ('viewer', 403), ('outsider', 404), ('admin', 204), ('owner', 204)]:
            self.as_(label)
            target = 'editor' if label == 'viewer' else 'viewer'
            self.assertEqual(self.remove(target).status_code, expected, label)
            if expected == 204:
                self.assertFalse(TeamMember.objects.filter(workspace=self.ws, member=self.u[target]).exists(), label)
                TeamMember.objects.create(member=self.u[target], workspace=self.ws, role=R.VIEWER)

    def test_a_removed_member_loses_access_to_the_workspace(self):
        self.as_('owner')
        self.assertEqual(self.remove('viewer').status_code, 204)
        self.as_('viewer')
        self.assertEqual(self.client.get(self.base + '/').status_code, 404)

    # --- leaving
    def test_any_member_can_leave_and_then_loses_access(self):
        for label in ('admin', 'editor', 'viewer'):
            self.as_(label)
            self.assertEqual(self.leave().status_code, 204, label)
            self.assertFalse(TeamMember.objects.filter(workspace=self.ws, member=self.u[label]).exists(), label)
            self.assertEqual(self.client.get(self.base + '/').status_code, 404, label)

    def test_a_non_member_cannot_leave(self):
        self.as_('outsider')
        self.assertEqual(self.leave().status_code, 404)

    # --- the last-Owner rule
    def test_the_only_owner_cannot_demote_remove_or_leave(self):
        self.as_('owner')
        for r in (self.change('owner', R.ADMIN), self.remove('owner'), self.leave()):
            self.assertEqual(r.status_code, 409)
            self.assertIn('at least one Owner', str(r.data['detail']))
        self.assertEqual(self.role_of('owner'), R.OWNER)

    def test_with_two_owners_one_may_leave_and_then_the_other_is_protected(self):
        self.second_owner()
        self.as_('owner')
        self.assertEqual(self.leave().status_code, 204)
        self.as_('admin')
        self.assertEqual(self.leave().status_code, 409)
        self.assertEqual(self.change('admin', R.EDITOR).status_code, 409)
        self.assertEqual(self.role_of('admin'), R.OWNER)

    def test_demoting_the_other_owner_is_fine_until_one_is_left(self):
        self.second_owner()
        self.as_('owner')
        self.assertEqual(self.change('admin', R.EDITOR).status_code, 200)
        self.assertEqual(self.change('owner', R.EDITOR).status_code, 409)

    # --- scoping
    def test_a_member_id_from_another_workspace_is_a_404(self):
        other_ws, other_u = make_workspace_with_roles('Beta')
        foreign = TeamMember.objects.get(workspace=other_ws, member=other_u['viewer'])
        self.as_('owner')
        url = f'{self.base}/members/{foreign.id}/'
        self.assertEqual(self.client.patch(url, {'role': R.ADMIN}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.role, R.VIEWER)

    def test_an_unknown_member_id_is_a_404(self):
        self.as_('owner')
        self.assertEqual(self.client.delete(f'{self.base}/members/999999/').status_code, 404)


class LastOwnerRaceTests(MemberTestMixin, TransactionTestCase):
    """TransactionTestCase, not TestCase: a normal test runs inside one transaction on one connection, which would
    hide the race. Here every request thread gets its own connection and its own committed transactions."""

    def setUp(self):
        self.build()
        self.set_role('admin', R.OWNER)  # two Owners: either may go, but not both

    def race(self, calls):
        """Runs each (user, request function) in its own thread, released together. Returns the status codes."""
        barrier = threading.Barrier(len(calls))
        statuses = [None] * len(calls)

        def run(i, user, call):
            try:
                client = APIClient()
                client.force_authenticate(user)
                barrier.wait(timeout=10)
                statuses[i] = call(client).status_code
            finally:
                connections.close_all()  # each thread opened its own database connection

        threads = [threading.Thread(target=run, args=(i, user, call)) for i, (user, call) in enumerate(calls)]
        # Widen the window between "is there another Owner?" and "make the change": without the lock both requests
        # would pass that check, so this makes a missing lock fail every time instead of once in a while.
        real = members._check_not_last_owner

        def slow_check(*args, **kwargs):
            real(*args, **kwargs)
            time.sleep(0.3)

        with mock.patch.object(members, '_check_not_last_owner', slow_check):
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)
        return statuses

    def owners(self):
        return TeamMember.objects.filter(workspace=self.ws, role=R.OWNER).count()

    def test_two_owners_demoting_each_other_at_once_leave_exactly_one(self):
        owner, admin = self.membership('owner'), self.membership('admin')
        patch = lambda target: lambda c: c.patch(f'{self.base}/members/{target.id}/', {'role': R.EDITOR}, format='json')
        statuses = self.race([(self.u['owner'], patch(admin)), (self.u['admin'], patch(owner))])
        # The loser runs second, under the lock, and its own role is re-read: it was already demoted, so it may no
        # longer manage anyone (403). Without the re-read it would pass the old permission check and demote the winner.
        self.assertEqual(sorted(statuses), [200, 403])
        self.assertEqual(self.owners(), 1)

    def test_two_owners_demoting_themselves_at_once_leave_exactly_one(self):
        owner, admin = self.membership('owner'), self.membership('admin')
        step_down = lambda me: lambda c: c.patch(f'{self.base}/members/{me.id}/', {'role': R.EDITOR}, format='json')
        statuses = self.race([(self.u['owner'], step_down(owner)), (self.u['admin'], step_down(admin))])
        self.assertEqual(sorted(statuses), [200, 409])  # the second would have left no Owner
        self.assertEqual(self.owners(), 1)

    def test_two_owners_leaving_at_once_leave_exactly_one(self):
        leave = lambda c: c.post(f'{self.base}/leave/')
        statuses = self.race([(self.u['owner'], leave), (self.u['admin'], leave)])
        self.assertEqual(sorted(statuses), [204, 409])
        self.assertEqual(self.owners(), 1)

    def test_an_owner_removed_while_leaving_cannot_strand_the_workspace(self):
        owner, admin = self.membership('owner'), self.membership('admin')
        remove_admin = lambda c: c.delete(f'{self.base}/members/{admin.id}/')
        leave = lambda c: c.post(f'{self.base}/leave/')
        statuses = self.race([(self.u['owner'], remove_admin), (self.u['admin'], leave)])
        # whoever takes the lock first removes the admin; the other request then finds no such member (404)
        self.assertEqual(sorted(statuses), [204, 404])
        self.assertEqual(self.owners(), 1)
