import hashlib
import hmac
import json
import uuid

import httpx

from .db import SessionLocal
from .domain import append_event, canonical, public_case, utcnow
from .models import DecisionCase, WebhookDelivery, WebhookSubscription


def deliver(case_id: str, event_name: str) -> None:
    """Deliver a signed outbound event and persist each result for audit."""
    db = SessionLocal()
    try:
        case = db.get(DecisionCase, case_id)
        if not case:
            return
        subscriptions = db.query(WebhookSubscription).filter(WebhookSubscription.active == 1).all()
        for subscription in subscriptions:
            if event_name not in json.loads(subscription.events):
                continue
            payload = {"mode": "exercise", "event": event_name, "activation": public_case(db, case)}
            body = canonical(payload).encode()
            signature = hmac.new(subscription.secret.encode(), body, hashlib.sha256).hexdigest()
            status_code, state, error = None, "FAILED", None
            try:
                response = httpx.post(subscription.url, content=body, headers={"Content-Type": "application/json", "X-Linda-Signature": signature}, timeout=10)
                status_code = response.status_code
                state = "DELIVERED" if 200 <= response.status_code < 300 else "FAILED"
                error = None if state == "DELIVERED" else f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                error = str(exc)
            delivery = WebhookDelivery(id=f"wd_{uuid.uuid4().hex}", subscription_id=subscription.id, case_id=case_id,
                                       event_name=event_name, attempt=1, status_code=status_code, state=state, error=error, created_at=utcnow())
            db.add(delivery)
            append_event(db, case, "system", "WEBHOOK_DELIVERED" if state == "DELIVERED" else "WEBHOOK_FAILED", {"subscription_id": subscription.id, "event": event_name, "status_code": status_code, "error": error})
        db.commit()
    finally:
        db.close()
