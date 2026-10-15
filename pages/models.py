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

 



class Drawing(models.Model):
    """One drawing block. A page's content holds {type: 'drawing', attrs: {id}}; the strokes live here."""
    page=models.ForeignKey(Page, on_delete=models.CASCADE, related_name='drawings')
    created_at=models.DateTimeField(auto_now_add=True)

    @property
    def workspace(self):  # lets RolePermission check drawings like pages
        return self.page.workspace

    def __str__(self):
        return f'Drawing {self.pk} on {self.page_id}'


class Stroke(models.Model):
    """One pen-down to pen-up. `points` = [[x, y, pressure], ...], raw ints; smoothing happens at render time."""
    drawing=models.ForeignKey(Drawing, on_delete=models.CASCADE, related_name='strokes')
    uid=models.UUIDField()  # made by the client, so a retried save can't draw the stroke twice
    points=models.JSONField()
    created_by=models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='strokes')
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=('id',)
        constraints=[models.UniqueConstraint(fields=('drawing', 'uid'), name='stroke_uid_once_per_drawing')]

    def __str__(self):
        return f'Stroke {self.uid}'
