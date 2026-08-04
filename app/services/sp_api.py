import requests
from app.dependencies import (
    LWA_CLIENT_ID,
    LWA_CLIENT_SECRET,
    LWA_REFRESH_TOKEN,
    SELLER_ID,
    MARKETPLACE_ID,
)


def get_access_token() -> str:
    response = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": LWA_REFRESH_TOKEN,
            "client_id": LWA_CLIENT_ID,
            "client_secret": LWA_CLIENT_SECRET,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def check_asin_restriction(asin: str, access_token: str) -> dict:
    url = "https://sellingpartnerapi-eu.amazon.com/listings/2021-08-01/restrictions"
    headers = {
        "x-amz-access-token": access_token,
        "Content-Type": "application/json",
    }
    params = {
        "asin": asin,
        "sellerId": SELLER_ID,
        "marketplaceIds": MARKETPLACE_ID,
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        restrictions = data.get("restrictions", [])
        if not restrictions:
            return {"asin": asin, "status": "ELIGIBLE", "reason": None}

        reasons = restrictions[0].get("reasons", [{}])
        reason_code = reasons[0].get("reasonCode", "UNKNOWN")
        has_links = any(reason.get("links") for reason in reasons)

        if has_links:
            return {"asin": asin, "status": "APPROVAL_REQUIRED", "reason": reason_code}
        return {"asin": asin, "status": "NOT_ELIGIBLE", "reason": reason_code}

    return {"asin": asin, "status": "ERROR", "reason": f"HTTP {response.status_code}"}