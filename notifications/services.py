import logging
from django.conf import settings
from .models import Notification

logger = logging.getLogger(__name__)

def create_notification(recipient, title, message, notification_type='INFO', link=None):
    """
    Creates an in-app notification and triggers mock email dispatch in application logs.
    """
    try:
        notification = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
        # Logging email dispatch
        logger.info(f"SMTP Mock Email sent to {recipient.email or recipient.username} - Subject: {title} | Content: {message}")
        return notification
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return None
