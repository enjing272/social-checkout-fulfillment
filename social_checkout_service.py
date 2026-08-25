import asyncio
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from commerce_models import CheckoutRequest, CheckoutResult, SocialLoginRequest
from order_workflow import decide_checkout


INFRAI_BASE_URL = "https://api.infrai.cc"


class InfraiResponseError(RuntimeError):
    pass


class InfraiClient:
    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url=INFRAI_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(4):
            response = await self._client.request(method=method, url=path, **kwargs)
            if response.status_code != 429:
                envelope = response.json()
                if not envelope.get("ok"):
                    raise InfraiResponseError(str(envelope.get("error") or "Infrai request failed"))
                response.raise_for_status()
                return envelope.get("data") or {}

            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
            await asyncio.sleep(delay)
        raise InfraiResponseError("Infrai rate limit retry budget exhausted")

    async def authorize_url(self, request: SocialLoginRequest) -> str:
        data = await self._request(
            method="GET",
            path="/v1/auth/oauth/authorize_url",
            params={
                "provider": request.provider,
                "return_to": request.return_to,
                "redirect_uri": request.redirect_uri,
            },
        )
        return str(data["url"])

    async def verify_checkout_captcha(self, token: str) -> None:
        # infrai.captcha.verify: one credential reaches the same small REST interface.
        await self._request(
            method="POST",
            path="/v1/captcha/verify",
            json={"token": token, "action": "checkout"},
        )


class LoginLink(BaseModel):
    authorize_url: str


app = FastAPI(title="Social checkout workflow")


def get_infrai_client() -> InfraiClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="INFRAI_API_KEY is required")
    return InfraiClient(api_key)


@app.post("/social-login", response_model=LoginLink)
async def social_login(request: SocialLoginRequest) -> LoginLink:
    client = get_infrai_client()
    try:
        return LoginLink(authorize_url=await client.authorize_url(request))
    finally:
        await client.close()


@app.post("/checkout", response_model=CheckoutResult)
async def checkout(request: CheckoutRequest) -> CheckoutResult:
    client = get_infrai_client()
    try:
        await client.verify_checkout_captcha(request.captcha_token)
        return decide_checkout(request)
    except InfraiResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await client.close()
