from rest_framework import viewsets, status, permissions, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from .models import (
    ConfigurationItem, CIRelationship, KBArticle,
    Incident, Problem, ChangeRequest, ServiceRequest,
    ApprovalWorkflow, WorkflowStep, ApprovalInstance
)
from .serializers import (
    ConfigurationItemSerializer, CIRelationshipSerializer, KBArticleSerializer,
    IncidentSerializer, ProblemSerializer, ChangeRequestSerializer,
    ServiceRequestSerializer, ApprovalInstanceSerializer
)
from notifications.services import create_notification

User = get_user_model()

class ConfigurationItemViewSet(viewsets.ModelViewSet):
    queryset = ConfigurationItem.objects.all()
    serializer_class = ConfigurationItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'serial_number', 'ip_address']
    ordering_fields = ['created_at', 'name']

class CIRelationshipViewSet(viewsets.ModelViewSet):
    queryset = CIRelationship.objects.all()
    serializer_class = CIRelationshipSerializer
    permission_classes = [permissions.IsAuthenticated]

class KBArticleViewSet(viewsets.ModelViewSet):
    queryset = KBArticle.objects.filter(is_published=True)
    serializer_class = KBArticleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content', 'category']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views += 1
        instance.save(update_fields=['views'])
        return super().retrieve(request, *args, **kwargs)

class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['ticket_number', 'title', 'description', 'category']
    ordering_fields = ['created_at', 'priority', 'sla_due']

    def get_queryset(self):
        """Standard employees see only incidents they caller/reported, Support/Managers see all."""
        user = self.request.user
        if user.role in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
            return Incident.objects.all()
        return Incident.objects.filter(caller=user)

    def perform_create(self, serializer):
        # Auto assign caller to request user
        incident = serializer.save(caller=self.request.user)
        
        # Trigger Automatic assignment engine based on load
        if not incident.assigned_to:
            self.auto_assign_incident(incident)

    def auto_assign_incident(self, incident):
        """Finds active IT Support agent with the lowest active ticket count and assigns this incident."""
        support_agents = User.objects.filter(role=User.Roles.IT_SUPPORT, is_active=True)
        if support_agents.exists():
            # Annotate support agents with count of their open/in-progress incidents
            agent_load = support_agents.annotate(
                active_tickets=Count(
                    'assigned_incidents',
                    filter=Q(assigned_incidents__status__in=[Incident.Statuses.NEW, Incident.Statuses.IN_PROGRESS])
                )
            ).order_by('active_tickets')

            best_agent = agent_load.first()
            if best_agent:
                incident.assigned_to = best_agent
                incident.status = Incident.Statuses.IN_PROGRESS
                incident.save()
                
                # Notify assignee
                create_notification(
                    recipient=best_agent,
                    title="New Ticket Assigned",
                    message=f"Incident {incident.ticket_number} has been automatically assigned to you.",
                    notification_type='ALERT',
                    link=f"/incidents/{incident.id}/"
                )

    @action(detail=True, methods=['post'], url_path='assign-to-me')
    def assign_to_me(self, request, pk=None):
        incident = self.get_object()
        if request.user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN]:
            return Response({'error': 'Only IT support agents can take ownership of tickets.'}, status=status.HTTP_403_FORBIDDEN)
        
        incident.assigned_to = request.user
        incident.status = Incident.Statuses.IN_PROGRESS
        incident.save()
        return Response({'status': 'Incident assigned successfully', 'assigned_to': request.user.username})

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve_incident(self, request, pk=None):
        incident = self.get_object()
        resolution_notes = request.data.get('resolution_notes')
        root_cause = request.data.get('root_cause')

        if not resolution_notes:
            return Response({'error': 'Resolution notes are required to resolve an incident.'}, status=status.HTTP_400_BAD_REQUEST)

        incident.status = Incident.Statuses.RESOLVED
        incident.resolution_notes = resolution_notes
        if root_cause:
            incident.root_cause = root_cause
        incident.resolved_at = timezone.now()
        incident.save()

        # Notify Caller
        create_notification(
            recipient=incident.caller,
            title="Ticket Resolved",
            message=f"Your incident {incident.ticket_number} has been marked as Resolved. Check notes.",
            notification_type='INFO',
            link=f"/incidents/{incident.id}/"
        )
        return Response({'status': 'Incident marked as Resolved'})

class ProblemViewSet(viewsets.ModelViewSet):
    queryset = Problem.objects.all()
    serializer_class = ProblemSerializer
    permission_classes = [permissions.IsAuthenticated]

class ChangeRequestViewSet(viewsets.ModelViewSet):
    queryset = ChangeRequest.objects.all()
    serializer_class = ChangeRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Roles.ADMIN, User.Roles.MANAGER, User.Roles.IT_SUPPORT]:
            return ServiceRequest.objects.all()
        return ServiceRequest.objects.filter(requester=user)

    def perform_create(self, serializer):
        service_request = serializer.save(requester=self.request.user)
        
        # Trigger Multi-level Workflow
        workflow = ApprovalWorkflow.objects.filter(request_type=service_request.request_type).first()
        if workflow:
            steps = workflow.steps.all()
            for step in steps:
                approver = None
                # Dynamically set manager as approver for level 1
                if step.role_required == 'MANAGER' and service_request.requester.department:
                    approver = service_request.requester.department.manager
                elif step.role_required == 'ADMIN':
                    # Fallback to Admin user
                    approver = User.objects.filter(role=User.Roles.ADMIN).first()
                elif step.role_required == 'IT_SUPPORT':
                    # Support Lead
                    approver = User.objects.filter(role=User.Roles.IT_SUPPORT).first()

                ApprovalInstance.objects.create(
                    service_request=service_request,
                    step=step,
                    approver=approver,
                    status=ApprovalInstance.Statuses.PENDING
                )
            
            service_request.status = ServiceRequest.Statuses.PENDING
            service_request.save()

            # Notify the first step approver
            first_approval = service_request.approvals.filter(step__step_number=1).first()
            if first_approval and first_approval.approver:
                create_notification(
                    recipient=first_approval.approver,
                    title="Approval Action Required",
                    message=f"Approval request pending for ticket: {service_request.ticket_number}.",
                    notification_type='APPROVAL',
                    link=f"/requests/{service_request.id}/"
                )
        else:
            # Auto approval
            service_request.status = ServiceRequest.Statuses.APPROVED
            service_request.save()

class ApprovalInstanceViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Users see only approvals assigned to them."""
        return ApprovalInstance.objects.filter(approver=self.request.user, status=ApprovalInstance.Statuses.PENDING)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        approval = self.get_object()
        comments = request.data.get('comments', '')

        approval.status = ApprovalInstance.Statuses.APPROVED
        approval.comments = comments
        approval.save()

        service_request = approval.service_request
        next_step_num = approval.step.step_number + 1

        # Check if there is a next step in the workflow chain
        next_approval = service_request.approvals.filter(step__step_number=next_step_num).first()
        if next_approval:
            # Alert the next approver
            if next_approval.approver:
                create_notification(
                    recipient=next_approval.approver,
                    title="Approval Action Required",
                    message=f"Workflow request {service_request.ticket_number} advanced to level {next_step_num}.",
                    notification_type='APPROVAL',
                    link=f"/requests/{service_request.id}/"
                )
        else:
            # All levels approved
            service_request.status = ServiceRequest.Statuses.APPROVED
            service_request.save()
            
            # Notify requester
            create_notification(
                recipient=service_request.requester,
                title="Service Request Approved",
                message=f"Your request {service_request.ticket_number} has been fully approved.",
                notification_type='INFO',
                link=f"/requests/{service_request.id}/"
            )

            # Trigger asset allocation if it is an asset request
            if service_request.request_type == ServiceRequest.RequestTypes.ASSET:
                self.fulfill_asset_request(service_request)

        return Response({'status': 'Approved successfully'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        approval = self.get_object()
        comments = request.data.get('comments')

        if not comments:
            return Response({'error': 'Rejection comments are required.'}, status=status.HTTP_400_BAD_REQUEST)

        approval.status = ApprovalInstance.Statuses.REJECTED
        approval.comments = comments
        approval.save()

        service_request = approval.service_request
        service_request.status = ServiceRequest.Statuses.REJECTED
        service_request.save()

        # Notify requester
        create_notification(
            recipient=service_request.requester,
            title="Service Request Rejected",
            message=f"Your request {service_request.ticket_number} was rejected. Reason: {comments}",
            notification_type='INFO',
            link=f"/requests/{service_request.id}/"
        )
        return Response({'status': 'Rejected successfully'})

    def fulfill_asset_request(self, service_request):
        """Finds an in-stock asset matching the requested type and allocates it to the requester."""
        from assets.models import Asset, AssetAllocation, AssetHistory
        
        req_details = service_request.details
        asset_type = req_details.get('asset_type', 'LAPTOP')
        
        available_asset = Asset.objects.filter(asset_type=asset_type, status=Asset.Statuses.IN_STOCK).first()
        if available_asset:
            available_asset.status = Asset.Statuses.IN_USE
            available_asset.save()

            # Allocate
            AssetAllocation.objects.create(
                asset=available_asset,
                assigned_to=service_request.requester,
                allocated_by=User.objects.filter(role=User.Roles.ADMIN).first(),
                status='ACTIVE'
            )
            # Log history
            AssetHistory.objects.create(
                asset=available_asset,
                action='Allocated',
                performed_by=User.objects.filter(role=User.Roles.ADMIN).first(),
                details=f"Auto-allocated based on service request approval: {service_request.ticket_number}"
            )
            service_request.status = ServiceRequest.Statuses.FULFILLED
            service_request.save()
