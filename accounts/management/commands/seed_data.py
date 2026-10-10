from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

from accounts.models import Department
from service_desk.models import (
    ConfigurationItem, CIRelationship, KBArticle,
    Incident, Problem, ChangeRequest, ServiceRequest,
    ApprovalWorkflow, WorkflowStep
)
from assets.models import Asset, AssetAllocation, AssetHistory

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds mock enterprise operations data into the database'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database with enterprise operations data...')

        # 1. Create Departments
        depts = {
            'IT': {'name': 'IT Operations', 'code': 'IT-OPS'},
            'HR': {'name': 'Human Resources', 'code': 'HR-CORP'},
            'FAC': {'name': 'Facilities Management', 'code': 'FAC-FAC'},
            'FIN': {'name': 'Finance & Accounting', 'code': 'FIN-ACC'},
        }
        dept_objs = {}
        for key, info in depts.items():
            dept, created = Department.objects.get_or_create(
                code=info['code'],
                defaults={'name': info['name']}
            )
            dept_objs[key] = dept
            if created:
                self.stdout.write(f"Created department: {dept.name}")

        # 2. Create Users
        # Admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@enterprise.com',
                'role': User.Roles.ADMIN,
                'employee_id': 'EMP0000',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('Password123')
            admin_user.save()
            self.stdout.write("Created Admin user: admin / Password123")

        # IT Manager
        it_mgr, created = User.objects.get_or_create(
            username='manager_it',
            defaults={
                'email': 'it_mgr@enterprise.com',
                'role': User.Roles.MANAGER,
                'department': dept_objs['IT'],
                'employee_id': 'EMP0001'
            }
        )
        if created:
            it_mgr.set_password('Password123')
            it_mgr.save()
            dept_objs['IT'].manager = it_mgr
            dept_objs['IT'].save()
            self.stdout.write("Created IT Manager user: manager_it")

        # HR Manager
        hr_mgr, created = User.objects.get_or_create(
            username='manager_hr',
            defaults={
                'email': 'hr_mgr@enterprise.com',
                'role': User.Roles.MANAGER,
                'department': dept_objs['HR'],
                'employee_id': 'EMP0002'
            }
        )
        if created:
            hr_mgr.set_password('Password123')
            hr_mgr.save()
            dept_objs['HR'].manager = hr_mgr
            dept_objs['HR'].save()
            self.stdout.write("Created HR Manager user: manager_hr")

        # IT Support Agents
        support_agents = []
        for i in range(1, 4):
            agent, created = User.objects.get_or_create(
                username=f'support_{i}',
                defaults={
                    'email': f'support_{i}@enterprise.com',
                    'role': User.Roles.IT_SUPPORT,
                    'department': dept_objs['IT'],
                    'employee_id': f'EMP001{i}'
                }
            )
            if created:
                agent.set_password('Password123')
                agent.save()
                self.stdout.write(f"Created IT Support agent: support_{i}")
            support_agents.append(agent)

        # Employees
        employees = []
        emp_depts = [('HR', 1), ('IT', 2), ('FIN', 3), ('FAC', 4)]
        for dept_code, index in emp_depts:
            emp, created = User.objects.get_or_create(
                username=f'employee_{index}',
                defaults={
                    'email': f'employee_{index}@enterprise.com',
                    'role': User.Roles.EMPLOYEE,
                    'department': dept_objs[dept_code],
                    'employee_id': f'EMP010{index}'
                }
            )
            if created:
                emp.set_password('Password123')
                emp.save()
                self.stdout.write(f"Created employee: employee_{index}")
            employees.append(emp)

        # 3. Create Configuration Items (CMDB)
        ci_ad, created = ConfigurationItem.objects.get_or_create(
            name='Active Directory Domain Services',
            defaults={
                'ci_type': ConfigurationItem.CITypes.CLOUD_SERVICE,
                'status': ConfigurationItem.CIStatus.OPERATIONAL,
                'description': 'Active Directory cloud authentication domain controller.'
            }
        )
        ci_db, created = ConfigurationItem.objects.get_or_create(
            name='Production Database Server',
            defaults={
                'ci_type': ConfigurationItem.CITypes.DATABASE,
                'status': ConfigurationItem.CIStatus.OPERATIONAL,
                'ip_address': '10.0.4.15',
                'description': 'Main database server containing system data.',
                'owner': it_mgr
            }
        )
        ci_router, created = ConfigurationItem.objects.get_or_create(
            name='Core Router - Floor 3',
            defaults={
                'ci_type': ConfigurationItem.CITypes.NETWORK,
                'status': ConfigurationItem.CIStatus.OPERATIONAL,
                'ip_address': '192.168.3.1',
                'description': 'Floor 3 router servicing general office access.'
            }
        )
        self.stdout.write("Created basic CMDB items.")

        # CMDB Relationships
        CIRelationship.objects.get_or_create(
            source=ci_db,
            target=ci_ad,
            defaults={'relationship_type': CIRelationship.RelationshipTypes.DEPENDS_ON}
        )

        # 4. Create Knowledge Base Articles
        KBArticle.objects.get_or_create(
            title='How to Connect to Corporate VPN',
            defaults={
                'content': 'To connect to the corporate VPN:\n1. Download GlobalProtect client.\n2. Set gateway to vpn.enterprise.com.\n3. Login using your active directory employee credentials.\n4. Accept the MFA challenge.',
                'category': 'IT Support',
                'author': it_mgr,
                'views': 120
            }
        )
        KBArticle.objects.get_or_create(
            title='Leave Request Policy Guide',
            defaults={
                'content': 'Standard leave requests require 2 days notice for single-day leaves and 2 weeks notice for extended leaves. Leaves must be approved by your Department Manager first, then by HR Operations.',
                'category': 'HR Policies',
                'author': hr_mgr,
                'views': 84
            }
        )

        # 5. Create Workflows for Service Requests
        # Leave Request Workflow (Manager -> Admin)
        leave_wf, _ = ApprovalWorkflow.objects.get_or_create(
            request_type=ServiceRequest.RequestTypes.LEAVE,
            defaults={'name': 'Standard Leave Approval Workflow', 'steps_count': 2}
        )
        WorkflowStep.objects.get_or_create(workflow=leave_wf, step_number=1, defaults={'role_required': 'MANAGER'})
        WorkflowStep.objects.get_or_create(workflow=leave_wf, step_number=2, defaults={'role_required': 'ADMIN'})

        # Asset Workflow (Manager -> IT Support)
        asset_wf, _ = ApprovalWorkflow.objects.get_or_create(
            request_type=ServiceRequest.RequestTypes.ASSET,
            defaults={'name': 'Hardware Asset Approval Workflow', 'steps_count': 2}
        )
        WorkflowStep.objects.get_or_create(workflow=asset_wf, step_number=1, defaults={'role_required': 'MANAGER'})
        WorkflowStep.objects.get_or_create(workflow=asset_wf, step_number=2, defaults={'role_required': 'IT_SUPPORT'})

        # Software Workflow (Manager -> IT Support)
        soft_wf, _ = ApprovalWorkflow.objects.get_or_create(
            request_type=ServiceRequest.RequestTypes.SOFTWARE,
            defaults={'name': 'Software License Grant Workflow', 'steps_count': 2}
        )
        WorkflowStep.objects.get_or_create(workflow=soft_wf, step_number=1, defaults={'role_required': 'MANAGER'})
        WorkflowStep.objects.get_or_create(workflow=soft_wf, step_number=2, defaults={'role_required': 'IT_SUPPORT'})
        self.stdout.write("Created multi-level approval workflows.")

        # 6. Create Assets
        assets_list = [
            {'name': 'ThinkPad X1 Carbon Gen 11', 'type': Asset.AssetTypes.LAPTOP, 'sn': 'SN-TP11009', 'cost': 1499.00},
            {'name': 'MacBook Pro 16" M3 Pro', 'type': Asset.AssetTypes.LAPTOP, 'sn': 'SN-MBPM3P16', 'cost': 2499.00},
            {'name': 'iPhone 15 Pro 256GB', 'type': Asset.AssetTypes.MOBILE, 'sn': 'SN-IPH15P98', 'cost': 1099.00},
            {'name': 'Dell UltraSharp 27" 4K', 'type': Asset.AssetTypes.MONITOR, 'sn': 'SN-DEL274K', 'cost': 450.00},
        ]
        asset_objs = []
        for a_data in assets_list:
            asset, created = Asset.objects.get_or_create(
                serial_number=a_data['sn'],
                defaults={
                    'name': a_data['name'],
                    'asset_type': a_data['type'],
                    'cost': a_data['cost'],
                    'status': Asset.Statuses.IN_STOCK
                }
            )
            asset_objs.append(asset)
            if created:
                self.stdout.write(f"Added asset item: {asset.name}")

        # Allocate an Asset
        asset_to_assign = asset_objs[0]
        if asset_to_assign.status == Asset.Statuses.IN_STOCK:
            asset_to_assign.status = Asset.Statuses.IN_USE
            asset_to_assign.save()
            
            # Allocation entry
            allocation = AssetAllocation.objects.create(
                asset=asset_to_assign,
                assigned_to=employees[0],
                allocated_by=admin_user,
                status='ACTIVE'
            )
            AssetHistory.objects.create(
                asset=asset_to_assign,
                action='Allocated',
                performed_by=admin_user,
                details=f"Laptop assigned to employee: {employees[0].username}"
            )
            self.stdout.write(f"Allocated laptop to {employees[0].username}")

        # 7. Create Incidents
        # Incident 1: Core Router is down
        Incident.objects.get_or_create(
            title='Core Router Floor 3 completely offline',
            defaults={
                'description': 'Floor 3 has lost all WiFi and ethernet connectivity. The status lights on the router are blinking orange.',
                'caller': employees[1],
                'assigned_to': support_agents[0],
                'status': Incident.Statuses.IN_PROGRESS,
                'priority': Incident.Priorities.CRITICAL,
                'urgency': Incident.Urgencies.HIGH,
                'impact': Incident.Impacts.HIGH,
                'category': 'Network',
                'affected_ci': ci_router,
                'sla_due': timezone.now() + timedelta(hours=2)
            }
        )

        # Incident 2: Database slowing down
        Incident.objects.get_or_create(
            title='Slow database query response times',
            defaults={
                'description': 'Application dashboards are taking up to 15 seconds to load. Database CPU usage is hitting 98%.',
                'caller': employees[2],
                'assigned_to': support_agents[1],
                'status': Incident.Statuses.NEW,
                'priority': Incident.Priorities.HIGH,
                'urgency': Incident.Urgencies.HIGH,
                'impact': Incident.Impacts.MEDIUM,
                'category': 'Database',
                'affected_ci': ci_db,
                'sla_due': timezone.now() + timedelta(hours=4)
            }
        )

        # Incident 3: MS Teams Access denied (Resolved)
        inc_resolved, created = Incident.objects.get_or_create(
            title='Access denied to Microsoft Teams channels',
            defaults={
                'description': 'I cannot open any channels in MS Teams since morning. Getting a credentials mismatch prompt.',
                'caller': employees[0],
                'assigned_to': support_agents[2],
                'status': Incident.Statuses.RESOLVED,
                'priority': Incident.Priorities.MEDIUM,
                'urgency': Incident.Urgencies.MEDIUM,
                'impact': Incident.Impacts.LOW,
                'category': 'Software',
                'sla_due': timezone.now() - timedelta(hours=5),
                'resolved_at': timezone.now() - timedelta(minutes=30),
                'root_cause': 'Active Directory sync delay',
                'resolution_notes': 'Forced profile sync in AD console. Employee relogged and confirmed access is restored.'
            }
        )
        
        # 8. Create a Problem
        Problem.objects.get_or_create(
            title='Recurring Database CPU spikes',
            defaults={
                'description': 'Multiple incidents reported regarding slow query responses linked to CPU spikes on Production Database Server.',
                'status': Problem.Statuses.INVESTIGATION,
                'assigned_to': support_agents[1],
                'workaround': 'Restart database connection pool when CPU usage exceeds 95%.'
            }
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with complete enterprise operations data.'))
