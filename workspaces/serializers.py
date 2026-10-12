from rest_framework import serializers

from .models import Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)  # the caller's role, annotated in the view

    class Meta:
        model = Workspace
        fields = ('id', 'name', 'description', 'role')
