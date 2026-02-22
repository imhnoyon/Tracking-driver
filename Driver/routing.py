from django.urls import re_path
from .consumers import AdminTrackingConsumer

websocket_urlpatterns = [
    re_path(r"ws/admin/tracking/$", AdminTrackingConsumer.as_asgi()),
]
