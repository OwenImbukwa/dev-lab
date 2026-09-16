# Stripe payments — Django / DRF

The `payments` app of a Django REST Framework backend, handling Stripe
payment intents and webhooks. Shown here as a standalone sample of the
pattern, not a runnable module — the imports (`OrderService`,
`PaymentRepository`, order/payment models) belong to the rest of the app.

- `views.py` — thin API controllers: create a Stripe PaymentIntent for an
  order, and receive/verify Stripe webhook events. No business logic here,
  just request handling and delegation to the service.
- `services.py` — the actual rules:
  - the charge amount is recomputed server-side from the order's line
    items on every intent creation; the client never gets to say how much
    to charge
  - the webhook handler verifies the Stripe signature before doing
    anything else
  - `payment_intent.succeeded` / `payment_intent.payment_failed` are
    handled idempotently (looked up by Stripe's payment intent id, safe
    against retried webhook deliveries) and only then does the order get
    marked paid

Views stay thin, services hold business rules, and repositories (not
included here) are the only layer that touches the ORM.
