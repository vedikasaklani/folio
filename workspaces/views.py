from django.db import transaction
from django.db.models import F, Prefetch
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import members
from .models import TeamMember, Workspace
from .permissions import ANY_ROLE, CAN_MANAGE, OWNER_ONLY, RolePermission
from .serializers import MemberRoleSerializer, MemberSerializer, WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    roles_by_action = {
        'retrieve': ANY_ROLE,
        'update': CAN_MANAGE,
        'partial_update': CAN_MANAGE,
        'destroy': OWNER_ONLY,
        'member': CAN_MANAGE,  # change a role
        'remove_member': CAN_MANAGE,
        'leave': ANY_ROLE,
    }

    def get_queryset(self):
        # Only workspaces the caller belongs to: outsiders get 404, not 403.
        # One join gives us the role too (unique constraint => one row per user+workspace).
        return (Workspace.objects.filter(memberships__member=self.request.user)
                .annotate(role=F('memberships__role')).order_by('id')
                .prefetch_related(Prefetch('memberships', TeamMember.objects.select_related('member').order_by('id'))))

    def perform_create(self, serializer):
        with transaction.atomic():  # workspace + owner row, or neither
            workspace = serializer.save()
            TeamMember.objects.create(member=self.request.user, workspace=workspace,
                                      role=TeamMember.Roles.OWNER)
        workspace.role = TeamMember.Roles.OWNER

    # Member management. The permission layer only checks "may this role manage members at all"; the finer rules
    # (an Admin never touches an Owner, the last Owner stays) are in members.py, under a lock.
    @action(detail=True, methods=['patch'], url_path=r'members/(?P<member_id>\d+)')
    def member(self, request, pk=None, member_id=None):
        serializer = MemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = members.change_role(self.get_object(), request.user, member_id, serializer.validated_data['role'])
        return Response(MemberSerializer(target, context=self.get_serializer_context()).data)

    @member.mapping.delete
    def remove_member(self, request, pk=None, member_id=None):
        members.remove_member(self.get_object(), request.user, member_id)
        return Response(status=204)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        members.leave(self.get_object(), request.user)
        return Response(status=204)
