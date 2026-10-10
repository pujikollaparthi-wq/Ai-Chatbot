from django.db import models
from django.conf import settings
import uuid

class AIChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Chat Session {self.id} for {self.user.username}"

class AIChatMessage(models.Model):
    class Senders(models.TextChoices):
        USER = 'USER', 'User'
        AI = 'AI', 'AI Assistant'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=Senders.choices)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender}: {self.message[:50]}"

class AIInsights(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    insight_type = models.CharField(max_length=100) # e.g. "Incident Trends", "SLA Predictor"
    summary = models.TextField()
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.insight_type} at {self.created_at}"
