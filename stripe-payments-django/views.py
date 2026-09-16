import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.orders.services import OrderService
from apps.payments.services import PaymentService


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment_intent(request, order_id: int):
    order = OrderService().get_by_id_for_user(order_id, request.user)
    payment, client_secret = PaymentService().create_intent_for_order(order)

    return Response(
        {
            "client_secret": client_secret,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "amount": str(payment.amount),
        },
        status=201,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(request.body, signature, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        return Response(status=400)

    payment_service = PaymentService()
    intent = event["data"]["object"]

    if event["type"] == "payment_intent.succeeded":
        payment_service.handle_payment_succeeded(intent["id"])
    elif event["type"] == "payment_intent.payment_failed":
        last_error = intent["last_payment_error"]
        failure_message = last_error["message"] if last_error else ""
        payment_service.handle_payment_failed(intent["id"], failure_message)

    return Response(status=200)
