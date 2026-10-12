from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from workspaces.views import WorkspaceViewSet

router = DefaultRouter()
router.register('workspaces', WorkspaceViewSet, basename='workspace')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
