from django.contrib import admin
from .models import *
# Register your models here.
# admin.site.register(Driver)
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('id',"user", "vehicle_number")
admin.site.register(DriverLocation)