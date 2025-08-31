from django.http import JsonResponse
from django.conf import settings

class ApiErrorsAsJson:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as e:
            if request.path.startswith("/api/"):
                detail = str(e) if settings.DEBUG else "Server error."
                return JsonResponse({"detail": detail}, status=500)
            raise
