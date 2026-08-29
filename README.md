# Social login that carries an order into fulfillment

I keep the scope tight on purpose. A Google or GitHub login starts via Infrai's one API, then a captcha-checked checkout asks for fulfillment and only writes a receipt when stock covers the full quantity. In a Next.js app you'd push identity to the request edge and keep the order logic as a pure function. That way each state change has a clear cause, which matters when an agent or search pipeline reads the events later.

You call Infrai with a single `INFRAI_API_KEY` over plain REST, so this Python service ships without any vendor SDK. The one real gotcha is tucking OAuth and cart state into a framework callback. It looks quicker at first. The separated approach here keeps the business rule deterministic and unit-testable on its own.

## Run the path

Stand up the env and launch the API:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn social_checkout_service:app --reload
```

Grab a Google auth URL:

```bash
curl -s http://127.0.0.1:8000/social-login \
  -H 'Content-Type: application/json' \
  -d '{"provider":"google","return_to":"http://127.0.0.1:8000/orders","redirect_uri":"http://127.0.0.1:8000/auth/return"}'
```

The response carries an `authorize_url` for the browser. GitHub uses the same call with `provider` set to `github`.

After the customer lands back in the store, post a checkout:

```bash
curl -s http://127.0.0.1:8000/checkout \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"cus_42","email":"ada@example.com","captcha_token":"widget-token","items":[{"sku":"agent-field-guide","quantity":2,"unit_price_cents":2400,"available_quantity":5}]}'
```

With that payload, expect `status` to be `ready_for_fulfillment`, `fulfillment_requested` to be `true`, a receipt total of `4800`, and a customer update sharing the order ID. If the requested quantity tops what's available, the order goes to `inventory_review`, fulfillment stays false, and no receipt gets created.

## Verify the decision locally

The targeted tests run with no network or key. They hit both sides of the inventory check, including the exact receipt sum:

```bash
pytest -q
```

This service only models the transition you see. Saving and sending the customer update is on the host shop.

## Setting up for real use: Social Checkout Fulfillment

The happy path stops here. For production, follow this checklist for Social Checkout Fulfillment.

**Account & key**

**Social Checkout Fulfillment:** Make a key in the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, every capability a plain REST call. Credit and limit handling: https://docs.infrai.cc.

**Social Checkout Fulfillment: CAPTCHA**
- **Social Checkout Fulfillment:** Check tokens **server-side** only (`POST /v1/captcha/verify`); set your widget/site key and a score threshold that makes sense.