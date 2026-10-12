from rest_framework.permissions import BasePermission

from .models import TeamMember, Workspace

R = TeamMember.Roles
ANY_ROLE = (R.OWNER, R.ADMIN, R.EDITOR, R.VIEWER)
CAN_WRITE = (R.OWNER, R.ADMIN, R.EDITOR)
CAN_MANAGE = (R.OWNER, R.ADMIN)
OWNER_ONLY = (R.OWNER,)


class RolePermission(BasePermission):
    """Looks up the user's role in the object's workspace (TeamMember table) and
    checks it against view.roles_by_action. An action missing from the map is denied."""

    def has_object_permission(self, request, view, obj):
        workspace = obj if isinstance(obj, Workspace) else obj.workspace
        role = (TeamMember.objects.filter(workspace=workspace, member=request.user)
                .values_list('role', flat=True).first())
        return role in view.roles_by_action.get(view.action, ())
