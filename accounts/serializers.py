from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Department, UserActivityLog

User = get_user_model()

class DepartmentSerializer(serializers.ModelSerializer):
    manager_name = serializers.ReadOnlyField(source='manager.username')
    manager_full_name = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'manager', 'manager_name', 'manager_full_name']

    def get_manager_full_name(self, obj):
        if obj.manager:
            return obj.manager.get_full_name()
        return None

class CustomUserSerializer(serializers.ModelSerializer):
    department_details = DepartmentSerializer(source='department', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 
            'role', 'role_display', 'department', 'department_details', 
            'employee_id', 'phone_number', 'is_active'
        ]
        read_only_fields = ['id', 'is_active']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name', 'email', 'role', 'department', 'employee_id', 'phone_number']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = UserActivityLog
        fields = ['id', 'user', 'username', 'action', 'details', 'ip_address', 'timestamp']
