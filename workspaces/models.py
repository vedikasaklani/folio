import hashlib
import secrets
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone
# Create your models here.
#user to workspace relationship

class Workspace(models.Model):
    name=models.CharField(max_length=200)
    description=models.TextField(blank=True)
    def __str__(self):
        return self.name


class TeamMember(models.Model):
    class Roles(models.TextChoices):
        OWNER='OW', 'Owner'
        ADMIN='AD', 'Admin'
        EDITOR='ED', 'Editor'
        VIEWER='VR', 'Viewer'
    member=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    workspace=models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    role=models.CharField(max_length=2, choices=Roles.choices, default=Roles.VIEWER)
    joined_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['member', 'workspace'], name='one_membership_per_user_per_workspace')]

    def __str__(self):
        return f'{self.member} - {self.workspace} ({self.get_role_display()})'


INVITE_TTL = timedelta(days=1)  # every invite link is valid for 24 hours; there is no per-link choice


def hash_token(token):
    # SHA-256, not a password hash: the token is 256 random bits, so there is nothing to brute-force and
    # a slow hash would only make every accept slower. A stolen database still cannot be turned back into links.
    return hashlib.sha256(token.encode()).hexdigest()


class Invite(models.Model):
    """A shareable join link. Only the hash of its token is stored; the token itself is shown once, at creation.
    Single use: the first person it adds uses it up (revoked_at is set), and it expires after a day anyway.
    It can grant any role except Owner (enforced by the database too)."""
    workspace=models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='invites')
    role=models.CharField(max_length=2, choices=TeamMember.Roles.choices)
    token_hash=models.CharField(max_length=64, unique=True)  # unique also builds the index the accept lookup uses
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at=models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField()
    revoked_at=models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints=[models.CheckConstraint(condition=~models.Q(role='OW'), name='invite_never_grants_owner')]

    def __str__(self):
        return f'{self.workspace} invite ({self.get_role_display()})'

    @property
    def is_active(self):
        return self.revoked_at is None and self.expires_at > timezone.now()

    @classmethod
    def issue(cls, workspace, role, created_by, ttl=INVITE_TTL):
        """Returns (invite, token). The token cannot be recovered later, so the caller must hand it out now."""
        if role == TeamMember.Roles.OWNER:
            raise ValueError('An invite link cannot grant Owner.')
        token = secrets.token_urlsafe(32)
        invite = cls.objects.create(workspace=workspace, role=role, created_by=created_by,
                                    token_hash=hash_token(token), expires_at=timezone.now() + ttl)
        return invite, token

    @classmethod
    def find_active(cls, token, lock=False):
        """The invite for this token, or None. Unknown, expired and revoked all look the same on purpose,
        so nobody can probe which tokens ever existed. lock=True holds the invite row until the transaction ends."""
        qs = cls.objects.select_related('workspace')
        if lock:
            qs = qs.select_for_update(of=('self',))  # only the invite row, not the joined workspace
        return qs.filter(token_hash=hash_token(token), revoked_at__isnull=True, expires_at__gt=timezone.now()).first()

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])
