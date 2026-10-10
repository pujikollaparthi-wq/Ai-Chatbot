from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from service_desk.models import (
    Incident, ServiceRequest, ApprovalInstance, KBArticle, ConfigurationItem,
    Problem, ChangeRequest
)
from assets.models import Asset, AssetAllocation
from ai_agent.models import AIInsights, AIChatSession

User = get_user_model()

def dashboard_redirect(request):
    """Redirects user to their appropriate role-based dashboard portal or renders landing page."""
    if not request.user.is_authenticated:
        return render(request, 'dashboard/home.html')
    role = request.user.role
    if role == User.Roles.ADMIN:
        return redirect('executive-dashboard')
    elif role == User.Roles.MANAGER:
        return redirect('manager-portal')
    elif role == User.Roles.IT_SUPPORT:
        return redirect('support-portal')
    else:
        return redirect('employee-portal')

def how_it_works(request):
    """Renders the AIOPS Platform overview infographic."""
    return render(request, 'dashboard/how_it_works.html')

@login_required
def employee_portal(request):
    """Renders the simple portal for standard employees."""
    user = request.user
    my_incidents = Incident.objects.filter(caller=user).order_by('-created_at')[:5]
    my_requests = ServiceRequest.objects.filter(requester=user).order_by('-created_at')[:5]
    
    # Active allocated assets
    my_assets = AssetAllocation.objects.filter(assigned_to=user, status='ACTIVE')
    
    # Popular KB articles
    kb_articles = KBArticle.objects.filter(is_published=True).order_by('-views')[:5]
    
    # Create or retrieve chat session for floating assistant
    chat_session = AIChatSession.objects.filter(user=user).first()
    if not chat_session:
        chat_session = AIChatSession.objects.create(user=user)

    context = {
        'my_incidents': my_incidents,
        'my_requests': my_requests,
        'my_assets': my_assets,
        'kb_articles': kb_articles,
        'chat_session_id': chat_session.id
    }
    return render(request, 'dashboard/employee_portal.html', context)

@login_required
def manager_portal(request):
    """Renders dashboard for department managers (includes approval queues)."""
    user = request.user
    if user.role not in [User.Roles.MANAGER, User.Roles.ADMIN]:
        return redirect('dashboard-redirect')

    # Approvals assigned to this manager that are pending
    pending_approvals = ApprovalInstance.objects.filter(approver=user, status=ApprovalInstance.Statuses.PENDING)
    
    # Incidents reported by department members
    dept_members = User.objects.filter(department=user.department)
    dept_incidents = Incident.objects.filter(caller__in=dept_members).order_by('-created_at')[:10]

    context = {
        'pending_approvals': pending_approvals,
        'dept_incidents': dept_incidents,
        'department': user.department
    }
    return render(request, 'dashboard/manager_portal.html', context)

@login_required
def support_portal(request):
    """Renders work queue dashboard for IT Support agents."""
    user = request.user
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN]:
        return redirect('dashboard-redirect')

    # Unassigned incidents
    unassigned_incidents = Incident.objects.filter(assigned_to__isnull=True).order_by('-created_at')
    
    # My assigned active incidents
    my_incidents = Incident.objects.filter(assigned_to=user).exclude(status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED]).order_by('-priority', 'sla_due')
    
    # Resolved queue
    resolved_incidents = Incident.objects.filter(assigned_to=user, status=Incident.Statuses.RESOLVED).order_by('-resolved_at')

    context = {
        'unassigned_incidents': unassigned_incidents,
        'my_incidents': my_incidents,
        'resolved_incidents': resolved_incidents
    }
    return render(request, 'dashboard/support_portal.html', context)

@login_required
def executive_dashboard(request):
    """Renders the high-level management executive analytics portal."""
    if request.user.role != User.Roles.ADMIN:
        return redirect('dashboard-redirect')

    # SLA and Incident Counts
    total_incidents = Incident.objects.count()
    open_incidents = Incident.objects.exclude(status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED]).count()
    closed_incidents = Incident.objects.filter(status=Incident.Statuses.CLOSED).count()
    resolved_incidents = Incident.objects.filter(status=Incident.Statuses.RESOLVED).count()

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = Incident.objects.filter(
        status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED],
        resolved_at__gte=today_start
    ).count()

    sla_breaches = Incident.objects.filter(sla_status='BREACHED').count()
    sla_compliance = 100.0
    if total_incidents > 0:
        sla_compliance = ((total_incidents - sla_breaches) / total_incidents) * 100

    # Calculate average resolution time (in hours) - ensuring positive duration values
    resolved_tickets = Incident.objects.filter(status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED], resolved_at__isnull=False)
    durations = [max(0.1, (t.resolved_at - t.created_at).total_seconds() / 3600) for t in resolved_tickets]
    avg_resolution_hours = round(sum(durations) / len(durations), 1) if durations else 0.0

    # Department SLA compliance rankings
    departments = User.objects.values('department__name', 'department__code').annotate(
        total_tickets=Count('incidents_reported'),
        breached_tickets=Count('incidents_reported', filter=Q(incidents_reported__sla_status='BREACHED'))
    ).exclude(department__name__isnull=True)

    dept_rankings = []
    for d in departments:
        tot = d['total_tickets']
        breached = d['breached_tickets']
        compliance = round(((tot - breached) / tot) * 100, 1) if tot > 0 else 100.0
        dept_rankings.append({
            'name': d['department__name'],
            'code': d['department__code'],
            'total': tot,
            'compliance': compliance
        })
    # Sort department rankings by compliance (highest first)
    dept_rankings = sorted(dept_rankings, key=lambda x: x['compliance'], reverse=True)

    # AI Insights
    ai_insights = AIInsights.objects.all().order_by('-created_at')[:3]

    # Recent Incidents
    recent_incidents = Incident.objects.all().order_by('-created_at')[:5]

    context = {
        'total_incidents': total_incidents,
        'open_incidents': open_incidents,
        'closed_incidents': closed_incidents + resolved_incidents,
        'resolved_today': resolved_today,
        'sla_breaches': sla_breaches,
        'sla_compliance': round(sla_compliance, 1),
        'avg_resolution_hours': avg_resolution_hours,
        'dept_rankings': dept_rankings,
        'ai_insights': ai_insights,
        'recent_incidents': recent_incidents,
    }
    return render(request, 'dashboard/executive_dashboard.html', context)


@login_required
def chart_data_api(request):
    """API endpoint providing aggregated chart data for Chart.js integrations."""
    if request.user.role not in [User.Roles.ADMIN, User.Roles.MANAGER, User.Roles.IT_SUPPORT]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    # 1. Incidents by status
    status_data = Incident.objects.values('status').annotate(count=Count('id'))
    status_dict = {item['status']: item['count'] for item in status_data}

    # 2. Incidents by priority
    priority_data = Incident.objects.values('priority').annotate(count=Count('id'))
    priority_dict = {item['priority']: item['count'] for item in priority_data}

    # 3. Incidents by category
    category_data = Incident.objects.values('category').annotate(count=Count('id'))
    category_dict = {item['category']: item['count'] for item in category_data}

    # 4. Weekly volume trend (last 7 days)
    today = timezone.now().date()
    labels = []
    counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime('%b %d'))
        day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        day_end = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.max.time()))
        counts.append(Incident.objects.filter(created_at__range=(day_start, day_end)).count())

    return JsonResponse({
        'status': status_dict,
        'priority': priority_dict,
        'category': category_dict,
        'trend': {
            'labels': labels,
            'values': counts
        }
    })

@login_required
def incidents_list(request):
    user = request.user
    if user.role in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
        incidents = Incident.objects.all().order_by('-created_at')
    else:
        incidents = Incident.objects.filter(caller=user).order_by('-created_at')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority', 'MEDIUM')
        category = request.POST.get('category', 'Software')
        
        # Leverage AI to predict category and priority
        from ai_agent.services import AIService
        ai_preds = AIService.predict_ticket_details(title, description)
        
        incident = Incident.objects.create(
            title=title,
            description=description,
            caller=user,
            priority=ai_preds.get('priority', priority),
            category=ai_preds.get('category', category),
            sla_due=timezone.now() + timedelta(hours=8)
        )
        
        # Trigger auto assign
        from service_desk.views import IncidentViewSet
        viewset = IncidentViewSet()
        viewset.auto_assign_incident(incident)
        
        return redirect('incidents-list')

    return render(request, 'dashboard/incidents_list.html', {'incidents': incidents})

@login_required
def incident_detail(request, pk):
    """Renders the detailed view of a single incident."""
    incident = get_object_or_404(Incident, pk=pk)
    
    # Check permissions: only caller, assigned agent, or privileged roles can view
    user = request.user
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
        if incident.caller != user:
            return redirect('incidents-list')
    
    # Compute SLA percentage for gauge visualization
    sla_pct = 75  # default
    if incident.sla_due and incident.status not in ['RESOLVED', 'CLOSED']:
        total_sla = (incident.sla_due - incident.created_at).total_seconds()
        elapsed = (timezone.now() - incident.created_at).total_seconds()
        if total_sla > 0:
            remaining_pct = max(0, min(100, ((total_sla - elapsed) / total_sla) * 100))
            sla_pct = int(remaining_pct * 3.6)  # convert to degrees out of 360
            sla_pct = max(0, min(100, int(remaining_pct)))
    elif incident.status in ['RESOLVED', 'CLOSED']:
        sla_pct = 100 if incident.sla_status != 'BREACHED' else 0
    
    context = {
        'incident': incident,
        'sla_pct': sla_pct,
    }
    return render(request, 'dashboard/incident_detail.html', context)


@login_required
def requests_list(request):
    user = request.user
    if user.role in [User.Roles.ADMIN, User.Roles.MANAGER, User.Roles.IT_SUPPORT]:
        requests_qs = ServiceRequest.objects.all().order_by('-created_at')
    else:
        requests_qs = ServiceRequest.objects.filter(requester=user).order_by('-created_at')

    if request.method == 'POST':
        title = request.POST.get('title')
        request_type = request.POST.get('request_type')
        
        details = {}
        if request_type == 'LEAVE':
            details = {
                'start_date': request.POST.get('start_date'),
                'end_date': request.POST.get('end_date'),
                'reason': request.POST.get('reason')
            }
        elif request_type == 'ASSET':
            details = {
                'asset_type': request.POST.get('asset_type'),
                'reason': request.POST.get('reason')
            }
        elif request_type == 'SOFTWARE':
            details = {
                'software_name': request.POST.get('software_name'),
                'reason': request.POST.get('reason')
            }

        service_request = ServiceRequest.objects.create(
            title=title,
            request_type=request_type,
            requester=user,
            details=details
        )
        
        # Trigger approvals workflow
        from service_desk.models import ApprovalWorkflow, WorkflowStep
        workflow = ApprovalWorkflow.objects.filter(request_type=service_request.request_type).first()
        if workflow:
            steps = workflow.steps.all()
            for step in steps:
                approver = None
                if step.role_required == 'MANAGER' and service_request.requester.department:
                    approver = service_request.requester.department.manager
                elif step.role_required == 'ADMIN':
                    approver = User.objects.filter(role=User.Roles.ADMIN).first()
                elif step.role_required == 'IT_SUPPORT':
                    approver = User.objects.filter(role=User.Roles.IT_SUPPORT).first()

                ApprovalInstance.objects.create(
                    service_request=service_request,
                    step=step,
                    approver=approver,
                    status=ApprovalInstance.Statuses.PENDING
                )
            
            service_request.status = ServiceRequest.Statuses.PENDING
            service_request.save()

            first_approval = service_request.approvals.filter(step__step_number=1).first()
            if first_approval and first_approval.approver:
                from notifications.services import create_notification
                create_notification(
                    recipient=first_approval.approver,
                    title="Approval Action Required",
                    message=f"Approval request pending for ticket: {service_request.ticket_number}.",
                    notification_type='APPROVAL',
                    link=f"/requests/"
                )
        else:
            service_request.status = ServiceRequest.Statuses.APPROVED
            service_request.save()

        return redirect('requests-list')

    return render(request, 'dashboard/requests_list.html', {'requests': requests_qs})

@login_required
def problems_list(request):
    problems = Problem.objects.all().order_by('-created_at')
    return render(request, 'dashboard/problems_list.html', {'problems': problems})

@login_required
def changes_list(request):
    changes = ChangeRequest.objects.all().order_by('-created_at')
    return render(request, 'dashboard/changes_list.html', {'changes': changes})

@login_required
def kb_list(request):
    articles = KBArticle.objects.filter(is_published=True).order_by('-created_at')
    return render(request, 'dashboard/kb_list.html', {'articles': articles})

@login_required
def assets_list(request):
    user = request.user
    if user.role in [User.Roles.ADMIN, User.Roles.IT_SUPPORT, User.Roles.MANAGER]:
        assets = Asset.objects.all().order_by('asset_tag')
    else:
        allocs = AssetAllocation.objects.filter(assigned_to=user, status='ACTIVE')
        assets = [a.asset for a in allocs]

    return render(request, 'dashboard/assets_list.html', {'assets': assets})

@login_required
def asset_detail(request, pk):
    """Renders the detailed view of a single asset."""
    from assets.models import AssetHistory
    
    asset = get_object_or_404(Asset, pk=pk)
    
    # Check permissions
    user = request.user
    if user.role not in [User.Roles.ADMIN, User.Roles.IT_SUPPORT, User.Roles.MANAGER]:
        # Standard employees can only view assets allocated to them
        if not AssetAllocation.objects.filter(asset=asset, assigned_to=user).exists():
            return redirect('assets-list')
    
    # Get allocation history
    allocations = AssetAllocation.objects.filter(asset=asset).order_by('-allocated_at')
    
    # Get current active allocation
    current_allocation = AssetAllocation.objects.filter(asset=asset, status='ACTIVE').first()
    
    # Get audit log history
    history = AssetHistory.objects.filter(asset=asset).order_by('-timestamp')
    
    context = {
        'asset': asset,
        'allocations': allocations,
        'current_allocation': current_allocation,
        'history': history,
    }
    return render(request, 'dashboard/asset_detail.html', context)


@login_required
def settings_page(request):
    """Renders the user settings and preferences page and handles updates."""
    from django.contrib import messages
    from django.contrib.auth import update_session_auth_hash
    import os
    from django.conf import settings

    # Handle GET request parameter for removing avatar
    if request.method == 'GET' and request.GET.get('remove_avatar') == 'true':
        avatar_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'avatars', f"{request.user.username}.png")
        if os.path.exists(avatar_path):
            try:
                os.remove(avatar_path)
                messages.success(request, 'Profile picture removed successfully.')
            except Exception as e:
                messages.error(request, 'Failed to remove profile picture.')
        return redirect('settings')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            if request.user.role == User.Roles.ADMIN:
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                email = request.POST.get('email', '').strip()
                
                if not first_name or not last_name or not email:
                    messages.error(request, 'All fields are required.')
                else:
                    request.user.first_name = first_name
                    request.user.last_name = last_name
                    request.user.email = email
                    request.user.save()
                    messages.success(request, 'Profile updated successfully!')
            else:
                messages.error(request, 'Only administrators can update their profile directly.')
                
        elif form_type == 'avatar':
            avatar_file = request.FILES.get('avatar')
            if avatar_file:
                ext = os.path.splitext(avatar_file.name)[1].lower()
                if ext not in ['.png', '.jpg', '.jpeg', '.gif']:
                    messages.error(request, 'Invalid file type. Only PNG, JPG, JPEG, and GIF are supported.')
                else:
                    avatar_dir = os.path.join(settings.BASE_DIR, 'static', 'img', 'avatars')
                    os.makedirs(avatar_dir, exist_ok=True)
                    avatar_path = os.path.join(avatar_dir, f"{request.user.username}.png")
                    try:
                        with open(avatar_path, 'wb+') as destination:
                            for chunk in avatar_file.chunks():
                                destination.write(chunk)
                        messages.success(request, 'Profile picture updated successfully!')
                    except Exception as e:
                        messages.error(request, f'Failed to upload profile picture: {str(e)}')
            else:
                messages.error(request, 'No image file uploaded.')
                
        elif form_type == 'security':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            if not current_password or not new_password or not confirm_password:
                messages.error(request, 'All password fields are required.')
            elif not request.user.check_password(current_password):
                messages.error(request, 'Incorrect current password.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully!')
                
        elif form_type == 'notifications':
            email_incidents = request.POST.get('email_incidents') == 'on'
            email_approvals = request.POST.get('email_approvals') == 'on'
            in_app_sounds = request.POST.get('in_app_sounds') == 'on'
            
            request.session['notif_email_incidents'] = email_incidents
            request.session['notif_email_approvals'] = email_approvals
            request.session['notif_in_app_sounds'] = in_app_sounds
            
            messages.success(request, 'Notification preferences updated successfully!')

        elif form_type == 'profile_request':
            req_first_name = request.POST.get('req_first_name', '').strip()
            req_last_name = request.POST.get('req_last_name', '').strip()
            req_email = request.POST.get('req_email', '').strip()
            req_reason = request.POST.get('req_reason', '').strip()

            if not req_reason:
                messages.error(request, 'Please provide a reason for the profile update request.')
            else:
                changes = []
                if req_first_name:
                    changes.append(f"First Name: '{request.user.first_name}' → '{req_first_name}'")
                if req_last_name:
                    changes.append(f"Last Name: '{request.user.last_name}' → '{req_last_name}'")
                if req_email:
                    changes.append(f"Email: '{request.user.email}' → '{req_email}'")

                if not changes:
                    messages.error(request, 'Please fill at least one field to request a change.')
                else:
                    changes_text = ', '.join(changes)
                    msg = (
                        f"Profile update requested by {request.user.get_full_name() or request.user.username} "
                        f"({request.user.username}). Requested changes: {changes_text}. "
                        f"Reason: {req_reason}"
                    )
                    # Send notification to all admins
                    from notifications.services import create_notification
                    admins = User.objects.filter(role=User.Roles.ADMIN)
                    for admin in admins:
                        create_notification(
                            recipient=admin,
                            title="Profile Update Request",
                            message=msg,
                            notification_type='INFO',
                            link='/settings/'
                        )
                    messages.success(request, '✅ Your profile update request has been sent to the administrator!')

        return redirect('settings')
        
    context = {
        'notif_email_incidents': request.session.get('notif_email_incidents', True),
        'notif_email_approvals': request.session.get('notif_email_approvals', True),
        'notif_in_app_sounds': request.session.get('notif_in_app_sounds', False),
    }
    return render(request, 'dashboard/settings.html', context)


# ----------------------------------------------------
# ADVANCED LIFECYCLE & ITSM FEATURES
# ----------------------------------------------------
from service_desk.models import (
    IncidentComment, IncidentAttachment, IncidentFeedback, IncidentActivity, log_incident_activity
)

@login_required
def close_incident(request, pk):
    """Closes an incident, changing status from RESOLVED to CLOSED."""
    incident = get_object_or_404(Incident, pk=pk)
    user = request.user
    
    # Permission check: support agent, admin, or the caller can close
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN] and incident.caller != user:
        return JsonResponse({'error': 'Unauthorized to close this ticket.'}, status=403)
        
    incident.status = Incident.Statuses.CLOSED
    incident.save()
    
    # Log activity
    log_incident_activity(
        incident=incident,
        actor=user,
        activity_type='CLOSED',
        description=f"Incident marked as CLOSED by {user.get_full_name() or user.username}."
    )
    
    return JsonResponse({'status': 'Incident closed successfully.'})

@login_required
def reopen_incident(request, pk):
    """Reopens a resolved or closed incident."""
    incident = get_object_or_404(Incident, pk=pk)
    user = request.user
    
    # Permission check
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN] and incident.caller != user:
        return JsonResponse({'error': 'Unauthorized to reopen this ticket.'}, status=403)
        
    # Reopen to IN_PROGRESS (if assigned) or NEW
    old_status = incident.get_status_display()
    incident.status = Incident.Statuses.IN_PROGRESS if incident.assigned_to else Incident.Statuses.NEW
    incident.resolved_at = None
    incident.save()
    
    # Log activity
    log_incident_activity(
        incident=incident,
        actor=user,
        activity_type='REOPENED',
        description=f"Incident reopened from {old_status} state by {user.get_full_name() or user.username}."
    )
    
    return JsonResponse({'status': 'Incident reopened successfully.'})

@login_required
def add_incident_comment(request, pk):
    """Adds public or internal comment to an incident."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)
        
    incident = get_object_or_404(Incident, pk=pk)
    user = request.user
    
    # Check permissions
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER] and incident.caller != user:
        return JsonResponse({'error': 'Unauthorized.'}, status=403)
        
    comment_text = request.POST.get('comment_text', '').strip()
    is_internal = request.POST.get('is_internal') == 'true'
    
    if not comment_text:
        return JsonResponse({'error': 'Comment content cannot be empty.'}, status=400)
        
    if is_internal and user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
        return JsonResponse({'error': 'Only support staff and admins can post internal notes.'}, status=403)
        
    comment = IncidentComment.objects.create(
        incident=incident,
        author=user,
        comment_text=comment_text,
        is_internal=is_internal
    )
    
    # Log activity
    act_type = 'INTERNAL_NOTE' if is_internal else 'COMMENT_ADDED'
    desc = f"Internal note added by {user.username}." if is_internal else f"Public comment added by {user.username}."
    log_incident_activity(incident, user, act_type, desc)
    
    return JsonResponse({
        'status': 'Comment added successfully',
        'comment': {
            'author': user.get_full_name() or user.username,
            'comment_text': comment.comment_text,
            'is_internal': comment.is_internal,
            'created_at': comment.created_at.strftime('%b %d, %Y %I:%M %p')
        }
    })

@login_required
def upload_incident_attachment(request, pk):
    """Uploads a file attachment for an incident."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)
        
    incident = get_object_or_404(Incident, pk=pk)
    user = request.user
    
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER] and incident.caller != user:
        return JsonResponse({'error': 'Unauthorized.'}, status=403)
        
    uploaded_file = request.FILES.get('attachment_file')
    if not uploaded_file:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
        
    attachment = IncidentAttachment.objects.create(
        incident=incident,
        uploaded_by=user,
        file=uploaded_file,
        filename=uploaded_file.name,
        file_size=uploaded_file.size
    )
    
    # Log activity
    log_incident_activity(
        incident=incident,
        actor=user,
        activity_type='ATTACHMENT_UPLOADED',
        description=f"File uploaded: {attachment.filename} ({round(attachment.file_size / 1024, 1)} KB) by {user.username}."
    )
    
    return JsonResponse({
        'status': 'Attachment uploaded successfully',
        'attachment': {
            'filename': attachment.filename,
            'url': attachment.file.url,
            'file_size': round(attachment.file_size / 1024, 1),
            'uploaded_by': attachment.uploaded_by.username,
            'created_at': attachment.created_at.strftime('%b %d, %Y %I:%M %p')
        }
    })

@login_required
def submit_incident_feedback(request, pk):
    """Submits user rating feedback and comments for resolved/closed incidents."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)
        
    incident = get_object_or_404(Incident, pk=pk)
    user = request.user
    
    # Only caller can submit feedback
    if incident.caller != user:
        return JsonResponse({'error': 'Only the reporter can submit feedback.'}, status=403)
        
    if incident.status not in [Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED]:
        return JsonResponse({'error': 'Feedback can only be submitted on resolved or closed tickets.'}, status=400)
        
    # Check if feedback already exists
    if hasattr(incident, 'feedback'):
        return JsonResponse({'error': 'Feedback already submitted for this incident.'}, status=400)
        
    try:
        import json
        data = json.loads(request.body)
        rating = int(data.get('rating', 5))
        comments = data.get('comments', '').strip()
    except Exception:
        rating = int(request.POST.get('rating', 5))
        comments = request.POST.get('comments', '').strip()
        
    if rating < 1 or rating > 5:
        return JsonResponse({'error': 'Rating must be between 1 and 5.'}, status=400)
        
    feedback = IncidentFeedback.objects.create(
        incident=incident,
        rating=rating,
        comments=comments
    )
    
    # Auto-close incident on feedback if it was only resolved
    if incident.status == Incident.Statuses.RESOLVED:
        incident.status = Incident.Statuses.CLOSED
        incident.save()
        
    # Log activity
    log_incident_activity(
        incident=incident,
        actor=user,
        activity_type='RATING_SUBMITTED',
        description=f"Feedback rating of {rating}/5 submitted by caller with comment: '{comments or 'No comment'}'. Ticket closed."
    )
    
    return JsonResponse({'status': 'Feedback submitted successfully. Ticket Closed.'})

# ----------------------------------------------------
# AI CO-PILOT VIEW HELPERS
# ----------------------------------------------------
from ai_agent.services import AIService

@login_required
def get_ai_suggestions(request, pk):
    """Fetches AI resolution suggestion and RCA for an incident."""
    incident = get_object_or_404(Incident, pk=pk)
    user = request.user
    
    # Staff only
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
        return JsonResponse({'error': 'Staff only feature.'}, status=403)
        
    suggestions = AIService.suggest_resolution(incident.title, incident.description)
    return JsonResponse(suggestions)

@login_required
def get_similar_incidents(request, pk):
    """Queries for resolved or closed incidents in the same category or description."""
    incident = get_object_or_404(Incident, pk=pk)
    user = request.user
    
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER] and incident.caller != user:
        return JsonResponse({'error': 'Unauthorized.'}, status=403)
        
    # Look for resolved or closed in same category, exclude current
    similar = Incident.objects.filter(
        category=incident.category,
        status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED]
    ).exclude(id=incident.id).order_by('-created_at')[:3]
    
    data = []
    for inc in similar:
        data.append({
            'id': str(inc.id),
            'ticket_number': inc.ticket_number,
            'title': inc.title,
            'status': inc.get_status_display(),
            'priority': inc.priority,
            'resolution_notes': inc.resolution_notes or 'No notes provided.',
            'root_cause': inc.root_cause or 'Not logged.'
        })
        
    return JsonResponse({'similar': data})

# ----------------------------------------------------
# PREDICTIVE AIOPS METRICS OUTAGE CENTER
# ----------------------------------------------------
@login_required
def predictive_alerts_dashboard(request):
    """Renders the AIOps Outage Predictor console."""
    if request.user.role not in [User.Roles.ADMIN, User.Roles.IT_SUPPORT, User.Roles.MANAGER]:
        return redirect('dashboard-redirect')
        
    return render(request, 'dashboard/predictive_alerts.html')

@login_required
def api_evaluate_infrastructure(request):
    """API endpoint to evaluate server telemetry and return outage probability."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
        
    try:
        import json
        data = json.loads(request.body)
        cpu = int(data.get('cpu', 50))
        memory = int(data.get('memory', 50))
        disk = int(data.get('disk', 50))
        network = int(data.get('network', 100))
    except Exception:
        cpu = int(request.POST.get('cpu', 50))
        memory = int(request.POST.get('memory', 50))
        disk = int(request.POST.get('disk', 50))
        network = int(request.POST.get('network', 100))
        
    prediction = AIService.predict_infrastructure_outage(cpu, memory, disk, network)
    return JsonResponse(prediction)

@login_required
def proactive_create_ticket(request):
    """Automatically creates a proactive incident ticket from the AIOps predictor screen."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
        
    user = request.user
    if user.role not in [User.Roles.ADMIN, User.Roles.IT_SUPPORT, User.Roles.MANAGER]:
        return JsonResponse({'error': 'Unauthorized.'}, status=403)
        
    try:
        import json
        data = json.loads(request.body)
        cpu = data.get('cpu', 90)
        memory = data.get('memory', 90)
        prob = data.get('probability', 85)
        server = data.get('server_name', 'Prod-DB-Server-01')
    except Exception:
        cpu = request.POST.get('cpu', 90)
        memory = request.POST.get('memory', 90)
        prob = request.POST.get('probability', 85)
        server = request.POST.get('server_name', 'Prod-DB-Server-01')
        
    title = f"PROACTIVE ALERT: Imminent Server Outage Risk on {server}"
    description = (
        f"AIOps Predictive Outage Engine flagged an active infrastructure outage warning on {server}:\n"
        f"- Outage Probability: {prob}%\n"
        f"- CPU Usage: {cpu}%\n"
        f"- Memory Usage: {memory}%\n"
        f"Critical thread pool exhaustion and hardware thermal limit expected in under 2 hours. Logged proactively to prevent SLA breach."
    )
    
    incident = Incident.objects.create(
        title=title,
        description=description,
        caller=user,
        category='Database' if 'DB' in server else 'Network' if 'Switch' in server else 'Hardware',
        priority=Incident.Priorities.CRITICAL if prob >= 80 else Incident.Priorities.HIGH,
        sla_due=timezone.now() + timedelta(hours=4)
    )
    
    # Auto assign to support load balanced
    from service_desk.views import IncidentViewSet
    IncidentViewSet().auto_assign_incident(incident)
    
    # Log timeline event
    log_incident_activity(
        incident=incident,
        actor=user,
        activity_type='CREATED',
        description=f"Proactive Incident automatically triggered by AIOps Predictor. Outage risk flagged: {prob}%."
    )
    
    return JsonResponse({
        'status': 'Proactive ticket created.',
        'redirect_url': f"/incidents/{incident.id}/"
    })

# ----------------------------------------------------
# REPORTING & EXPORTS (CSV, EXCEL, PDF)
# ----------------------------------------------------
import csv
from django.http import HttpResponse

@login_required
def export_incidents_csv(request):
    """Exports active incidents queue into standard CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="incidents_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Ticket Number', 'Title', 'Category', 'Priority', 'Status', 
        'Caller', 'Assigned To', 'SLA Due', 'SLA Status', 'Resolved At', 'Created At'
    ])
    
    # Get user role constraints
    user = request.user
    if user.role in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
        incidents = Incident.objects.all().order_by('-created_at')
    else:
        incidents = Incident.objects.filter(caller=user).order_by('-created_at')
        
    for inc in incidents:
        writer.writerow([
            inc.ticket_number,
            inc.title,
            inc.category,
            inc.priority,
            inc.get_status_display(),
            inc.caller.username,
            inc.assigned_to.username if inc.assigned_to else 'Unassigned',
            inc.sla_due.strftime('%Y-%m-%d %H:%M:%S') if inc.sla_due else 'None',
            inc.sla_status,
            inc.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if inc.resolved_at else 'None',
            inc.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
        
    return response

@login_required
def export_incidents_excel(request):
    """Exports incidents list to Excel using openpyxl."""
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:
        # Fallback to CSV with XLS headers
        return export_incidents_csv(request)
        
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Incident Report"
    
    # Apply theme colors (Deep Indigo Theme)
    header_fill = PatternFill(start_color="1e1b4b", end_color="1e1b4b", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="ffffff")
    cell_font = Font(name="Segoe UI", size=10)
    
    headers = [
        'Ticket ID', 'Title', 'Category', 'Priority', 'Status', 
        'Caller', 'Assigned Agent', 'SLA Status', 'Created At', 'Resolved At'
    ]
    
    ws.append(headers)
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    user = request.user
    if user.role in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
        incidents = Incident.objects.all().order_by('-created_at')
    else:
        incidents = Incident.objects.filter(caller=user).order_by('-created_at')
        
    for inc in incidents:
        row = [
            inc.ticket_number,
            inc.title,
            inc.category,
            inc.priority,
            inc.get_status_display(),
            inc.caller.username,
            inc.assigned_to.username if inc.assigned_to else 'Unassigned',
            inc.sla_status,
            inc.created_at.strftime('%Y-%m-%d %H:%M'),
            inc.resolved_at.strftime('%Y-%m-%d %H:%M') if inc.resolved_at else 'Active'
        ]
        ws.append(row)
        
    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            cell.font = cell_font
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
        
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="incidents_report.xlsx"'
    wb.save(response)
    return response

@login_required
def export_incidents_pdf(request):
    """Generates a print-ready PDF containing the entire Incidents queue report using reportlab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
    except ImportError:
        return HttpResponse("reportlab package not available. Please install reportlab first.", status=500)
        
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="incidents_summary.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#1e1b4b'),
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20
    )
    cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#0f172a')
    )
    header_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=colors.white
    )
    
    # Title & Subheader
    story.append(Paragraph("AIOPS Platform - Incident Report Summary", title_style))
    story.append(Paragraph(f"Generated on {timezone.now().strftime('%b %d, %Y %I:%M %p')} | Scope: System Wide Queue", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Data Table
    headers = [Paragraph(h, header_style) for h in ['Ticket', 'Title', 'Category', 'Priority', 'Status', 'SLA State', 'Created At']]
    data = [headers]
    
    user = request.user
    if user.role in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
        incidents = Incident.objects.all().order_by('-created_at')
    else:
        incidents = Incident.objects.filter(caller=user).order_by('-created_at')
        
    for inc in incidents:
        data.append([
            Paragraph(inc.ticket_number, cell_style),
            Paragraph(inc.title[:35] + '...' if len(inc.title) > 35 else inc.title, cell_style),
            Paragraph(inc.category, cell_style),
            Paragraph(inc.priority, cell_style),
            Paragraph(inc.get_status_display(), cell_style),
            Paragraph(inc.sla_status, cell_style),
            Paragraph(inc.created_at.strftime('%Y-%m-%d %H:%M'), cell_style)
        ])
        
    # Column width rules (Total = 540)
    col_widths = [65, 155, 60, 50, 60, 65, 85]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e1b4b')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('TOPPADDING', (0,1), (-1,-1), 6),
    ]))
    
    story.append(table)
    doc.build(story)
    return response

@login_required
def export_single_incident_pdf(request, pk):
    """Generates a beautiful print-optimized single Incident detail audit document."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
    except ImportError:
        return HttpResponse("reportlab package not available.", status=500)
        
    incident = get_object_or_404(Incident, pk=pk)
    
    # Check permissions
    user = request.user
    if user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER] and incident.caller != user:
        return HttpResponse("Unauthorized.", status=403)
        
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="incident_{incident.ticket_number}_report.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Styles
    title_style = ParagraphStyle('MainTitle', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#0f172a'), spaceAfter=5)
    ticket_style = ParagraphStyle('TktNumber', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#4f46e5'), spaceAfter=15)
    heading_style = ParagraphStyle('SectionHeading', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1e1b4b'), spaceBefore=15, spaceAfter=8)
    label_style = ParagraphStyle('FieldLabel', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#64748b'))
    val_style = ParagraphStyle('FieldValue', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#0f172a'))
    body_style = ParagraphStyle('TktBody', fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor('#1e293b'))
    meta_style = ParagraphStyle('AuditMeta', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#94a3b8'), spaceBefore=25)
    
    story.append(Paragraph(f"{incident.title}", title_style))
    story.append(Paragraph(f"TICKET NUMBER: {incident.ticket_number} | CATEGORY: {incident.category}", ticket_style))
    story.append(Spacer(1, 10))
    
    # 1. Metadata Grid Table
    meta_data = [
        [Paragraph("Reporter:", label_style), Paragraph(incident.caller.get_full_name() or incident.caller.username, val_style),
         Paragraph("Assigned To:", label_style), Paragraph(incident.assigned_to.get_full_name() if incident.assigned_to else "Unassigned", val_style)],
        [Paragraph("Priority:", label_style), Paragraph(incident.priority, val_style),
         Paragraph("Status:", label_style), Paragraph(incident.get_status_display(), val_style)],
        [Paragraph("Urgency:", label_style), Paragraph(incident.get_urgency_display(), val_style),
         Paragraph("Impact:", label_style), Paragraph(incident.get_impact_display(), val_style)],
        [Paragraph("Created At:", label_style), Paragraph(incident.created_at.strftime('%b %d, %Y %I:%M %p'), val_style),
         Paragraph("SLA Status:", label_style), Paragraph(incident.sla_status, val_style)]
    ]
    
    meta_table = Table(meta_data, colWidths=[80, 180, 80, 180])
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))
    
    # 2. Description
    story.append(Paragraph("Description", heading_style))
    desc_box = Table([[Paragraph(incident.description, body_style)]], colWidths=[520])
    desc_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(desc_box)
    story.append(Spacer(1, 15))
    
    # 3. Resolution Details
    if incident.resolution_notes:
        story.append(Paragraph("Resolution & Root Cause Details", heading_style))
        rca = incident.root_cause or "Not specified."
        res_text = (
            f"<b>Root Cause Analysis (RCA):</b><br/>{rca}<br/><br/>"
            f"<b>Resolution Notes:</b><br/>{incident.resolution_notes}"
        )
        res_box = Table([[Paragraph(res_text, body_style)]], colWidths=[520])
        res_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ecfdf5')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#a7f3d0')),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(res_box)
        story.append(Spacer(1, 15))
        
    # 4. Comments & Internal Notes (Staff only checks internal comments)
    comments_qs = incident.comments.all()
    if comments_qs.exists():
        story.append(Paragraph("Comments & Activities Summary", heading_style))
        comm_rows = []
        for comm in comments_qs:
            if comm.is_internal and user.role not in [User.Roles.IT_SUPPORT, User.Roles.ADMIN, User.Roles.MANAGER]:
                continue # Hide internal note
            label = "<b>[INTERNAL NOTE]</b> " if comm.is_internal else ""
            comment_body = f"<b>{comm.author.username}</b> ({comm.created_at.strftime('%Y-%m-%d %H:%M')}):<br/>{label}{comm.comment_text}"
            comm_rows.append([Paragraph(comment_body, body_style)])
            
        if comm_rows:
            comm_table = Table(comm_rows, colWidths=[520])
            comm_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(comm_table)
            story.append(Spacer(1, 15))
            
    # 5. Timeline Activities
    acts = incident.activities.all()
    if acts.exists():
        story.append(Paragraph("Incident Timeline History", heading_style))
        act_rows = []
        for act in acts:
            time_str = act.created_at.strftime('%Y-%m-%d %H:%M')
            act_text = f"<b>[{act.activity_type}]</b> - {act.description} (<i>{time_str}</i>)"
            act_rows.append([Paragraph(act_text, val_style)])
            
        act_table = Table(act_rows, colWidths=[520])
        act_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(act_table)
        story.append(Spacer(1, 10))
        
    # Feedback
    if hasattr(incident, 'feedback'):
        story.append(Paragraph("User Feedback Satisfaction Survey", heading_style))
        feedback_text = (
            f"<b>Satisfaction Rating:</b> {'⭐' * incident.feedback.rating} ({incident.feedback.rating}/5)<br/>"
            f"<b>Comments:</b> {incident.feedback.comments or 'None provided.'}"
        )
        fb_box = Table([[Paragraph(feedback_text, body_style)]], colWidths=[520])
        fb_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fef3c7')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#fde68a')),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(fb_box)
        
    story.append(Paragraph(f"This is an automated audit report generated from the AIOPS ITSM Platform. Audit Key: {incident.id}", meta_style))
    
    doc.build(story)
    return response


@login_required
def dashboard_metrics_api(request):
    """API endpoint providing real-time aggregated metrics for live dashboard auto-refresh."""
    if request.user.role != User.Roles.ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    total_incidents = Incident.objects.count()
    open_incidents = Incident.objects.exclude(status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED]).count()
    
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = Incident.objects.filter(
        status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED],
        resolved_at__gte=today_start
    ).count()

    sla_breaches = Incident.objects.filter(sla_status='BREACHED').count()
    
    # Calculate average resolution time (in hours)
    resolved_tickets = Incident.objects.filter(status__in=[Incident.Statuses.RESOLVED, Incident.Statuses.CLOSED], resolved_at__isnull=False)
    durations = [max(0.1, (t.resolved_at - t.created_at).total_seconds() / 3600) for t in resolved_tickets]
    avg_resolution_hours = round(sum(durations) / len(durations), 1) if durations else 0.0

    sla_compliance = 100.0
    if total_incidents > 0:
        sla_compliance = round(((total_incidents - sla_breaches) / total_incidents) * 100, 1)

    # Department compliance
    departments = User.objects.values('department__name').annotate(
        total_tickets=Count('incidents_reported'),
        breached_tickets=Count('incidents_reported', filter=Q(incidents_reported__sla_status='BREACHED'))
    ).exclude(department__name__isnull=True)

    dept_rankings = []
    for d in departments:
        tot = d['total_tickets']
        breached = d['breached_tickets']
        compliance = round(((tot - breached) / tot) * 100, 1) if tot > 0 else 100.0
        dept_rankings.append({
            'name': d['department__name'],
            'compliance': compliance
        })
    dept_rankings = sorted(dept_rankings, key=lambda x: x['compliance'], reverse=True)

    # Recent incidents
    recent = []
    for inc in Incident.objects.all().order_by('-created_at')[:5]:
        recent.append({
            'ticket_number': inc.ticket_number,
            'title': inc.title,
            'category': inc.category,
            'priority': inc.priority,
            'priority_display': inc.get_priority_display(),
            'status': inc.status,
            'status_display': inc.get_status_display(),
            'assigned_to': inc.assigned_to.get_full_name() if inc.assigned_to else 'Unassigned'
        })

    # AI insights
    insights = []
    for ins in AIInsights.objects.all().order_by('-created_at')[:3]:
        insights.append({
            'insight_type': ins.insight_type,
            'summary': ins.summary
        })

    return JsonResponse({
        'total_incidents': total_incidents,
        'open_incidents': open_incidents,
        'resolved_today': resolved_today,
        'sla_breaches': sla_breaches,
        'sla_compliance': sla_compliance,
        'avg_resolution_hours': avg_resolution_hours,
        'dept_rankings': dept_rankings,
        'recent_incidents': recent,
        'ai_insights': insights
    })




