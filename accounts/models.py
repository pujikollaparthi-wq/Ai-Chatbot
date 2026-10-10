from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    manager = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments'
    )

    def __str__(self):
        return f"{self.name} ({self.code})"

class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        MANAGER = 'MANAGER', 'Manager'
        EMPLOYEE = 'EMPLOYEE', 'Employee'
        IT_SUPPORT = 'IT_SUPPORT', 'IT Support'

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.EMPLOYEE
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

class UserActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=100)
    details = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
