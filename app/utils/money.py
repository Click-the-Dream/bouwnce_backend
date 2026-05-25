from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def naira_to_kobo(amount_naira: float) -> int:
    return int(
        (Decimal(str(amount_naira)) * Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )

