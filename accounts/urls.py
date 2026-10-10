from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib.auth import views as auth_views
from .views import DepartmentViewSet, CustomUserViewSet, UserActivityLogViewSet, UserRegistrationView, logout_user

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='department')
router.register('users', CustomUserViewSet, basename='user')
router.register('logs', UserActivityLogViewSet, basename='activity-log')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', logout_user, name='logout'),
]
