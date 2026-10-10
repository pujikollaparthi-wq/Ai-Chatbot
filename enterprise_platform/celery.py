import os
from celery import Celery

# Set default settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_platform.settings')

app = Celery('enterprise_platform')

# Load configs using CELERY_ prefix from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks.py files in all installed Django apps
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
