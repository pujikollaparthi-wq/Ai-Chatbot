from rest_framework import serializers
from .models import Asset, AssetAllocation, AssetHistory
from accounts.serializers import CustomUserSerializer

class AssetSerializer(serializers.ModelSerializer):
    asset_type_display = serializers.CharField(source='get_asset_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Asset
        fields = ['id', 'asset_tag', 'name', 'asset_type', 'asset_type_display', 'status', 'status_display', 'serial_number', 'cost', 'created_at']
        read_only_fields = ['id', 'asset_tag', 'created_at']

class AssetAllocationSerializer(serializers.ModelSerializer):
    asset_details = AssetSerializer(source='asset', read_only=True)
    assigned_to_details = CustomUserSerializer(source='assigned_to', read_only=True)
    allocated_by_details = CustomUserSerializer(source='allocated_by', read_only=True)

    class Meta:
        model = AssetAllocation
        fields = ['id', 'asset', 'asset_details', 'assigned_to', 'assigned_to_details', 'allocated_by', 'allocated_by_details', 'allocated_at', 'returned_at', 'status']
        read_only_fields = ['id', 'allocated_at']

class AssetHistorySerializer(serializers.ModelSerializer):
    performed_by_name = serializers.ReadOnlyField(source='performed_by.username')
    asset_tag = serializers.ReadOnlyField(source='asset.asset_tag')

    class Meta:
        model = AssetHistory
        fields = ['id', 'asset', 'asset_tag', 'action', 'performed_by', 'performed_by_name', 'details', 'timestamp']
