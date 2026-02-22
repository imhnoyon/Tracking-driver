import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AdminTrackingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.group_name = "admin_tracking"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_location(self, event):
        await self.send(text_data=json.dumps({
            "driver_id": event["driver_id"],
            "latitude": event["latitude"],
            "longitude": event["longitude"],
        }))
