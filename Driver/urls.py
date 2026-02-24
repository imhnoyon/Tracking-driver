from django.urls import path
from .views import *

urlpatterns = [
    path("update-location/", UpdateDriverLocation.as_view()),
    path("users-list/", UserListView.as_view()),
]
