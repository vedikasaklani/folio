from rest_framework import serializers

from workspaces.models import Workspace

from .content import drawing_ids, plain_text, title_of, validate_doc
from .models import Drawing, Page, Stroke

MAX_POINTS = 2000  # per stroke
MAX_STROKES = 1000  # per drawing
MAX_DRAWINGS = 50  # per page
COORD_MAX = 10_000  # x and y, in the drawing's own units (the client scales them to the screen)


class PageListSerializer(serializers.ModelSerializer):
    """Sidebar row: no text (it can be large). has_children is annotated in the view."""
    has_children = serializers.BooleanField(read_only=True)

    class Meta:
        model = Page
        fields = ('id', 'workspace', 'parent', 'name', 'has_children')
        read_only_fields = fields


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ('id', 'workspace', 'parent', 'name', 'content', 'text', 'author', 'created_at', 'updated_at')
        read_only_fields = ('author', 'text')  # text is derived from content

    def get_fields(self):
        fields = super().get_fields()
        user = self.context['request'].user
        # Ids outside the caller's workspaces are "does not exist" (400), same as a made-up id.
        fields['workspace'].queryset = Workspace.objects.filter(memberships__member=user)
        fields['parent'].queryset = Page.objects.filter(workspace__memberships__member=user)
        return fields

    def validate_content(self, value):
        if value:  # {} = "no body yet"
            try:
                validate_doc(value)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return value

    def check_drawings(self, content):
        # A block may only point at one of this page's own drawings, and only once (copy-paste of a block is unsupported).
        ids = drawing_ids(content)
        own = set(self.instance.drawings.filter(id__in=ids).values_list('id', flat=True)) if self.instance else set()
        if len(ids) != len(set(ids)) or not set(ids) <= own:
            raise serializers.ValidationError({'content': "A drawing block must point at one of the page's own drawings, once."})

    def validate(self, attrs):
        if attrs.get('content'):  # the document's first node is the title: it wins over any `name` sent
            attrs['name'] = title_of(attrs['content'])
            attrs['text'] = plain_text(attrs['content'])
        if attrs.get('content'):
            self.check_drawings(attrs['content'])
        if self.instance and attrs.get('workspace', self.instance.workspace) != self.instance.workspace:
            raise serializers.ValidationError({'workspace': 'A page cannot move to another workspace.'})
        page = self.instance or Page()
        for key, value in attrs.items():
            setattr(page, key, value)
        page.clean()  # same-workspace + no-cycle rules; DRF turns Django's ValidationError into a 400
        return attrs


class DrawingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drawing
        fields = ('id', 'page')

    def get_fields(self):
        fields = super().get_fields()
        fields['page'].queryset = Page.objects.filter(workspace__memberships__member=self.context['request'].user)
        return fields

    def validate_page(self, page):
        if page.drawings.count() >= MAX_DRAWINGS:
            raise serializers.ValidationError('This page has too many drawings.')
        return page


class StrokeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stroke
        fields = ('uid', 'points')

    def validate_points(self, points):
        coord = lambda v: isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= COORD_MAX
        pressure = lambda v: isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 100  # percent
        if not isinstance(points, list) or not 1 <= len(points) <= MAX_POINTS:
            raise serializers.ValidationError(f'A stroke has 1 to {MAX_POINTS} points.')
        for p in points:
            if not (isinstance(p, list) and len(p) == 3 and coord(p[0]) and coord(p[1]) and pressure(p[2])):
                raise serializers.ValidationError('Each point is [x, y, pressure] as whole numbers.')
        return points


class DrawingSerializer(serializers.ModelSerializer):
    strokes = StrokeSerializer(many=True, read_only=True)

    class Meta:
        model = Drawing
        fields = ('id', 'page', 'strokes')
        read_only_fields = fields
