"""Token issuance and verification for the demo app."""

import hashlib
import hmac

SECRET = b"demo-secret"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(user_id: str) -> str:
    payload = f"{user_id}:demo"
    signature = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify(token: str) -> bool:
    user_id, tag, signature = token.rsplit(":", 2)
    expected = hmac.new(SECRET, f"{user_id}:{tag}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
