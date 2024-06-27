"""Middleware to allow custom delete logic."""

import threading


class GlobalRequestMiddleware:
    """Middleware to track keep track of the request through all the processing."""

    _threadmap = {}

    def __init__(self, get_response):
        """Init."""
        self.get_response = get_response

    def __call__(self, request):
        """Call."""
        self._threadmap[threading.get_ident()] = request
        response = self.get_response(request)
        try:
            del self._threadmap[threading.get_ident()]
        except KeyError:
            pass
        return response

    @classmethod
    def get_current_request(cls):
        """Get the request context within the Thread."""
        try:
            return cls._threadmap[threading.get_ident()]
        except KeyError:
            return None
