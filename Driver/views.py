from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Driver, DriverLocation
from .serializers import DriverLocationSerializer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class UpdateDriverLocation(APIView):

    def post(self, request):
        driver_id = request.data.get("driver_id")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")

        try:
            driver = Driver.objects.get(id=driver_id)
        except Driver.DoesNotExist:
            return Response({"error": "Driver not found"}, status=404)

        location = DriverLocation.objects.create(
            driver=driver,
            latitude=latitude,
            longitude=longitude
        )

        # Send to WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "admin_tracking",
            {
                "type": "send_location",
                "driver_id": driver.id,
                "latitude": latitude,
                "longitude": longitude,
            }
        )

        return Response({"status": "Location updated"})
