from django.db import models
from django.conf import settings
import uuid

class Notification(models.Model):
    class NotificationTypes(models.TextChoices):
        INFO = 'INFO', 'Information'
        ALERT = 'ALERT', 'Alert'
        SLA_ESCALATION = 'SLA_ESCALATION', 'SLA Escalation'
        APPROVAL = 'APPROVAL', 'Approval Request'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationTypes.choices, default=NotificationTypes.INFO)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} - {self.title} ({'Read' if self.is_read else 'Unread'})"
