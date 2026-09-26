from django.contrib.auth import logout


class SessionEpochMiddleware:
    """End any session whose epoch no longer matches the person's. A requester
    can bump the other party's epoch to sign them out everywhere."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            if request.session.get("epoch", 0) != user.session_epoch:
                logout(request)
        return self.get_response(request)
