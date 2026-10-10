from django.db import models
from django.conf import settings
import uuid
import random

class Asset(models.Model):
    class AssetTypes(models.TextChoices):
        LAPTOP = 'LAPTOP', 'Laptop'
        MOBILE = 'MOBILE', 'Mobile Phone'
        MONITOR = 'MONITOR', 'Monitor'
        SOFTWARE = 'SOFTWARE', 'Software License'

    class Statuses(models.TextChoices):
        IN_STOCK = 'IN_STOCK', 'In Stock'
        IN_USE = 'IN_USE', 'In Use'
        RETIRED = 'RETIRED', 'Retired'
        DAMAGED = 'DAMAGED', 'Damaged'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_tag = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=20, choices=AssetTypes.choices, default=AssetTypes.LAPTOP)
    status = models.CharField(max_length=20, choices=Statuses.choices, default=Statuses.IN_STOCK)
    serial_number = models.CharField(max_length=100, unique=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.asset_tag:
            while True:
                tag = f"AST{random.randint(1000000, 9999999)}"
                if not Asset.objects.filter(asset_tag=tag).exists():
                    self.asset_tag = tag
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset_tag} - {self.name} ({self.status})"

class AssetAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='allocations')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_assets')
    allocated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='allocations_made')
    allocated_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('ACTIVE', 'Active'), ('RETURNED', 'Returned')], default='ACTIVE')

    def __str__(self):
        return f"{self.asset.name} assigned to {self.assigned_to.username}"

class AssetHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=50) # e.g. "Allocated", "Returned", "Damaged Report"
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    details = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.asset.asset_tag} - {self.action} on {self.timestamp}"
