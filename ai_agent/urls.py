from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIChatViewSet, AIInsightsViewSet, AITicketIntelligenceView, AIPredictiveIncidentDetectionView

router = DefaultRouter()
router.register('chat', AIChatViewSet, basename='ai-chat')
router.register('insights', AIInsightsViewSet, basename='ai-insight')

urlpatterns = [
    path('', include(router.urls)),
    path('intelligence/predict/', AITicketIntelligenceView.as_view(), name='ai-predict'),
    path('intelligence/sla-risks/', AIPredictiveIncidentDetectionView.as_view(), name='ai-sla-risks'),
]
