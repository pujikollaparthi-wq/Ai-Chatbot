from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model, login as django_login
from django.shortcuts import render, redirect, get_object_or_404
from .models import Department, UserActivityLog
from .serializers import (
    DepartmentSerializer, CustomUserSerializer, 
    UserRegistrationSerializer, UserActivityLogSerializer
)

User = get_user_model()

class IsAdminOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow administrators to edit objects."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == User.Roles.ADMIN

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name', 'code']

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['username', 'first_name', 'last_name', 'email']

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsAdminOrReadOnly()]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='me')
    def current_user(self, request):
        """Returns details of the currently authenticated user."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if 'text/html' in request.headers.get('Accept', ''):
            departments = Department.objects.all()
            roles = User.Roles.choices
            return render(request, 'accounts/register.html', {
                'departments': departments,
                'roles': roles
            })
        return Response({"detail": "GET method not allowed for API registration."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, request):
        is_html = 'text/html' in request.headers.get('Accept', '') or request.content_type == 'application/x-www-form-urlencoded'
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if data.get('department') == '':
            data['department'] = None

        # Verify passwords match first for browser submissions
        if is_html:
            password = data.get('password')
            password_confirm = data.get('password_confirm')
            if password != password_confirm:
                departments = Department.objects.all()
                roles = User.Roles.choices
                return render(request, 'accounts/register.html', {
                    'departments': departments,
                    'roles': roles,
                    'errors': {'password': ['Passwords do not match.']},
                    'data': data
                })

        serializer = UserRegistrationSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Log registration action
            UserActivityLog.objects.create(
                user=user,
                action='REGISTER',
                details=f"User registered with role: {user.role}",
                ip_address=self.get_client_ip(request)
            )
            
            if is_html:
                # Redirect to login page after successful registration
                from django.contrib import messages
                messages.success(request, f'Account created successfully! Please login with your credentials.')
                return redirect('login')
                
            return Response(CustomUserSerializer(user).data, status=status.HTTP_201_CREATED)
            
        if is_html:
            departments = Department.objects.all()
            roles = User.Roles.choices
            return render(request, 'accounts/register.html', {
                'departments': departments,
                'roles': roles,
                'errors': serializer.errors,
                'data': data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0]
        return request.META.get('REMOTE_ADDR')

class UserActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Admins see everything; standard users see only their own actions."""
        user = self.request.user
        if user.role == User.Roles.ADMIN:
            return UserActivityLog.objects.all()
        return UserActivityLog.objects.filter(user=user)

from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_user(request):
    from django.contrib import messages
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('login')
