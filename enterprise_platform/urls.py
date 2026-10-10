from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # REST API endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/accounts/', include('accounts.urls')),
    path('api/service_desk/', include('service_desk.urls')),
    path('api/assets/', include('assets.urls')),
    path('api/ai/', include('ai_agent.urls')),
    
    # Template-based browser routes
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('notifications/', include('notifications.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

