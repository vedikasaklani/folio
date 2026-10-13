from rest_framework import serializers

from .models import TeamMember, Workspace


class MemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='member.username')
    is_you = serializers.SerializerMethodField()

    class Meta:
        model = TeamMember
        fields = ('username', 'role', 'is_you')

    def get_is_you(self, obj):
        return obj.member_id == self.context['request'].user.id


class WorkspaceSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)  # the caller's role, annotated in the view
    members = MemberSerializer(source='memberships', many=True, read_only=True)

    class Meta:
        model = Workspace
        fields = ('id', 'name', 'description', 'role', 'members')
