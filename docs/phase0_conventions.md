# Phase 0 — Discovery Notes: Existing Conventions

Scope: everything Phases 1–4 (event ticketing payments) must reuse, with zero
regression to the product-checkout flow. Verified by reading the code, not from
memory. Line references approximate; use symbol names when navigating.

## 1. The "transactions" model is `Payment` (`app/models/payment.py`)

There is no `transactions` table. The money-mover is:

| Column                | Type                                                                                                                              | Notes                                                                                                  |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `user_id`             | UUID FK → `users.id` (CASCADE)                                                                                                    | not null                                                                                               |
| `amount`              | Integer                                                                                                                           | **naira units** despite Paystack being kobo; kobo conversion happens at the edge via `naira_to_kobo()` |
| `currency`            | String, default `"NGN"`                                                                                                           |                                                                                                        |
| `provider`            | String, server_default `"paystack"`                                                                                               |                                                                                                        |
| `provider_payment_id` | String, not null                                                                                                                  | **the Paystack reference**, never a polymorphic ID                                                     |
| `payment_url`         | String, not null                                                                                                                  | authorization URL                                                                                      |
| `status`              | PG enum `payment_status_enum`: successful / cancelled / initiated / declined / refunded / abandoned / failed, default `initiated` |                                                                                                        |
| (+ `BaseModel`)       | id UUID, created_at, updated_at, deleted_at, is_deleted                                                                           | soft delete convention                                                                                 |

Polymorphic linking: **does not exist**. linkage is one-to-one per flow:

- Products: `Order.payment_id → payments.id`; `Order.reference_token` (unique) holds the Paystack reference; `Order.idempotent_key` (unique) drives checkout idempotency.
- Events: `UserEventAttendance.payment_reference` (unique, indexed) + `payment_url` (migration `d4e5f6a7b8c9`, additive nullable columns).

**Implication for Phase 1 (schema):** additive nullable columns / new tables only,
matching migration style: `revision` string id, `down_revision` chain,
`Alembic/versions/`, plain `sa.Column` adds with matching `downgrade()`.

## 2. Product checkout path (do not touch)

`POST /cart/checkout` (`app/api/v1/cart_router.py:104`, auth `CurrentActiveUser`)
→ `OrderService.checkout()` (`app/service/order_srevice.py`):

1. **Idempotency**: header `Idempotent-key` (400 if missing) → `Order.get_by_idempotent_key` → short-circuit return stored `payment_url`/`reference_token`/`amount_kobo`.
2. Load carts → `Order.check_cart_availability` (Redis-backed stock) → `reserve_products` → group by store → validate per-store `shipment_id` belongs to store → compute total (naira float) → `naira_to_kobo`.
3. `paystack_service.create_payment_intent({email, amount(kobo)})` — **sync SDK call** (`paystackapi`), returns `(authorization_url, reference)`. Wrap in try/except → `InternalServerErrorException`, release reservations on failure.
4. `Payment.create(...)` then `Order.create(...)` (payment first, then order carrying `reference_token` + `idempotent_key`).
5. Response: `response_builder(...)` envelope, `data = {payment_url, reference_token, amount_kobo, available_products, unavailable_products}`.

Input validation: Pydantic schemas (`app/schemas/order.py` — `CheckoutInputSchema`); ranges/types at boundary; existence checks in service.

## 3. Webhook path (shared by products and events — extend, don't fork)

`POST /payment/paystack/webhook` (`app/api/v1/payment.py`) — **public, unauthenticated**; dispatch is a chain:

```
paystack_webhook
  → attendance_service.handle_paystack_webhook(db, redis, request)   # events, returns None if not ours
  → order_service.handle_successful_payment(request, db, redis)      # products fallback
```

Order path: `verify_webhook_signature` (HMAC-SHA512 of raw body vs `x-paystack-signature`, via `paystack_service`; skippable with `PAYSTACK_WEBHOOK_VERIFY_SIGNATURE`) → parse JSON → ignore non-`charge.success` → `queue_paid_order(reference, amount_kobo, event_id=paystack txn id)`:

- lookup `Order.get_by_reference`; **owner check absent by design (webhook is provider-trusted)** — compare `str(order.user_id)` only in user-facing `verify_payment`.
- status gate `["initiated", "abandoned"]` else idempotent no-op ("Order has been processed")
- re-verify amount with Paystack `callback()` (via `asyncio.to_thread`) + `ConflictException("amount mismatch")`
- Redis `SET NX EX 900` dedupe key `order_processing:queued:{reference}` → `process_paid_order.delay(...)` (Celery, retries + DLQ `dlq:order_processor`).

Event path: same signature check → reference lookup on `UserEventAttendance.payment_reference` → if none, `return None` (falls through to order flow) → verify via `callback()` → `dispatch_event(EVENT_ATTENDANCE_PAYMENT_COMPLETED, ...)`.

Consumer (`app/worker/event_system.py`, `EVENT_ATTENDANCE_PAYMENT_COMPLETED`):
`get_by_id_for_update` (row lock) → idempotent guard `payment_status == "successful"` → reference match + `naira_to_kobo(total_amount) == amount_kobo` else `ConflictException` → set `payment_status="successful"`, `attendance_status="confirmed"` → mobile stream event + push notification (both suppress DB notification writes for `event.payment.*`).

## 4. Event model (`app/event_broadcast/models/events.py`)

`OutingEvent` (`outing_events`): `id`, `name`, `desc`, `date` (DateTime), `price`
(Float, default 0.0), `location`, `location_type` (enum physical/virtual/hybrid),
`link`, `banner_url`, `state` (enum `EventState` draft/live), `ticket_info`
(JSONB — **source of truth for per-ticket pricing**, shape `[{ticket_name, price, ticket_description?}]`), `interests` (JSONB), `creator_id` (UUID FK users — this is the owner).

**No capacity / remaining-tickets column exists.** Availability is implied by
state == LIVE. If Phase 2 needs capacity, that's a new additive column/table.

Attendance: `UserEventAttendance` (`user_event_attendance`): user_id, event_id,
`ticket_info` JSONB, `total_amount` (naira float), `total_tickets`, `payment_status` (String "pending"/"successful", **plain string, not enum**), `payment_reference` (unique), `payment_url`, `attendance_status` ("pending_payment"/"confirmed"). One attendance per (user, event) — `check_existing_attendance` raises on duplicate claim. Soft-delete only.

## 5. Auth / session middleware (`app/api/dependencies.py`)

- `CurrentUser` (JWT bearer via `HTTPBearer`, token blacklist in Redis, `type == "access"`), `CurrentActiveUser` (adds `is_active`), `CurrentVendor`, `CurrentAdmin`, `CurrentStore`/`CurrentActiveStore` (vendor + their store).
- **Resource-owner pattern**: fetch resource, then `if str(resource.user_id) != str(current_user.id): raise ForbiddenException` — e.g. `order_service.cancel_order`, `attendance_service.verify_event_payment`. New owner-scoped endpoints must copy this inline check (there is no reusable dependency for it).
- Sessions: `dbSessionDep` (AsyncSession, `get_async_session`), `redisSessionDep`. `redis` is used for dedupe keys and the mobile event stream.

## 6. Infra utilities to reuse (no second client)

- **Paystack**: `app/service/payment/paystack.py` — `PaystackGateWay` (`paystackapi` SDK): `create_payment_intent(data{email, amount_kobo}) -> (url, reference)` (sync), `callback(reference) -> (bool, payload|msg)` (sync), `verify_webhook_signature(request)` (async). Module singleton `paystack_service`. All call sites wrap the sync calls in `asyncio.to_thread` when off the request path.
- **Email**: `app/utils/emails.py` — `send_email(email_to, subject, html_content) -> bool` (env-switched Resend / SMTP / console), `generate_email_content(subject, template_name, context)`, templates in `app/email_templates/` (build/ then src/). Two send styles exist: direct `asyncio.to_thread(send_email, ...)` (newsletter, auth) and Celery `dispatch_event(EMAIL_NOTIFICATION, EmailNotificationEvent(...))` + template (worker paths, e.g. `order_processor`). **For webhook/worker-triggered mail, use the event-system path.**
- **Cloudinary**: `app/utils/cloudinary_utils.py` (`upload_images`, `delete_images`, `delete_folder`, temp-file helpers) and `app/service/upload_service.py` (signed direct-upload params). Already used by products/store/chat; reuse for ticket/badge/QR assets.
- **Money**: `app/utils/money.py` `naira_to_kobo(amount_naira: float) -> int` (Decimal, ROUND_HALF_UP). DB stores naira floats; kobo only at the Paystack boundary and in comparisons.

## 7. Conventions checklist for Phases 1–4

- **Router**: `APIRouter(prefix=..., tags=[...])`, registered in `app/api/v1/__init__.py` (`api_router.include_router(...)`); event routers under `app/event_broadcast/api/v1/` merged via `event_router`. Endpoints: FastAPI `status.HTTP_...`, `response_model=` from schema module, `summary=`, `Query(ge=..., le=...)` for pagination (1–100).
- **Response envelope**: `response_builder(status_code, message, data=..., status="success")` → `{status, status_code, message, data?}`; typed variants subclass `BaseResponse` (`app/utils/responses.py`). Pagination keys (`page`, `page_size`, `total_pages`, `total_<noun>`) are added to the top level of the response dict.
- **Errors**: `app/utils/exception.py` `ApiException` family (BadRequest/UnAuthorized/Forbidden/NotFound/Conflict/Gone/InternalServerError) with `detail = {status_code, status:"error", message, data?}`. Raise, never return error dicts. `raise ... from None` to suppress chains.
- **Validation**: Pydantic v2 `BaseModel` + `Annotated[T, Field(...)]` (`gt`, `ge`, `le`, `min_length`, `description`); boundary = endpoint schema; service re-checks ranges/existence and raises `BadRequestException`/`NotFoundException`. UUID-string checks via `app.utils.helper.is_valid_uuid` (base model also guards `get_by_id`).
- **Services**: `XxxService` class + module-level singleton (`order_service`, `attendance_service`, `paystack_service`). Models carry classmethod query helpers (`get_by_reference`, `get_by_payment_reference`, `get_by_id_for_update`) and return raw scalars; services serialize via `to_dict()` + `_serialize_*` helpers (stringify UUIDs/enums).
- **Async work**: Redis `SET NX EX` for dedupe/idempotency keys (`order_processing:queued:{ref}`, 900s), Celery tasks in `app/worker/tasks/` (registered in `celery_app.include`), beat schedule in `celery_app.conf.beat_schedule` (existing `reconcile-event-payments` every 300s covers pending event + order payments), in-process fan-out via `dispatch_event` + `EventNames` + dataclass payloads.
- **Schema changes**: additive only, nullable or server_default, paired `upgrade()`/`downgrade()`, unique index when the column is a lookup key (see `d4e5f6a7b8c9`).
- **Idempotency requirements** (per ground rules): money endpoints need an idempotency key (header `Idempotent-key` for client-facing checkout; provider reference + status-gate for webhooks) validated at the boundary before any DB/Paystack call.

## 8. Known gaps / risks to carry into design

1. **Amount semantics are inconsistent**: `payments.amount` and `attendance.total_amount` are naira floats, but webhook payloads and dedupe compare in kobo. Any new code must pin its unit explicitly and convert only via `naira_to_kobo`. (Float money is a standing debt; do not extend it to new tables if avoidable.)
2. `event_id` in `queue_paid_order` is the **Paystack transaction id**, not an `outing_events.id` — don't conflate.
3. Webhook handlers return 200 with "awaiting verification" on failed re-verify instead of 5xx; reconcile task (`reconcile-event-payments`) is the recovery net. New flows should behave the same way.
4. `print()` logging appears in checkout paths; follow the newer `logging.getLogger(__name__)` style in worker code for anything new.
5. `attendance.payment_status`/`attendance_status` are plain strings, not enums — match that unless Phase 1 explicitly migrates them (additive constraint says don't).
6. Webhook is unauthenticated and both handlers verify the signature redundantly (attendance first, then order) — harmless but any new handler in the chain must not skip `verify_webhook_signature`.
7. Test suite is light (11 files; `tests/test_web_push.py` asserts beat schedule wiring). New phases should follow that pattern: plain pytest modules under `tests/`, no DB fixtures required for pure-logic assertions.
