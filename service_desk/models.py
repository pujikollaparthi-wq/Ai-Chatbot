from django.db import models
from django.conf import settings
import uuid
import random

class ConfigurationItem(models.Model):
    class CITypes(models.TextChoices):
        HARDWARE = 'HARDWARE', 'Hardware'
        SOFTWARE = 'SOFTWARE', 'Software'
        CLOUD_SERVICE = 'CLOUD_SERVICE', 'Cloud Service'
        NETWORK = 'NETWORK', 'Network'
        DATABASE = 'DATABASE', 'Database'

    class CIStatus(models.TextChoices):
        OPERATIONAL = 'OPERATIONAL', 'Operational'
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'
        RETIRED = 'RETIRED', 'Retired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    ci_type = models.CharField(max_length=20, choices=CITypes.choices, default=CITypes.HARDWARE)
    status = models.CharField(max_length=20, choices=CIStatus.choices, default=CIStatus.OPERATIONAL)
    serial_number = models.CharField(max_length=50, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_cis')
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.ci_type})"

class CIRelationship(models.Model):
    class RelationshipTypes(models.TextChoices):
        DEPENDS_ON = 'DEPENDS_ON', 'Depends on'
        RUNS_ON = 'RUNS_ON', 'Runs on'
        CONNECTED_TO = 'CONNECTED_TO', 'Connected to'

    source = models.ForeignKey(ConfigurationItem, on_delete=models.CASCADE, related_name='relations_out')
    target = models.ForeignKey(ConfigurationItem, on_delete=models.CASCADE, related_name='relations_in')
    relationship_type = models.CharField(max_length=20, choices=RelationshipTypes.choices, default=RelationshipTypes.DEPENDS_ON)

    def __str__(self):
        return f"{self.source.name} --[{self.relationship_type}]--> {self.target.name}"

class KBArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=50, default='General IT')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='kb_articles')
    views = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Incident(models.Model):
    class Statuses(models.TextChoices):
        NEW = 'NEW', 'New'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    class Priorities(models.TextChoices):
        CRITICAL = 'CRITICAL', 'Critical'
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'

    class Urgencies(models.TextChoices):
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'

    class Impacts(models.TextChoices):
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=15, unique=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='incidents_reported')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_incidents')
    status = models.CharField(max_length=20, choices=Statuses.choices, default=Statuses.NEW)
    priority = models.CharField(max_length=20, choices=Priorities.choices, default=Priorities.MEDIUM)
    urgency = models.CharField(max_length=20, choices=Urgencies.choices, default=Urgencies.MEDIUM)
    impact = models.CharField(max_length=20, choices=Impacts.choices, default=Impacts.MEDIUM)
    category = models.CharField(max_length=50, default='Software')
    affected_ci = models.ForeignKey(ConfigurationItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    sla_due = models.DateTimeField(null=True, blank=True)
    sla_status = models.CharField(max_length=20, default='WITHIN_SLA') # WITHIN_SLA, BREACHED
    resolved_at = models.DateTimeField(null=True, blank=True)
    root_cause = models.TextField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            while True:
                num = f"INC{random.randint(1000000, 9999999)}"
                if not Incident.objects.filter(ticket_number=num).exists():
                    self.ticket_number = num
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.title}"

class Problem(models.Model):
    class Statuses(models.TextChoices):
        NEW = 'NEW', 'New'
        INVESTIGATION = 'INVESTIGATION', 'Under Investigation'
        KNOWN_ERROR = 'KNOWN_ERROR', 'Known Error'
        RESOLVED = 'RESOLVED', 'Resolved'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=15, unique=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Statuses.choices, default=Statuses.NEW)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_problems')
    known_error = models.BooleanField(default=False)
    workaround = models.TextField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            while True:
                num = f"PRB{random.randint(1000000, 9999999)}"
                if not Problem.objects.filter(ticket_number=num).exists():
                    self.ticket_number = num
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.title}"

class ChangeRequest(models.Model):
    class Types(models.TextChoices):
        STANDARD = 'STANDARD', 'Standard'
        NORMAL = 'NORMAL', 'Normal'
        EMERGENCY = 'EMERGENCY', 'Emergency'

    class Statuses(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        APPROVAL = 'APPROVAL', 'Awaiting Approval'
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        IMPLEMENTING = 'IMPLEMENTING', 'Implementing'
        REVIEW = 'REVIEW', 'Review'
        CLOSED = 'CLOSED', 'Closed'

    class Risks(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=15, unique=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    change_type = models.CharField(max_length=20, choices=Types.choices, default=Types.NORMAL)
    status = models.CharField(max_length=20, choices=Statuses.choices, default=Statuses.DRAFT)
    risk = models.CharField(max_length=20, choices=Risks.choices, default=Risks.LOW)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='changes_requested')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_changes')
    implementation_plan = models.TextField()
    backout_plan = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            while True:
                num = f"CHG{random.randint(1000000, 9999999)}"
                if not ChangeRequest.objects.filter(ticket_number=num).exists():
                    self.ticket_number = num
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.title}"

class ServiceRequest(models.Model):
    class RequestTypes(models.TextChoices):
        LEAVE = 'LEAVE', 'Leave Request'
        ASSET = 'ASSET', 'Asset Allocation'
        SOFTWARE = 'SOFTWARE', 'Software Access'

    class Statuses(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        FULFILLED = 'FULFILLED', 'Fulfilled'
        CLOSED = 'CLOSED', 'Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=15, unique=True, blank=True)
    title = models.CharField(max_length=200)
    request_type = models.CharField(max_length=20, choices=RequestTypes.choices)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_requests')
    status = models.CharField(max_length=20, choices=Statuses.choices, default=Statuses.DRAFT)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            while True:
                num = f"REQ{random.randint(1000000, 9999999)}"
                if not ServiceRequest.objects.filter(ticket_number=num).exists():
                    self.ticket_number = num
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.title}"

class ApprovalWorkflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    request_type = models.CharField(max_length=20, choices=ServiceRequest.RequestTypes.choices, unique=True)
    steps_count = models.IntegerField(default=1)

    def __str__(self):
        return self.name

class WorkflowStep(models.Model):
    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.CASCADE, related_name='steps')
    step_number = models.IntegerField()
    role_required = models.CharField(max_length=20) # MANAGER, ADMIN, IT_SUPPORT

    class Meta:
        ordering = ['step_number']

    def __str__(self):
        return f"{self.workflow.name} - Step {self.step_number} ({self.role_required})"

class ApprovalInstance(models.Model):
    class Statuses(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='approvals')
    step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approvals_assigned')
    status = models.CharField(max_length=20, choices=Statuses.choices, default=Statuses.PENDING)
    comments = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service_request.ticket_number} - Step {self.step.step_number} ({self.status})"


class IncidentComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment_text = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.incident.ticket_number}"


class IncidentAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='incident_attachments/')
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment {self.filename} for {self.incident.ticket_number}"


class IncidentFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.OneToOneField(Incident, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comments = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.incident.ticket_number} - Rating: {self.rating}"


class IncidentActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.CharField(max_length=50)  # e.g., CREATED, CLAIMED, RESOLVED, CLOSED, REOPENED, COMMENT_ADDED, ATTACHMENT_UPLOADED, RATING_SUBMITTED
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Incident Activities'

    def __str__(self):
        return f"{self.activity_type} on {self.incident.ticket_number}"


def log_incident_activity(incident, actor, activity_type, description):
    IncidentActivity.objects.create(
        incident=incident,
        actor=actor,
        activity_type=activity_type,
        description=description
    )

