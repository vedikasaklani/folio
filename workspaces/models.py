from django.db import models
from django.conf import settings
# Create your models here.
#user to workspace relationship

class Workspace(models.Model):
    name=models.CharField(max_length=200)
    description=models.TextField(blank=True)
    def __str__(self):
        return self.name


class TeamMember(models.Model):
    class Roles(models.TextChoices):
        OWNER='OW', 'Owner'
        ADMIN='AD', 'Admin'
        EDITOR='ED', 'Editor'
        VIEWER='VR', 'Viewer'
    member=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    workspace=models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    role=models.CharField(max_length=2, choices=Roles.choices, default=Roles.VIEWER)
    joined_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['member', 'workspace'], name='one_membership_per_user_per_workspace')]

    def __str__(self):
        return f'{self.member} - {self.workspace} ({self.get_role_display()})'
