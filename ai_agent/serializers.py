from rest_framework import serializers
from .models import AIChatSession, AIChatMessage, AIInsights

class AIChatMessageSerializer(serializers.ModelSerializer):
    sender_display = serializers.CharField(source='get_sender_display', read_only=True)

    class Meta:
        model = AIChatMessage
        fields = ['id', 'session', 'sender', 'sender_display', 'message', 'timestamp']
        read_only_fields = ['id', 'timestamp']

class AIChatSessionSerializer(serializers.ModelSerializer):
    messages = AIChatMessageSerializer(many=True, read_only=True)
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = AIChatSession
        fields = ['id', 'user', 'username', 'created_at', 'messages']
        read_only_fields = ['id', 'user', 'created_at']

class AIInsightsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInsights
        fields = ['id', 'insight_type', 'summary', 'data', 'created_at']
        read_only_fields = ['id', 'created_at']
