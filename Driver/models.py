from django.db import models
from django.contrib.auth.models import User


class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    vehicle_number = models.CharField(max_length=50)

    def __str__(self):
        return self.user.username


class DriverLocation(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.driver.user.username} - {self.latitude}, {self.longitude}"
