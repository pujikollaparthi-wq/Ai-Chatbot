from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Users see only their own notifications."""
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'Notification marked as read.'})

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_as_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'All notifications marked as read.'})

# Template-based browser views
@login_required
def notification_list(request):
    """Renders all notifications and marks unread ones as read."""
    notifications = Notification.objects.filter(recipient=request.user)
    # Mark them as read when opening notifications page
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications/list.html', {'notifications': notifications})
