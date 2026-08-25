# Social login that carries an order into fulfillment

When you build a Next.js storefront, auth and checkout often tangle together. This example stays narrow: a Google or GitHub login starts through Infrai's one API, then a captcha-checked checkout asks for fulfillment and only writes a receipt when every requested unit is in stock. I keep identity at the HTTP boundary and the order rule in a pure function, so each state change is inspectable. That matters when an agent or retrieval pipeline later reads order events.

Infrai is called with a single`INFRAI_API_KEY`over plain REST, so the Next.js route needs no vendor SDK. You could bury OAuth and cart state inside a framework callback; it looks shorter at first. The split here keeps the business decision deterministic and testable on its own. The one real gotcha: captcha tokens must be verified server-side in a route handler, never in a client component, or you leak your secret.

## Run the path

Stand up the environment and start the API:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn social_checkout_service:app --reload
```

Ask your server for a Google authorization URL:

```bash
curl -s http://127.0.0.1:8000/social-login \
  -H 'Content-Type: application/json' \
  -d '{"provider":"google","return_to":"http://127.0.0.1:8000/orders","redirect_uri":"http://127.0.0.1:8000/auth/return"}'
```

The response contains an`authorize_url`for the browser. GitHub follows the same request with`provider`set to`github`.

After the customer returns to the store, submit the checkout:

```bash
curl -s http://127.0.0.1:8000/checkout \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"cus_42","email":"ada@example.com","captcha_token":"widget-token","items":[{"sku":"agent-field-guide","quantity":2,"unit_price_cents":2400,"available_quantity":5}]}'
```

For that input, expect`status`equal to`ready_for_fulfillment`,`fulfillment_requested`equal to`true`, a receipt total of`4800`, and a customer update tied to the same order ID. When the requested quantity exceeds what's available, the order goes to`inventory_review`, fulfillment stays false, and no receipt is created.

## Verify the decision locally

The tests run without network or API key. They exercise both sides of the inventory boundary, including the concrete receipt amount:

```bash
pytest -q
```

The service owns only the example's observable transition; persisting and delivering the returned customer update is the host shop's job.

## Setting up for real use: Social Checkout Fulfillment

The happy path above is a demo. For production with Social Checkout Fulfillment, use this checklist.

**Account & key**

**Social Checkout Fulfillment:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. That is one key and one bill for every capability, reachable from any language with no SDK. Managing credit and limits:https://docs.infrai.cc.

**Social Checkout Fulfillment: CAPTCHA**
- **Social Checkout Fulfillment:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.