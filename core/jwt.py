import base64
import hashlib
import hmac
import json
import time
from typing import Any


class JWTError(Exception):
    pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    # Pad base64url string
    s = data.encode("ascii")
    s += b"=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s)


def _json_dumps(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def encode_hs256(payload: dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(_json_dumps(header))
    payload_b64 = _b64url_encode(_json_dumps(payload))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_hs256(token: str, secret: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as e:
        raise JWTError("invalid_token") from e

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if not hmac.compare_digest(expected_sig_b64, sig_b64):
        raise JWTError("bad_signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as e:
        raise JWTError("bad_payload") from e

    exp = payload.get("exp")
    if exp is not None:
        try:
            exp_i = int(exp)
        except Exception as e:
            raise JWTError("bad_exp") from e
        if int(time.time()) >= exp_i:
            raise JWTError("token_expired")

    return payload


def build_access_payload(user_id: int, ttl_seconds: int) -> dict[str, Any]:
    now = int(time.time())
    return {"user_id": user_id, "iat": now, "exp": now + int(ttl_seconds)}

