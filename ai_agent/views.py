from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import AIChatSession, AIChatMessage, AIInsights
from .serializers import AIChatSessionSerializer, AIChatMessageSerializer, AIInsightsSerializer
from .services import AIService
from service_desk.models import Incident

User = get_user_model()

class AIChatViewSet(viewsets.ModelViewSet):
    serializer_class = AIChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Standard employees see only their own chat sessions; Admins see all."""
        user = self.request.user
        if user.role == User.Roles.ADMIN:
            return AIChatSession.objects.all()
        return AIChatSession.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, pk=None):
        """Sends a message to the AI Assistant and returns the AI response."""
        session = self.get_object()
        user_message_text = request.data.get('message')

        if not user_message_text:
            return Response({'error': 'Message field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Save user message
        AIChatMessage.objects.create(
            session=session,
            sender=AIChatMessage.Senders.USER,
            message=user_message_text
        )

        # Get session messages for context
        messages_qs = session.messages.all()
        history = [{'sender': m.sender, 'message': m.message} for m in messages_qs]

        # Query AI Service
        ai_response_text = AIService.get_chat_response(history)

        # Save AI response
        ai_message = AIChatMessage.objects.create(
            session=session,
            sender=AIChatMessage.Senders.AI,
            message=ai_response_text
        )

        return Response(AIChatMessageSerializer(ai_message).data, status=status.HTTP_201_CREATED)

class AIInsightsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AIInsights.objects.all()
    serializer_class = AIInsightsSerializer
    permission_classes = [permissions.IsAuthenticated]

class AITicketIntelligenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Predicts ticket category and priority before submission."""
        title = request.data.get('title')
        description = request.data.get('description')

        if not title or not description:
            return Response({'error': 'Title and Description are required for prediction.'}, status=status.HTTP_400_BAD_REQUEST)

        predictions = AIService.predict_ticket_details(title, description)
        recommendations = AIService.suggest_resolution(title, description)
        
        predictions.update(recommendations)
        return Response(predictions, status=status.HTTP_200_OK)

class AIPredictiveIncidentDetectionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Scans all active incidents and flags potential SLA breach risks."""
        incidents = Incident.objects.exclude(status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED])
        scanned_tickets = []

        for incident in incidents:
            is_risk, probability = AIService.predict_sla_breach(incident)
            if is_risk:
                scanned_tickets.append({
                    'id': incident.id,
                    'ticket_number': incident.ticket_number,
                    'title': incident.title,
                    'assigned_to': incident.assigned_to.username if incident.assigned_to else 'Unassigned',
                    'priority': incident.priority,
                    'sla_probability': round(probability, 2)
                })

        return Response({
            'scanned_count': incidents.count(),
            'high_risk_breaches': scanned_tickets
        }, status=status.HTTP_200_OK)
