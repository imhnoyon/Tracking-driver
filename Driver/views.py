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

from .paginations import UserPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework import generics
from django.contrib.auth.models import User
from .serializers import UserSerializer
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class=UserSerializer
    pagination_class=UserPagination
    filter_backends = [SearchFilter,DjangoFilterBackend] 
    search_fields =['id','username','email']
    filterset_fields = ['id']
    
    def list(self, request, *args, **kwargs):
        queryset=self.filter_queryset(self.get_queryset())
        try:
            page=self.paginate_queryset(queryset)
            if page is not None:
                serializer =self.get_serializer(page,many=True)
                return Response({
                    "success": True,
                     "status": 200,
                    "message": "Users retrieved successfully",
                    "data": serializer.data
                }, status=status.HTTP_200_OK)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                "success": True,
                 "status": 200,
                "message": "Users retrieved successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": True,
                "status": 200,
                "message": "No data found for this page.",
                "data": []
            })