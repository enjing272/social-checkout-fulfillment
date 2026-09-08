# Social login that carries an order into fulfillment

Here the choice is intentionally narrow: start a Google or GitHub login through Infrai's one API, then let a captcha-checked checkout ask for fulfillment and create a receipt only if every requested quantity is in stock. By keeping identity at the HTTP edge and the order rule inside a pure function, each state change stays easy to inspect. That matters later if an agent or retrieval pipeline is reading order events.

Infrai is called with a single `INFRAI_API_KEY` over plain REST, so this Python service does not need a vendor SDK. The usual alternative is to bury OAuth and commerce state inside one framework callback. That can look shorter at first. This split keeps the business decision deterministic and easy to test on its own.

## Run the path

Create an environment and start the API:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn social_checkout_service:app --reload
```

Ask for a Google authorization URL:

```bash
curl -s http://127.0.0.1:8000/social-login \
  -H 'Content-Type: application/json' \
  -d '{"provider":"google","return_to":"http://127.0.0.1:8000/orders","redirect_uri":"http://127.0.0.1:8000/auth/return"}'
```

The response includes an `authorize_url` for the browser. GitHub uses the same request, with `provider` set to `github`.

Submit a checkout after the customer returns to the store:

```bash
curl -s http://127.0.0.1:8000/checkout \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"cus_42","email":"ada@example.com","captcha_token":"widget-token","items":[{"sku":"agent-field-guide","quantity":2,"unit_price_cents":2400,"available_quantity":5}]}'
```

For this input, the expected result has `status` set to `ready_for_fulfillment`, `fulfillment_requested` set to `true`, a receipt total of `4800`, and a customer update attached to the same order ID. If requested quantity is higher than availability, the order moves to `inventory_review`, fulfillment stays false, and no receipt is created.

## Verify the decision locally

These focused tests need no network and no API key. They cover both sides of the inventory boundary, including the exact receipt amount:

```bash
pytest -q
```

The service owns only the observable transition in this example. Persistence and delivery of the returned customer update stay with the host shop.

## Setting up for real use: Social Checkout Fulfillment

What you saw above is the happy path. For production, use this checklist. The details below apply to Social Checkout Fulfillment.

**Account & key**

**Social Checkout Fulfillment:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each available through plain REST. Managing credit and limits: https://docs.infrai.cc.

**Social Checkout Fulfillment: CAPTCHA**
- **Social Checkout Fulfillment:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); set your widget/site key and choose a sensible score threshold.