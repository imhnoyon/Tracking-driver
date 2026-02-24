from rest_framework import serializers
from .models import Driver, DriverLocation
from django.contrib.auth.models import User

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = "__all__"


class DriverLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverLocation
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['id','username','email']