from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings

@api_view(["GET"])
def health(request):
    return Response({
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    })

urlpatterns = [
    path("health", health),
    path("api/v1/", include("core.urls")),
]
