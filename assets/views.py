from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Asset, AssetAllocation, AssetHistory
from .serializers import AssetSerializer, AssetAllocationSerializer, AssetHistorySerializer

User = get_user_model()

class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """IT and managers see all assets; standard employees see assets currently allocated to them."""
        user = self.request.user
        if user.role in [User.Roles.ADMIN, User.Roles.IT_SUPPORT, User.Roles.MANAGER]:
            return Asset.objects.all()
        return Asset.objects.filter(allocations__assigned_to=user, allocations__status='ACTIVE')

    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        """Manually allocates an asset to a user."""
        asset = self.get_object()
        assigned_to_id = request.data.get('assigned_to')

        if request.user.role not in [User.Roles.ADMIN, User.Roles.IT_SUPPORT]:
            return Response({'error': 'Unauthorized. Only IT Support or Admins can allocate assets.'}, status=status.HTTP_403_FORBIDDEN)

        if asset.status != Asset.Statuses.IN_STOCK:
            return Response({'error': 'Asset is not available in stock.'}, status=status.HTTP_400_BAD_REQUEST)

        assigned_to = User.objects.filter(id=assigned_to_id).first()
        if not assigned_to:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Allocate asset
        asset.status = Asset.Statuses.IN_USE
        asset.save()

        AssetAllocation.objects.create(
            asset=asset,
            assigned_to=assigned_to,
            allocated_by=request.user,
            status='ACTIVE'
        )

        AssetHistory.objects.create(
            asset=asset,
            action='Allocated',
            performed_by=request.user,
            details=f"Manually allocated to user: {assigned_to.username}"
        )

        return Response({'status': 'Asset allocated successfully.'})

    @action(detail=True, methods=['post'], url_path='return')
    def return_asset(self, request, pk=None):
        """Processes the return of an allocated asset."""
        asset = self.get_object()

        if request.user.role not in [User.Roles.ADMIN, User.Roles.IT_SUPPORT]:
            return Response({'error': 'Unauthorized. Only IT Support or Admins can return assets.'}, status=status.HTTP_403_FORBIDDEN)

        allocation = AssetAllocation.objects.filter(asset=asset, status='ACTIVE').first()
        if not allocation:
            return Response({'error': 'No active allocation found for this asset.'}, status=status.HTTP_400_BAD_REQUEST)

        # Return asset
        asset.status = Asset.Statuses.IN_STOCK
        asset.save()

        allocation.status = 'RETURNED'
        allocation.returned_at = timezone.now()
        allocation.save()

        AssetHistory.objects.create(
            asset=asset,
            action='Returned',
            performed_by=request.user,
            details=f"Returned by employee: {allocation.assigned_to.username}"
        )

        return Response({'status': 'Asset returned successfully.'})

class AssetAllocationViewSet(viewsets.ModelViewSet):
    serializer_class = AssetAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Roles.ADMIN, User.Roles.IT_SUPPORT, User.Roles.MANAGER]:
            return AssetAllocation.objects.all()
        return AssetAllocation.objects.filter(assigned_to=user)

class AssetHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssetHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Roles.ADMIN, User.Roles.IT_SUPPORT]:
            return AssetHistory.objects.all()
        return AssetHistory.objects.filter(asset__allocations__assigned_to=user).distinct()
