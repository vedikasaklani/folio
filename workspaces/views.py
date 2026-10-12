from django.db import transaction
from django.db.models import F
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import TeamMember, Workspace
from .permissions import ANY_ROLE, CAN_MANAGE, OWNER_ONLY, RolePermission
from .serializers import WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    roles_by_action = {
        'retrieve': ANY_ROLE,
        'update': CAN_MANAGE,
        'partial_update': CAN_MANAGE,
        'destroy': OWNER_ONLY,
    }

    def get_queryset(self):
        # Only workspaces the caller belongs to: outsiders get 404, not 403.
        # One join gives us the role too (unique constraint => one row per user+workspace).
        return (Workspace.objects.filter(memberships__member=self.request.user)
                .annotate(role=F('memberships__role')).order_by('id'))

    def perform_create(self, serializer):
        with transaction.atomic():  # workspace + owner row, or neither
            workspace = serializer.save()
            TeamMember.objects.create(member=self.request.user, workspace=workspace,
                                      role=TeamMember.Roles.OWNER)
        workspace.role = TeamMember.Roles.OWNER
