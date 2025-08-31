from rest_framework.views import exception_handler

def drf_exception_handler(exc, context):
    resp = exception_handler(exc, context)
    if resp is not None:
        # add a consistent envelope
        resp.data = {
            "detail": resp.data.get("detail", resp.data),
            "status": resp.status_code,
        }
    return resp
