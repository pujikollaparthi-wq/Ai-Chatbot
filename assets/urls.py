from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, AssetAllocationViewSet, AssetHistoryViewSet

router = DefaultRouter()
router.register('catalog', AssetViewSet, basename='asset')
router.register('allocations', AssetAllocationViewSet, basename='asset-allocation')
router.register('history', AssetHistoryViewSet, basename='asset-history')

urlpatterns = [
    path('', include(router.urls)),
]
