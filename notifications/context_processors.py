from .models import Notification
import os
from django.conf import settings

def unread_notifications(request):
    """Exposes unread notifications counts, items, and dynamic user avatar URL to all templates."""
    context = {}
    if request.user.is_authenticated:
        context['unread_notifications_count'] = Notification.objects.filter(recipient=request.user, is_read=False).count()
        context['latest_notifications'] = Notification.objects.filter(recipient=request.user, is_read=False)[:5]
        
        # Check if custom avatar exists in static directory
        avatar_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'avatars', f"{request.user.username}.png")
        if os.path.exists(avatar_path):
            mtime = os.path.getmtime(avatar_path)
            context['avatar_url'] = f"/static/img/avatars/{request.user.username}.png?v={mtime}"
        else:
            context['avatar_url'] = f"https://ui-avatars.com/api/?name={request.user.first_name}+{request.user.last_name}&background=4f46e5&color=fff&size=100"
    else:
        context['unread_notifications_count'] = 0
        context['latest_notifications'] = []
        context['avatar_url'] = "https://ui-avatars.com/api/?name=Guest&background=4f46e5&color=fff&size=100"
    return context
