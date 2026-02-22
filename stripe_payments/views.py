# views.py
import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token

from .models import Payment
from .serializers import RegisterSerializer, LoginSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "message": "User created successfully",
                "token": token.key
            })
        return Response(serializer.errors, status=400)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )

        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "message": "Login successful",
                "token": token.key
            })
        return Response({"error": "Invalid credentials"}, status=401)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "username": request.user.username
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        return Response({"message": "Logged out successfully"})


class PaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(user=request.user).order_by('-created_at')
        data = [{
            "id": p.id,
            "amount": p.amount / 100,  # Convert cents to dollars for display
            "paid": p.paid,
            "session_id": p.stripe_session_id,
            "created_at": p.created_at
        } for p in payments]
        return Response(data)


class CreateCheckoutSession(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # You can pass product details in the request body
            product_name = request.data.get('product_name', 'Default Product')
            amount = int(request.data.get('amount', 50000000))  # amount in cents
            quantity = int(request.data.get('quantity', 1))
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': product_name,
                        },
                        'unit_amount': amount,
                    },
                    'quantity': quantity,
                }],
                mode='payment',
                # In production, these should be full URLs to your frontend
                success_url=request.build_absolute_uri('/stripe/success/'),
                cancel_url=request.build_absolute_uri('/stripe/cancel/'),
            )


            # Save pending payment
            Payment.objects.create(
                user=request.user,
                stripe_session_id=session.id,
                amount=amount * quantity
            )

            return Response({'sessionId': session.id, 'checkoutUrl': session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session['id']

        try:
            payment = Payment.objects.get(stripe_session_id=session_id)
            payment.paid = True
            payment.save()
            print(f"Payment successful for session {session_id}")
        except Payment.DoesNotExist:
            print(f"Payment record not found for session {session_id}")

    return HttpResponse(status=200)