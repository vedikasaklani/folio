from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from pages.views import DrawingViewSet, PageViewSet
from workspaces.views import AcceptInviteView, WorkspaceViewSet

router = DefaultRouter()
router.register('workspaces', WorkspaceViewSet, basename='workspace')
router.register('pages', PageViewSet, basename='page')
router.register('drawings', DrawingViewSet, basename='drawing')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('browser-login/', include('rest_framework.urls')),  # session login for the browsable API only
    path('api/invites/accept/', AcceptInviteView.as_view()),
    path('api/', include(router.urls)),
]
