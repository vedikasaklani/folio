import threading
import time
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import INVITE_TTL, Invite, TeamMember, hash_token
from .tests import make_workspace_with_roles

R = TeamMember.Roles
User = get_user_model()


class InviteModelTests(TestCase):
    def setUp(self):
        self.ws, self.u = make_workspace_with_roles('Acme')

    def issue(self, role=R.EDITOR, **kwargs):
        return Invite.issue(self.ws, role, self.u['admin'], **kwargs)

    def test_token_is_shown_once_and_only_its_hash_is_stored(self):
        invite, token = self.issue()
        self.assertEqual(invite.token_hash, hash_token(token))
        self.assertEqual(len(invite.token_hash), 64)
        invite.refresh_from_db()
        self.assertNotIn(token, [getattr(invite, f.name) for f in Invite._meta.fields])  # no column holds the raw token
        self.assertFalse(Invite.objects.filter(token_hash=token).exists())

    def test_tokens_are_long_and_never_repeat(self):
        tokens = [self.issue()[1] for _ in range(20)]
        self.assertEqual(len(set(tokens)), 20)
        self.assertTrue(all(len(t) >= 43 for t in tokens))  # 32 random bytes as url-safe base64

    def test_find_active_matches_only_the_real_token(self):
        invite, token = self.issue()
        self.assertEqual(Invite.find_active(token), invite)
        for wrong in ('', 'nope', token[:-1], token + 'x', token.swapcase()):  # base64 is case-sensitive
            self.assertIsNone(Invite.find_active(wrong), wrong)

    def test_expired_and_revoked_tokens_are_not_found(self):
        expired_invite, expired = self.issue(ttl=timedelta(seconds=-1))
        revoked_invite, revoked = self.issue()
        revoked_invite.revoke()
        self.assertIsNone(Invite.find_active(expired))
        self.assertIsNone(Invite.find_active(revoked))
        self.assertFalse(expired_invite.is_active)
        self.assertFalse(revoked_invite.is_active)

    def test_a_valid_invite_is_active(self):
        invite, _ = self.issue()
        self.assertTrue(invite.is_active)
        self.assertEqual(INVITE_TTL, timedelta(days=1))
        remaining = (invite.expires_at - timezone.now()).total_seconds()
        self.assertAlmostEqual(remaining, 24 * 3600, delta=60)  # valid for one day from now

    def test_revoking_twice_keeps_the_first_timestamp(self):
        invite, _ = self.issue()
        invite.revoke()
        first = invite.revoked_at
        invite.revoke()
        invite.refresh_from_db()
        self.assertEqual(invite.revoked_at, first)

    def test_a_link_can_never_grant_owner(self):
        with self.assertRaises(ValueError):
            Invite.issue(self.ws, R.OWNER, self.u['owner'])
        # even code that skips issue() is stopped, by the database's own check
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invite.objects.create(workspace=self.ws, role=R.OWNER, token_hash='x' * 64,
                                  expires_at=timezone.now() + timedelta(days=1))
        self.assertEqual(Invite.objects.count(), 0)

    def test_every_other_role_can_be_invited(self):
        for role in (R.ADMIN, R.EDITOR, R.VIEWER):
            invite, _ = self.issue(role)
            self.assertEqual(invite.role, role)

    def test_a_token_hash_can_only_exist_once(self):
        invite, _ = self.issue()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invite.objects.create(workspace=self.ws, role=R.VIEWER, token_hash=invite.token_hash,
                                  expires_at=timezone.now() + timedelta(days=1))

    def test_invites_outlive_their_creator_but_not_their_workspace(self):
        invite, token = self.issue()
        self.u['admin'].delete()
        invite.refresh_from_db()
        self.assertIsNone(invite.created_by)  # the link keeps working until it expires or is revoked
        self.assertEqual(Invite.find_active(token), invite)
        self.ws.delete()
        self.assertEqual(Invite.objects.count(), 0)


class InviteApiTests(APITestCase):
    def setUp(self):
        self.ws, self.u = make_workspace_with_roles('Acme')
        self.newcomer = User.objects.create_user('newcomer')
        self.second = User.objects.create_user('second')

    def create(self, label='admin', role=R.EDITOR):
        self.client.force_authenticate(self.u[label])
        return self.client.post(f'/api/workspaces/{self.ws.id}/invites/', {'role': role}, format='json')

    def accept(self, user, token):
        self.client.force_authenticate(user)
        return self.client.post('/api/invites/accept/', {'token': token}, format='json')

    def role_of(self, user):
        return TeamMember.objects.filter(workspace=self.ws, member=user).values_list('role', flat=True).first()

    def test_only_owners_and_admins_create_links(self):
        for label, expected in [('owner', 201), ('admin', 201), ('editor', 403), ('viewer', 403), ('outsider', 404)]:
            self.assertEqual(self.create(label).status_code, expected, label)

    def test_link_is_shown_once_and_stored_hashed(self):
        r = self.create()
        token = r.data['token']
        invite = Invite.objects.get()
        self.assertEqual((invite.token_hash, invite.role, invite.created_by), (hash_token(token), R.EDITOR, self.u['admin']))
        self.assertFalse(Invite.objects.filter(token_hash=token).exists())
        self.assertAlmostEqual((invite.expires_at - timezone.now()).total_seconds(), INVITE_TTL.total_seconds(), delta=60)

    def test_each_link_is_its_own(self):
        tokens = {self.create('admin', role).data['token'] for role in (R.ADMIN, R.EDITOR, R.EDITOR, R.VIEWER)}
        tokens.add(self.create('owner', R.EDITOR).data['token'])
        self.assertEqual(len(tokens), 5)

    def test_link_roles(self):
        for role, expected in [(R.ADMIN, 201), (R.EDITOR, 201), (R.VIEWER, 201), (R.OWNER, 400), ('XX', 400), ('', 400)]:
            self.assertEqual(self.create('admin', role).status_code, expected, role)
        self.client.force_authenticate(self.u['owner'])
        self.assertEqual(self.client.post(f'/api/workspaces/{self.ws.id}/invites/', {}, format='json').status_code, 400)

    def test_accept_joins_with_the_links_role(self):
        token = self.create('admin', R.VIEWER).data['token']
        r = self.accept(self.newcomer, token)
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['id'], r.data['role']), (self.ws.id, R.VIEWER))
        self.assertIn('newcomer', [m['username'] for m in r.data['members']])
        self.assertEqual(self.role_of(self.newcomer), R.VIEWER)
        self.assertEqual(self.client.get(f'/api/workspaces/{self.ws.id}/').status_code, 200)  # now a member

    def test_a_link_works_once(self):
        token = self.create().data['token']
        self.assertEqual(self.accept(self.newcomer, token).status_code, 200)
        self.assertEqual(self.accept(self.second, token).status_code, 404)
        self.assertIsNone(self.role_of(self.second))

    def test_a_member_opening_a_link_keeps_their_role_and_the_link(self):
        token = self.create('owner', R.VIEWER).data['token']
        r = self.accept(self.u['admin'], token)
        self.assertEqual((r.status_code, r.data['role']), (200, R.ADMIN))
        self.assertEqual(self.accept(self.newcomer, token).status_code, 200)  # still unused

    def test_bad_links_all_look_the_same(self):
        expired, expired_token = Invite.issue(self.ws, R.EDITOR, self.u['admin'], ttl=timedelta(seconds=-1))
        revoked, revoked_token = Invite.issue(self.ws, R.EDITOR, self.u['admin'])
        revoked.revoke()
        used = self.create().data['token']
        self.accept(self.second, used)
        bodies = set()
        for token in (expired_token, revoked_token, used, 'not-a-real-token', 'x' * 100):
            r = self.accept(self.newcomer, token)
            self.assertEqual(r.status_code, 404, token)
            bodies.add(str(r.data))
        self.assertEqual(len(bodies), 1)
        self.assertIsNone(self.role_of(self.newcomer))

    def test_accept_needs_a_signed_in_user_and_a_token(self):
        token = self.create().data['token']
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/invites/accept/', {'token': token}, format='json').status_code, 401)
        self.client.force_authenticate(self.newcomer)
        for body in ({}, {'token': ''}, {'token': 'x' * 101}):
            self.assertEqual(self.client.post('/api/invites/accept/', body, format='json').status_code, 400, body)
        self.assertEqual(self.accept(self.newcomer, token).status_code, 200)  # the failed tries did not use it up


class InviteRaceTests(TransactionTestCase):
    """Two people open the same single-use link at the same moment: exactly one gets in."""

    def test_only_one_of_two_simultaneous_accepts_joins(self):
        ws, u = make_workspace_with_roles('Race')
        invite, token = Invite.issue(ws, R.EDITOR, u['owner'])
        people = [User.objects.create_user(f'racer{i}') for i in range(2)]
        barrier = threading.Barrier(2)
        statuses = [None, None]

        def run(i):
            try:
                client = APIClient()
                client.force_authenticate(people[i])
                barrier.wait(timeout=10)
                statuses[i] = client.post('/api/invites/accept/', {'token': token}, format='json').status_code
            finally:
                connections.close_all()

        real = Invite.revoke

        def slow_revoke(self):  # widen the gap between "the link is unused" and "mark it used"
            time.sleep(0.3)
            real(self)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(2)]
        with mock.patch.object(Invite, 'revoke', slow_revoke):
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)
        self.assertEqual(sorted(statuses), [200, 404])
        self.assertEqual(TeamMember.objects.filter(workspace=ws, member__in=people).count(), 1)
