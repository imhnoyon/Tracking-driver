from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'paid', 'created_at')
    list_filter = ('paid', 'created_at')
    search_fields = ('stripe_session_id', 'user__username')
