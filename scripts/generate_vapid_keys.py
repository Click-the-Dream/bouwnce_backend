"""Generate a VAPID key pair for Web Push notifications.

Usage:
    .venv/bin/python scripts/generate_vapid_keys.py

Prints:
  - VAPID_PRIVATE_KEY (PEM): set this as the `VAPID_PRIVATE_KEY` env var on the backend.
  - APPLICATION_SERVER_KEY (base64url): give this to the frontend as the
    `applicationServerKey` argument of `PushManager.subscribe()`.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def main() -> None:
    vapid = Vapid()
    vapid.generate_keys()

    private_key_pem = vapid.private_pem().decode()
    public_key_der = serialization.load_pem_public_key(vapid.public_pem()).public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    application_server_key = (
        base64.urlsafe_b64encode(public_key_der).rstrip(b"=").decode()
    )

    print("VAPID_PRIVATE_KEY (PEM — set as env var):")
    print(private_key_pem)
    print()
    print(
        "APPLICATION_SERVER_KEY (base64url — frontend PushManager.subscribe "
        "applicationServerKey):"
    )
    print(application_server_key)


if __name__ == "__main__":
    main()
