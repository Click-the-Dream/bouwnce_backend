from typing import Any

from paystackapi.paystack import Paystack

from app.core.config import settings


class PaystackGateWay:
    def __init__(self):
        self.paystack = Paystack(secret_key=settings.PAYSTACK_API_KEY)

    def create_payment_intent(self, data: dict[str, Any]):
        """Initialize payment with paystack SDK

        amount: Naira for now
        """

        response = self.paystack.transaction.initialize(
            email=data["email"], amount=data["amount"]
        )
        if response["status"]:
            return response["data"]["authorization_url"], response["data"]["reference"]
        else:
            raise Exception(response["message"])

    def webhook(self):
        pass

    def callback(self, reference: str):
        """Verify Payment transaction using paystack SDK"""
        response = self.paystack.transaction.verify(reference)
        if response["status"] and response["data"]["status"] == "success":
            return True, response["data"]
        return False, response["data"]
