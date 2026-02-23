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

from .models import Payment, StripeAccount
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
                "user_id": user.id,
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
                "user_id": user.id,
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
            amount = int(request.data.get('amount', 500))  # amount in cents
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


class ConnectStripeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Creates a Stripe Express account and returns an onboarding link.
        """
        try:
            # Check if user already has an account
            stripe_account, created = StripeAccount.objects.get_or_create(user=request.user)
            
            if not stripe_account.stripe_account_id:
                # Create a new Express account
                account = stripe.Account.create(
                    type="express",
                    country="US",  # Or dynamic based on user profile
                    email="mahedi.dev2002@gmail.com",
                    capabilities={
                        "card_payments": {"requested": True},
                        "transfers": {"requested": True},
                    },
                )
                stripe_account.stripe_account_id = account.id
                stripe_account.save()

            # Create an account link for onboarding
            # account_link = stripe.AccountLink.create(
            #     account=stripe_account.stripe_account_id,
            #     refresh_url=request.build_absolute_uri('/stripe/connect-refresh/'),
            #     return_url=request.build_absolute_uri('/stripe/connect-success/'),
            #     type="account_onboarding",
            # )

            return Response({
                "account_id": stripe_account.stripe_account_id,
                # "onboarding_url": account_link.url
                
            })
        except Exception as e:
            print(f"Error in ConnectStripeView: {str(e)}")
            return Response({"error": str(e)}, status=400)


class TransferMoneyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Transfer money from platform balance to a recipient's Stripe account.
        Payload: {"recipient_id": 1, "amount": 1000} (amount in cents)
        """
        try:
            recipient_id = request.data.get('recipient_id')
            amount = int(request.data.get('amount'))
            
            recipient_user = User.objects.get(id=recipient_id)
            recipient_stripe = StripeAccount.objects.get(user=recipient_user)

            if not recipient_stripe.stripe_account_id:
                
                return Response({"error": "Recipient does not have a linked Stripe account"}, status=400)

            # Perform the transfer
            transfer = stripe.Transfer.create(
                amount=amount,
                currency="usd",
                destination=recipient_stripe.stripe_account_id,
                description=f"Transfer to {recipient_user.username}",
            )
             # Create an account link for onboarding
            stripe_account, _ = StripeAccount.objects.get_or_create(user=recipient_user)
            account_link = stripe.AccountLink.create(
                account=stripe_account.stripe_account_id,
                refresh_url=request.build_absolute_uri('/stripe/connect-refresh/'),
                return_url=request.build_absolute_uri('/stripe/connect-success/'),
                type="account_onboarding",
            )
            return Response({
                "message": "Transfer successful",
                "transfer_id": transfer.id,
                "amount": amount,
                "onboarding_url": account_link.url
            })
        except User.DoesNotExist:
            return Response({"error": "Recipient user not found"}, status=404)
        except StripeAccount.DoesNotExist:
            return Response({"error": "Recipient has no Stripe account"}, status=400)
        except Exception as e:
            print(f"Error in TransferMoneyView: {str(e)}")
            return Response({"error": str(e)}, status=400)


class CreateTransferCheckoutSession(APIView):
    """
    Creates a Checkout Session that automatically transfers a portion of the payment 
    to a connected account when completed. (Real-time transfer)
    Payload: {"recipient_id": 1, "amount": 5000, "commission_pct": 10}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            recipient_id = request.data.get('recipient_id')
            total_amount = int(request.data.get('amount')) # total in cents
            commission_pct = int(request.data.get('commission_pct', 10))

            recipient_user = User.objects.get(id=recipient_id)
            recipient_stripe = StripeAccount.objects.get(user=recipient_user)

            # Calculate transfer amount (what goes to the driver/seller)
            transfer_amount = int(total_amount * (100 - commission_pct) / 100)

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': f'Payment for {recipient_user.username}'},
                        'unit_amount': total_amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                payment_intent_data={
                    'transfer_data': {
                        'destination': recipient_stripe.stripe_account_id,
                        'amount': transfer_amount,
                    },
                },
                success_url=request.build_absolute_uri('/stripe/success/'),
                cancel_url=request.build_absolute_uri('/stripe/cancel/'),
            )

            Payment.objects.create(
                user=request.user,
                stripe_session_id=session.id,
                amount=total_amount
            )

            return Response({'sessionId': session.id, 'checkoutUrl': session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class StripeLoginLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Generates a login link for the connected user's Stripe Express dashboard.
        """
        try:
            stripe_account = StripeAccount.objects.get(user=request.user)
            if not stripe_account.stripe_account_id:
                return Response({"error": "No Stripe account linked"}, status=400)

            link = stripe.Account.create_login_link(stripe_account.stripe_account_id)
            return Response({"url": link.url})
        except StripeAccount.DoesNotExist:
            return Response({"error": "No Stripe account linked"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class SendMoneyByCardView(APIView):
    """
    Allows a user to send money to another user by entering card details.
    The money goes directly to the recipient's Stripe account.
    Payload: {"recipient_id": 1, "amount": 1000} (amount in cents)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            recipient_id = request.data.get('recipient_id')
            amount = int(request.data.get('amount'))

            recipient_user = User.objects.get(id=recipient_id)
            recipient_stripe = StripeAccount.objects.get(user=recipient_user)

            if not recipient_stripe.stripe_account_id:
                return Response({"error": "Recipient has not linked their Stripe account"}, status=400)

            # Create a Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"Payment to {recipient_user.username}",
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                payment_intent_data={
                    'transfer_data': {
                        'destination': recipient_stripe.stripe_account_id,
                    },
                },
                success_url=request.build_absolute_uri('/stripe/success/'),
                cancel_url=request.build_absolute_uri('/stripe/cancel/'),
            )

            # Record the pending payment
            Payment.objects.create(
                user=request.user,
                stripe_session_id=session.id,
                amount=amount
            )

            return Response({
                'checkoutUrl': session.url,
                'sessionId': session.id
            })

        except User.DoesNotExist:
            return Response({"error": "Recipient user not found"}, status=404)
        except StripeAccount.DoesNotExist:
            return Response({"error": "Recipient has no Stripe account"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


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