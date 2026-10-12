from django.contrib import admin
from .models import TeamMember, Workspace

admin.site.register([Workspace, TeamMember])
