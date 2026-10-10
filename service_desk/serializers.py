from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ConfigurationItem, CIRelationship, KBArticle,
    Incident, Problem, ChangeRequest, ServiceRequest,
    ApprovalWorkflow, WorkflowStep, ApprovalInstance
)
from accounts.serializers import CustomUserSerializer

User = get_user_model()

# CMDB Serializers
class ConfigurationItemSerializer(serializers.ModelSerializer):
    owner_details = CustomUserSerializer(source='owner', read_only=True)
    ci_type_display = serializers.CharField(source='get_ci_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ConfigurationItem
        fields = ['id', 'name', 'ci_type', 'ci_type_display', 'status', 'status_display', 'serial_number', 'ip_address', 'owner', 'owner_details', 'description', 'created_at', 'updated_at']

class CIRelationshipSerializer(serializers.ModelSerializer):
    source_name = serializers.ReadOnlyField(source='source.name')
    target_name = serializers.ReadOnlyField(source='target.name')
    relationship_type_display = serializers.CharField(source='get_relationship_type_display', read_only=True)

    class Meta:
        model = CIRelationship
        fields = ['id', 'source', 'source_name', 'target', 'target_name', 'relationship_type', 'relationship_type_display']

# KB Serializers
class KBArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')
    author_full_name = serializers.SerializerMethodField()

    class Meta:
        model = KBArticle
        fields = ['id', 'title', 'content', 'category', 'author', 'author_name', 'author_full_name', 'views', 'is_published', 'created_at', 'updated_at']

    def get_author_full_name(self, obj):
        if obj.author:
            return obj.author.get_full_name()
        return None

# Incident Serializers
class IncidentSerializer(serializers.ModelSerializer):
    caller_details = CustomUserSerializer(source='caller', read_only=True)
    assigned_to_details = CustomUserSerializer(source='assigned_to', read_only=True)
    affected_ci_details = ConfigurationItemSerializer(source='affected_ci', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    urgency_display = serializers.CharField(source='get_urgency_display', read_only=True)
    impact_display = serializers.CharField(source='get_impact_display', read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id', 'ticket_number', 'title', 'description', 'caller', 'caller_details', 
            'assigned_to', 'assigned_to_details', 'status', 'status_display', 
            'priority', 'priority_display', 'urgency', 'urgency_display', 
            'impact', 'impact_display', 'category', 'affected_ci', 'affected_ci_details', 
            'sla_due', 'sla_status', 'resolved_at', 'root_cause', 'resolution_notes', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'ticket_number', 'sla_status', 'resolved_at', 'created_at', 'updated_at']

# Problem Serializers
class ProblemSerializer(serializers.ModelSerializer):
    assigned_to_details = CustomUserSerializer(source='assigned_to', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Problem
        fields = ['id', 'ticket_number', 'title', 'description', 'status', 'status_display', 'assigned_to', 'assigned_to_details', 'known_error', 'workaround', 'resolution_notes', 'created_at']
        read_only_fields = ['id', 'ticket_number', 'created_at']

# Change Request Serializers
class ChangeRequestSerializer(serializers.ModelSerializer):
    requested_by_details = CustomUserSerializer(source='requested_by', read_only=True)
    assigned_to_details = CustomUserSerializer(source='assigned_to', read_only=True)
    change_type_display = serializers.CharField(source='get_change_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    risk_display = serializers.CharField(source='get_risk_display', read_only=True)

    class Meta:
        model = ChangeRequest
        fields = [
            'id', 'ticket_number', 'title', 'description', 'change_type', 'change_type_display', 
            'status', 'status_display', 'risk', 'risk_display', 'requested_by', 'requested_by_details', 
            'assigned_to', 'assigned_to_details', 'implementation_plan', 'backout_plan', 
            'start_date', 'end_date', 'created_at'
        ]
        read_only_fields = ['id', 'ticket_number', 'created_at']

# Workflow & Approvals
class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStep
        fields = ['id', 'step_number', 'role_required']

class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalWorkflow
        fields = ['id', 'name', 'request_type', 'steps_count', 'steps']

class ApprovalInstanceSerializer(serializers.ModelSerializer):
    approver_details = CustomUserSerializer(source='approver', read_only=True)
    step_number = serializers.ReadOnlyField(source='step.step_number')
    role_required = serializers.ReadOnlyField(source='step.role_required')
    ticket_number = serializers.ReadOnlyField(source='service_request.ticket_number')
    request_title = serializers.ReadOnlyField(source='service_request.title')

    class Meta:
        model = ApprovalInstance
        fields = ['id', 'service_request', 'ticket_number', 'request_title', 'step', 'step_number', 'role_required', 'approver', 'approver_details', 'status', 'comments', 'updated_at']
        read_only_fields = ['id', 'service_request', 'step', 'updated_at']

class ServiceRequestSerializer(serializers.ModelSerializer):
    requester_details = CustomUserSerializer(source='requester', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approvals = ApprovalInstanceSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceRequest
        fields = ['id', 'ticket_number', 'title', 'request_type', 'request_type_display', 'requester', 'requester_details', 'status', 'status_display', 'details', 'approvals', 'created_at']
        read_only_fields = ['id', 'ticket_number', 'created_at']
