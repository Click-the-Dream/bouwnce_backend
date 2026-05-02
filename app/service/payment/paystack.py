import hashlib
import hmac
from typing import Any

from fastapi.requests import Request
from paystackapi.paystack import Paystack

from app.core.config import settings
from app.utils.exception import BadRequestException


class PaystackGateWay:
    def __init__(self):
        self.paystack = Paystack(secret_key=settings.PAYSTACK_API_KEY)

    def create_payment_intent(self, data: dict[str, Any]):
        """Initialize payment with paystack SDK

        amount: Naira for now
        """
        response = self.paystack.transaction.initialize(
            email=data["email"], amount=int(data["amount"])
        )
        if response["status"]:
            return response["data"]["authorization_url"], response["data"]["reference"]
        else:
            raise Exception(response["message"])

    def callback(self, reference: str):
        """Verify Payment transaction using paystack SDK"""
        response = self.paystack.transaction.verify(reference)

        if not response["status"]:
            return False, response["message"]

        if response["data"]["status"] == "success":
            return True, response["data"]

        return False, response["data"]

    async def verify_webhook_signature(self, request: Request):
        """
        verify the request coming to paystack webhook is coming from paystack

        :param request: fastapi request object
        :type request: Request
        :return: True is validation is correct otherwise throw error
        :rtype: Literal[True]
        """

        if not settings.PAYSTACK_WEBHOOK_VERIFY_SIGNATURE:
            return True

        body = await request.body()

        signature = request.headers.get("x-paystack-signature")

        if not signature:
            raise BadRequestException(message="Missing signature")

        computed_hash = hmac.new(
            settings.PAYSTACK_API_KEY.encode("utf-8"), body, hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, signature):
            raise BadRequestException(message="Invalid signature")

        return True


paystack_service = PaystackGateWay()
