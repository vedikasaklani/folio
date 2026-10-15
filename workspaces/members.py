"""Changing who is in a workspace: change a role, remove a member, leave.

The rules that protect a workspace's people live here, not in the views, so they can be tested without HTTP and
no endpoint can forget one:
  - only Owners and Admins manage members, and an Admin can never touch an Owner or make one;
  - a workspace always keeps at least one Owner.

Every function takes a lock on the workspace row first. Two requests changing the same workspace therefore run one
after the other, and the role checks and the Owner count are read after the lock, so they cannot go stale.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, NotFound, PermissionDenied

from .models import Invite, TeamMember, Workspace
from .permissions import CAN_MANAGE

R = TeamMember.Roles


class LastOwnerError(APIException):
    status_code = 409  # the request is valid, but it clashes with the workspace's current state
    default_detail = 'A workspace needs at least one Owner. Make someone else an Owner first.'
    default_code = 'last_owner'


def _lock_and_load_actor(workspace, user):
    Workspace.objects.select_for_update().get(pk=workspace.pk)  # blocks until any other change to this workspace commits
    try:
        # Re-read the caller's membership under the lock: the role the permission check saw may be seconds old.
        return TeamMember.objects.get(workspace=workspace, member=user)
    except TeamMember.DoesNotExist:
        raise NotFound()


def _check_may_touch(actor, target, new_role=None):
    if actor.role not in CAN_MANAGE:
        raise PermissionDenied()
    if actor.role != R.OWNER and (target.role == R.OWNER or new_role == R.OWNER):
        raise PermissionDenied('Only an Owner can change an Owner or make someone an Owner.')


def _check_not_last_owner(target, new_role=None):
    """Refuses any change that would leave the workspace without an Owner."""
    if target.role != R.OWNER or new_role == R.OWNER:
        return
    others = TeamMember.objects.filter(workspace_id=target.workspace_id, role=R.OWNER).exclude(pk=target.pk)
    if not others.exists():
        raise LastOwnerError()


@transaction.atomic
def change_role(workspace, user, member_id, new_role):
    actor = _lock_and_load_actor(workspace, user)
    target = get_object_or_404(TeamMember, pk=member_id, workspace=workspace)  # an id from another workspace is a 404
    _check_may_touch(actor, target, new_role)
    _check_not_last_owner(target, new_role)
    if target.role != new_role:  # same role again is a no-op, not an error
        target.role = new_role
        target.save(update_fields=['role'])
    return target


@transaction.atomic
def remove_member(workspace, user, member_id):
    actor = _lock_and_load_actor(workspace, user)
    target = get_object_or_404(TeamMember, pk=member_id, workspace=workspace)
    _check_may_touch(actor, target)
    _check_not_last_owner(target)
    target.delete()


@transaction.atomic
def leave(workspace, user):
    actor = _lock_and_load_actor(workspace, user)  # any member may leave; the last Owner may not
    _check_not_last_owner(actor)
    actor.delete()


@transaction.atomic
def accept_invite(token, user):
    """Joins `user` to the invite's workspace with the invite's role and returns the workspace.
    Single use: the link is used up by the first person it adds. Someone already in the workspace keeps their role
    and leaves the link unused (opening your own link by mistake does not waste it).
    The invite row is locked, so two people opening one link at the same moment cannot both get in: the second
    waits, then finds the link used and gets the same 404 as for any bad link."""
    invite = Invite.find_active(token, lock=True)
    if invite is None:
        raise NotFound('This invite link is invalid, used or expired.')
    _, joined = TeamMember.objects.get_or_create(workspace=invite.workspace, member=user, defaults={'role': invite.role})
    if joined:
        invite.revoke()
    return invite.workspace
