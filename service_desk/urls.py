from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConfigurationItemViewSet, CIRelationshipViewSet, KBArticleViewSet,
    IncidentViewSet, ProblemViewSet, ChangeRequestViewSet,
    ServiceRequestViewSet, ApprovalInstanceViewSet
)

router = DefaultRouter()
router.register('cmdb/items', ConfigurationItemViewSet, basename='cmdb-item')
router.register('cmdb/relations', CIRelationshipViewSet, basename='cmdb-relation')
router.register('kb', KBArticleViewSet, basename='kb-article')
router.register('incidents', IncidentViewSet, basename='incident')
router.register('problems', ProblemViewSet, basename='problem')
router.register('changes', ChangeRequestViewSet, basename='change')
router.register('requests', ServiceRequestViewSet, basename='request')
router.register('approvals', ApprovalInstanceViewSet, basename='approval')

urlpatterns = [
    path('', include(router.urls)),
]
