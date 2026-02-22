from django.urls import path
from django.http import HttpResponse
from .views import *

urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/profile/', ProfileView.as_view(), name='profile'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/payments/', PaymentListView.as_view(), name='payment-list'),
    path('create-payment/', CreateCheckoutSession.as_view(), name='create-payment'),
    path('webhook/', stripe_webhook, name='stripe-webhook'),
    # Simple templates or responses for success/cancel
    path('success/', lambda r: HttpResponse("Payment Successful!"), name='payment-success'),
    path('cancel/', lambda r: HttpResponse("Payment Cancelled!"), name='payment-cancel'),
]
