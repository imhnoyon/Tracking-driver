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
    
    # Stripe Connect Endpoints
    path('connect-account/', ConnectStripeView.as_view(), name='connect-stripe-account'),
    path('transfer/', TransferMoneyView.as_view(), name='stripe-transfer'),
    path('transfer-payment/', CreateTransferCheckoutSession.as_view(), name='create-transfer-payment'),
    path('login-link/', StripeLoginLinkView.as_view(), name='stripe-login-link'),
    path('send-money-card/', SendMoneyByCardView.as_view(), name='send-money-by-card'),
    
    # Simple templates or responses for success/cancel
    path('success/', lambda r: HttpResponse("Payment Successful!"), name='payment-success'),
    path('cancel/', lambda r: HttpResponse("Payment Cancelled!"), name='payment-cancel'),
    path('connect-success/', lambda r: HttpResponse("Stripe Account Connected successfully!"), name='connect-success'),
    path('connect-refresh/', lambda r: HttpResponse("Please refresh or restart onboarding."), name='connect-refresh'),
]
