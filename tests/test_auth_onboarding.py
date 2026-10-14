from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.products import product_domain
from app.models.store import Store
from app.models.user import User
from app.models.wallet import UserWallet
from app.service.auth_service import AuthService
from app.service.order_srevice import OrderService


@pytest.mark.asyncio
async def test_clear_otp_only_mutates_otp_fields() -> None:
    user = User(otp="123456", otp_time=datetime(2026, 10, 14, tzinfo=UTC))

    user.clear_otp()

    assert user.otp is None
    assert user.otp_time is None


@pytest.mark.asyncio
async def test_registration_batches_wallet_and_otp_persistence(monkeypatch) -> None:
    user_id = uuid4()
    session = SimpleNamespace(
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
    )

    monkeypatch.setattr(User, "get_by_unique", AsyncMock(return_value=None))
    monkeypatch.setattr(User, "to_dict", lambda self: {"id": str(self.id)})
    monkeypatch.setattr(
        "app.service.auth_service.generate_login_verification_email",
        lambda username, otp: SimpleNamespace(
            subject=f"Verification for {username}",
            html_content=f"Verification code: {otp}",
        ),
    )
    monkeypatch.setattr(
        "app.service.auth_service.response_builder",
        lambda **kwargs: kwargs,
    )

    await AuthService().create_user(
        {
            "id": user_id,
            "email": "new-user@example.com",
            "full_name": "New User",
            "username": "newuser",
            "role": "user",
        },
        db=session,
        background_tasks=BackgroundTasks(),
    )

    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    registered_user = session.add.call_args_list[0].args[0]
    assert isinstance(registered_user, User)
    assert registered_user.id == user_id
    wallet = session.add.call_args_list[1].args[0]
    assert isinstance(wallet, UserWallet)
    assert wallet.user_id == user_id
    assert registered_user.otp is not None


@pytest.mark.asyncio
async def test_auth_user_query_prevents_eager_and_lazy_relationship_loads() -> None:
    user = User(id=uuid4(), email="user@example.com", username="user")
    result = SimpleNamespace(scalar_one_or_none=lambda: user)

    class SessionStub:
        async def execute(self, statement):
            self.statement = statement
            return result

    db = SessionStub()

    found_user = await User.get_for_auth(str(user.id), db=cast(AsyncSession, db))

    assert found_user is user
    relationship_loader = db.statement._with_options[0]
    assert relationship_loader.strategy == (("lazy", "raise"),)
    assert set(db.statement.columns_clause_froms) == {User.__table__}

    found_by_email = await User.get_by_unique(
        db=cast(AsyncSession, db), email="user@example.com"
    )
    assert found_by_email is user
    assert db.statement._with_options[0].strategy == (("lazy", "raise"),)
    assert set(db.statement.columns_clause_froms) == {User.__table__}


@pytest.mark.asyncio
async def test_cart_product_ids_query_selects_only_product_ids() -> None:
    user_id = uuid4()
    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: ["product-123"])
    )

    class SessionStub:
        async def execute(self, statement):
            self.statement = statement
            return result

    db = SessionStub()

    product_ids = await Cart.get_product_ids_for_user(
        user_id, db=cast(AsyncSession, db)
    )

    assert product_ids == ["product-123"]
    assert db.statement.selected_columns.keys() == ["product_id"]
    assert set(db.statement.columns_clause_froms) == {Cart.__table__}


@pytest.mark.asyncio
async def test_cart_shipping_info_queries_carts_without_user_relationship(
    monkeypatch,
) -> None:
    user = User(id=uuid4(), email="user@example.com", username="user")
    store_id = uuid4()
    db = cast(AsyncSession, object())
    cart_products = AsyncMock(return_value=["product-123"])
    monkeypatch.setattr(Cart, "get_product_ids_for_user", cart_products)
    monkeypatch.setattr(
        product_domain,
        "get_products_by_ids",
        AsyncMock(return_value=[SimpleNamespace(store_id=store_id)]),
    )
    monkeypatch.setattr(
        Store,
        "get_store_by_ids",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=store_id,
                    name="Store",
                    shipment_info=[],
                )
            ]
        ),
    )

    await OrderService().get_cart_shipping_info(user, db=db)

    cart_products.assert_awaited_once_with(user.id, db)
    product_domain.get_products_by_ids.assert_awaited_once_with(["product-123"])
