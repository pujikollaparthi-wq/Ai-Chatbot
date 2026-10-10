from ai_agent.models import AIChatSession

def chat_session(request):
    """Automatically injects chat_session_id into the template context for authenticated users."""
    if request.user.is_authenticated:
        try:
            chat_session = AIChatSession.objects.filter(user=request.user).first()
            if not chat_session:
                chat_session = AIChatSession.objects.create(user=request.user)
            return {'chat_session_id': chat_session.id}
        except Exception:
            return {}
    return {}
