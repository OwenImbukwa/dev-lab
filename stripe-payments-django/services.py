from decimal import Decimal

import stripe
from django.conf import settings
from django.db.models import DecimalField, ExpressionWrapper, F, Sum

from apps.core.exceptions import ValidationFailedError
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.payments.models import Payment
from apps.payments.repositories import PaymentRepository

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:
    def __init__(self, repository: PaymentRepository | None = None):
        self.repository = repository or PaymentRepository()

    def create_intent_for_order(self, order: Order) -> tuple[Payment, str]:
        if order.status != Order.Status.PENDING:
            raise ValidationFailedError("This order isn't awaiting payment.")

        amount_cents = self._amount_in_cents(order)
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            automatic_payment_methods={"enabled": True},
            metadata={"order_id": str(order.id)},
        )
        payment = self.repository.create(
            order=order,
            stripe_payment_intent_id=intent.id,
            amount=Decimal(amount_cents) / 100,
        )
        return payment, intent.client_secret

    def handle_payment_succeeded(self, payment_intent_id: str) -> None:
        payment = self.repository.get_by_payment_intent_id(payment_intent_id)
        if payment is None:
            return
        self.repository.update_status(payment, status=Payment.Status.SUCCEEDED)
        OrderService().mark_paid(payment.order)

    def handle_payment_failed(self, payment_intent_id: str, failure_message: str) -> None:
        payment = self.repository.get_by_payment_intent_id(payment_intent_id)
        if payment is None:
            return
        self.repository.update_status(payment, status=Payment.Status.FAILED, failure_message=failure_message)

    def _amount_in_cents(self, order: Order) -> int:
        total = order.items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
        )["total"] or Decimal("0")
        return int((total * 100).to_integral_value())
