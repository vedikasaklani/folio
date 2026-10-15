from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import INVITE_TTL, Invite, TeamMember, hash_token
from .tests import make_workspace_with_roles

R = TeamMember.Roles


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
