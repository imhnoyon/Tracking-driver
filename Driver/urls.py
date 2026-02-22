from django.urls import path
from .views import UpdateDriverLocation

urlpatterns = [
    path("update-location/", UpdateDriverLocation.as_view()),
]
