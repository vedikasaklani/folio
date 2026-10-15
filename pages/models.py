from django.contrib.auth import get_user_model
from django.db import models

from workspaces.models import Workspace

User=get_user_model()
# Create your models here.
from django.core.exceptions import ValidationError


class Page(models.Model):
    author=models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='pages')
    workspace=models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='pages')
    name=models.CharField(max_length=200)
    content=models.JSONField(default=dict, blank=True)  # ProseMirror doc; validated in pages/content.py
    text=models.TextField(blank=True)  # plain-text copy derived from `content` (search, diffs, AI later)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    parent=models.ForeignKey('self',on_delete=models.CASCADE, related_name='children', blank=True, null=True)

    def clean(self):
        super().clean()
        if self.parent and self.parent.workspace_id != self.workspace_id:
            raise ValidationError({'parent': "The parent page must be in the same workspace."})
        node=self.parent
        while node:
            if self.pk and node.pk==self.pk:
                raise ValidationError({'parent': 'A page cannot be its own ancestor.'})
            node=node.parent

    def __str__(self):
        return self.name

 

