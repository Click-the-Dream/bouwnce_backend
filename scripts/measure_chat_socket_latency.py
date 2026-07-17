from __future__ import annotations

import argparse
import asyncio
import json
import time

import websockets


async def _wait_for_message(websocket, expected_type: str | set[str], timeout: float):
    expected_types = (
        {expected_type} if isinstance(expected_type, str) else set(expected_type)
    )
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        remaining = max(0.1, deadline - time.perf_counter())
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
        except TimeoutError:
            continue
        message = json.loads(raw)
        if message.get("type") in expected_types:
            return message
    expected_label = " or ".join(sorted(expected_types))
    raise RuntimeError(f"Did not receive {expected_label} within {timeout}s")


def _build_ws_url(base_url: str, token: str) -> str:
    ws_base_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_base_url}/api/v1/events/ws?token={token}"


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure pure socket chat latency from websocket send to ack/delivery"
    )
    parser.add_argument(
        "--sender-token",
        required=True,
        help="Sender access token",
    )
    parser.add_argument(
        "--recipient-token",
        required=True,
        help="Recipient access token",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base API URL used to build websocket URLs",
    )
    parser.add_argument(
        "--message",
        default="socket latency test message",
        help="Message body to send",
    )
    parser.add_argument(
        "--recipient-id",
        required=True,
        help="Recipient user id",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Per-event receive timeout in seconds",
    )
    args = parser.parse_args()

    sender_ws_url = _build_ws_url(args.base_url, args.sender_token)
    recipient_ws_url = _build_ws_url(args.base_url, args.recipient_token)

    print(f"[setup] sender_ws={sender_ws_url}", flush=True)
    print(f"[setup] recipient_ws={recipient_ws_url}", flush=True)

    async with websockets.connect(
        recipient_ws_url, ping_interval=20, ping_timeout=20
    ) as recipient_ws:
        await _wait_for_message(recipient_ws, "chat.ready", args.timeout)

        async with websockets.connect(
            sender_ws_url, ping_interval=20, ping_timeout=20
        ) as sender_ws:
            await _wait_for_message(sender_ws, "chat.ready", args.timeout)

            client_id = f"socket-{int(time.time() * 1000)}"
            send_started = time.perf_counter()
            await sender_ws.send(
                json.dumps(
                    {
                        "type": "chat.send",
                        "recipient_id": args.recipient_id,
                        "body": args.message,
                        "client_id": client_id,
                    }
                )
            )

            send_ack_started = time.perf_counter()
            send_ack = await _wait_for_message(sender_ws, "chat.send.ack", args.timeout)
            send_ack_elapsed = time.perf_counter() - send_ack_started

            sent_started = time.perf_counter()
            sent = await _wait_for_message(sender_ws, "chat.sent", args.timeout)
            sent_elapsed = time.perf_counter() - sent_started

            recipient_started = time.perf_counter()
            message = await _wait_for_message(
                recipient_ws, "chat.message", args.timeout
            )
            recipient_elapsed = time.perf_counter() - recipient_started

            print("[result] send_ack:", json.dumps(send_ack, indent=2), flush=True)
            print("[result] sent:", json.dumps(sent, indent=2), flush=True)
            print("[result] message:", json.dumps(message, indent=2), flush=True)
            print(
                f"[timing] send_ack_wait={send_ack_elapsed:.3f}s "
                f"sent_wait={sent_elapsed:.3f}s "
                f"recipient_wait={recipient_elapsed:.3f}s "
                f"total={time.perf_counter() - send_started:.3f}s",
                flush=True,
            )


if __name__ == "__main__":
    asyncio.run(main())
