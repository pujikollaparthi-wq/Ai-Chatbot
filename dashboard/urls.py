from django.urls import path
from .views import (
    dashboard_redirect, employee_portal, manager_portal,
    support_portal, executive_dashboard, chart_data_api,
    incidents_list, incident_detail, requests_list, problems_list, changes_list,
    kb_list, assets_list, asset_detail, how_it_works, settings_page,
    close_incident, reopen_incident, add_incident_comment, upload_incident_attachment,
    submit_incident_feedback, get_ai_suggestions, get_similar_incidents,
    predictive_alerts_dashboard, api_evaluate_infrastructure, proactive_create_ticket,
    export_incidents_csv, export_incidents_excel, export_incidents_pdf,
    export_single_incident_pdf, dashboard_metrics_api
)

urlpatterns = [
    path('', dashboard_redirect, name='dashboard-redirect'),
    path('how-it-works/', how_it_works, name='how-it-works'),
    path('portal/employee/', employee_portal, name='employee-portal'),
    path('portal/manager/', manager_portal, name='manager-portal'),
    path('portal/support/', support_portal, name='support-portal'),
    path('portal/executive/', executive_dashboard, name='executive-dashboard'),
    
    # Sidebar custom list views
    path('incidents/', incidents_list, name='incidents-list'),
    path('incidents/<uuid:pk>/', incident_detail, name='incident-detail'),
    path('requests/', requests_list, name='requests-list'),
    path('problems/', problems_list, name='problems-list'),
    path('changes/', changes_list, name='changes-list'),
    path('kb/', kb_list, name='kb-list'),
    path('assets/', assets_list, name='assets-list'),
    path('assets/<uuid:pk>/', asset_detail, name='asset-detail'),
    
    path('settings/', settings_page, name='settings'),
    
    path('api/charts/', chart_data_api, name='chart-data-api'),

    # Lifecycle paths
    path('incidents/<uuid:pk>/close/', close_incident, name='close-incident'),
    path('incidents/<uuid:pk>/reopen/', reopen_incident, name='reopen-incident'),

    # Interactive components paths
    path('incidents/<uuid:pk>/comment/', add_incident_comment, name='add-incident-comment'),
    path('incidents/<uuid:pk>/attachment/', upload_incident_attachment, name='upload-incident-attachment'),
    path('incidents/<uuid:pk>/feedback/', submit_incident_feedback, name='submit-incident-feedback'),

    # AI Advisors paths
    path('incidents/<uuid:pk>/ai-suggest/', get_ai_suggestions, name='get-ai-suggestions'),
    path('incidents/<uuid:pk>/similar/', get_similar_incidents, name='get-similar-incidents'),

    # AIOps Outage Predictor paths
    path('aiops/predictive-alerts/', predictive_alerts_dashboard, name='predictive-alerts'),
    path('api/aiops/evaluate/', api_evaluate_infrastructure, name='api-evaluate-infrastructure'),
    path('aiops/create-proactive-ticket/', proactive_create_ticket, name='proactive-create-ticket'),

    # Reporting & Queue Exports paths
    path('incidents/export/csv/', export_incidents_csv, name='export-incidents-csv'),
    path('incidents/export/excel/', export_incidents_excel, name='export-incidents-excel'),
    path('incidents/export/pdf/', export_incidents_pdf, name='export-incidents-pdf'),
    path('incidents/<uuid:pk>/export/pdf/', export_single_incident_pdf, name='export-single-incident-pdf'),
    path('api/dashboard/metrics/', dashboard_metrics_api, name='dashboard-metrics-api'),
]


