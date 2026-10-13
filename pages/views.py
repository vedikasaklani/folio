from django.db.models import Exists, OuterRef
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated

from workspaces.permissions import ANY_ROLE, CAN_WRITE, RolePermission

from .models import Page
from .serializers import PageListSerializer, PageSerializer


class PagePagination(CursorPagination):
    page_size = 20
    ordering = 'id'  # creation order; stable while rows are added or deleted mid-scroll


class PageViewSet(viewsets.ModelViewSet):
    """List = one tree level, paginated, no text: ?workspace=<id>&parent=<id|null>. Detail has the text."""
    permission_classes = [IsAuthenticated, RolePermission]
    pagination_class = PagePagination
    roles_by_action = {
        'create': CAN_WRITE,
        'retrieve': ANY_ROLE,
        'update': CAN_WRITE,
        'partial_update': CAN_WRITE,
        'destroy': CAN_WRITE,
    }

    def get_serializer_class(self):
        return PageListSerializer if self.action == 'list' else PageSerializer

    def get_queryset(self):
        qs = Page.objects.filter(workspace__memberships__member=self.request.user).order_by('id')
        if self.action != 'list':
            return qs
        params = self.request.query_params
        for key in ('workspace', 'parent'):
            value = params.get(key)
            if value is None:
                continue
            if key == 'parent' and value == 'null':
                qs = qs.filter(parent__isnull=True)
            elif value.isdigit():
                qs = qs.filter(**{f'{key}_id': value})
            else:
                raise ValidationError({key: 'Must be an integer id' + (" or 'null'." if key == 'parent' else '.')})
        return qs.annotate(has_children=Exists(Page.objects.filter(parent=OuterRef('pk'))))

    def perform_create(self, serializer):
        # No object exists yet, so run the role check against the target workspace by hand.
        self.check_object_permissions(self.request, serializer.validated_data['workspace'])
        serializer.save(author=self.request.user)
