from django.contrib import admin
from .models import Drawing, Page, Stroke

admin.site.register([Page, Drawing, Stroke])
