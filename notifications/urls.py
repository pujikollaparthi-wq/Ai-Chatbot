from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, notification_list

router = DefaultRouter()
router.register('api', NotificationViewSet, basename='notification-api')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', notification_list, name='notification-list'),
]
