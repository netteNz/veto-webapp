# server/api/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def healthz(_):
    return JsonResponse({"ok": True})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('veto.urls')),   # delegate to the app
] + [path('healthz/', healthz)]