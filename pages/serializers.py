from rest_framework import serializers

from workspaces.models import Workspace

from .models import Page


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ('id', 'workspace', 'parent', 'name', 'text', 'author', 'created_at', 'updated_at')
        read_only_fields = ('author',)

    def get_fields(self):
        fields = super().get_fields()
        user = self.context['request'].user
        # Ids outside the caller's workspaces are "does not exist" (400), same as a made-up id.
        fields['workspace'].queryset = Workspace.objects.filter(memberships__member=user)
        fields['parent'].queryset = Page.objects.filter(workspace__memberships__member=user)
        return fields

    def validate(self, attrs):
        if self.instance and attrs.get('workspace', self.instance.workspace) != self.instance.workspace:
            raise serializers.ValidationError({'workspace': 'A page cannot move to another workspace.'})
        page = self.instance or Page()
        for key, value in attrs.items():
            setattr(page, key, value)
        page.clean()  # same-workspace + no-cycle rules; DRF turns Django's ValidationError into a 400
        return attrs
