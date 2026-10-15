from rest_framework import serializers

from .models import TeamMember, Workspace


class MemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='member.username')
    is_you = serializers.SerializerMethodField()

    class Meta:
        model = TeamMember
        fields = ('id', 'username', 'role', 'is_you')  # id = the membership, what member management addresses

    def get_is_you(self, obj):
        return obj.member_id == self.context['request'].user.id


class MemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=TeamMember.Roles.choices)


class WorkspaceSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)  # the caller's role, annotated in the view
    members = MemberSerializer(source='memberships', many=True, read_only=True)

    class Meta:
        model = Workspace
        fields = ('id', 'name', 'description', 'role', 'members')
