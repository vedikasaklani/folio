from rest_framework import serializers

from workspaces.models import Workspace

from .content import plain_text, title_of, validate_doc
from .models import Page


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

    def validate(self, attrs):
        if attrs.get('content'):  # the document's first node is the title: it wins over any `name` sent
            attrs['name'] = title_of(attrs['content'])
            attrs['text'] = plain_text(attrs['content'])
        if self.instance and attrs.get('workspace', self.instance.workspace) != self.instance.workspace:
            raise serializers.ValidationError({'workspace': 'A page cannot move to another workspace.'})
        page = self.instance or Page()
        for key, value in attrs.items():
            setattr(page, key, value)
        page.clean()  # same-workspace + no-cycle rules; DRF turns Django's ValidationError into a 400
        return attrs
