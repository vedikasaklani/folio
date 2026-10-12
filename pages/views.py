from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from workspaces.permissions import ANY_ROLE, CAN_WRITE, RolePermission

from .models import Page
from .serializers import PageSerializer


class PageViewSet(viewsets.ModelViewSet):
    """Flat list (id + parent on each row); the client builds the tree. Filter: ?workspace=<id>."""
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    roles_by_action = {
        'create': CAN_WRITE,
        'retrieve': ANY_ROLE,
        'update': CAN_WRITE,
        'partial_update': CAN_WRITE,
        'destroy': CAN_WRITE,
    }

    def get_queryset(self):
        qs = Page.objects.filter(workspace__memberships__member=self.request.user).order_by('id')
        workspace = self.request.query_params.get('workspace')
        if self.action == 'list' and workspace is not None:
            if not workspace.isdigit():
                raise ValidationError({'workspace': 'Must be an integer id.'})
            qs = qs.filter(workspace_id=workspace)
        return qs

    def perform_create(self, serializer):
        # No object exists yet, so run the role check against the target workspace by hand.
        self.check_object_permissions(self.request, serializer.validated_data['workspace'])
        serializer.save(author=self.request.user)
