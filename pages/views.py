from django.db.models import Exists, OuterRef
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.permissions import ANY_ROLE, CAN_WRITE, RolePermission

from .models import Drawing, Page
from .serializers import (MAX_STROKES, DrawingCreateSerializer, DrawingSerializer, PageListSerializer, PageSerializer,
                          StrokeSerializer)


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


class DrawingViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """A drawing block's strokes. Strokes are append-only: POST one on pen-up, DELETE one to undo."""
    permission_classes = [IsAuthenticated, RolePermission]
    roles_by_action = {
        'create': CAN_WRITE,
        'retrieve': ANY_ROLE,
        'add_stroke': CAN_WRITE,
        'remove_stroke': CAN_WRITE,
    }

    def get_serializer_class(self):
        return DrawingCreateSerializer if self.action == 'create' else DrawingSerializer

    def get_queryset(self):
        return (Drawing.objects.filter(page__workspace__memberships__member=self.request.user)
                .select_related('page__workspace').prefetch_related('strokes'))

    def perform_create(self, serializer):
        self.check_object_permissions(self.request, serializer.validated_data['page'])  # Page has .workspace too
        serializer.save()

    @action(detail=True, methods=['post'], url_path='strokes')
    def add_stroke(self, request, pk=None):
        drawing = self.get_object()
        data = StrokeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        # ponytail: soft cap, two racing posts can overshoot by one; fine for a size limit
        if drawing.strokes.count() >= MAX_STROKES:
            raise ValidationError({'detail': 'This drawing has too many strokes.'})
        _, created = drawing.strokes.get_or_create(  # same uid again = a retried save, not a second stroke
            uid=data.validated_data['uid'],
            defaults={'points': data.validated_data['points'], 'created_by': request.user})
        return Response(status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path=r'strokes/(?P<uid>[0-9a-f-]{36})')
    def remove_stroke(self, request, pk=None, uid=None):
        deleted, _ = self.get_object().strokes.filter(uid=uid).delete()
        return Response(status=status.HTTP_204_NO_CONTENT if deleted else status.HTTP_404_NOT_FOUND)
