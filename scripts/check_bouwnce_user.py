from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from sqlalchemy import func, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.db.postgres_db_conn import get_async_session
from app.models.chat import Conversation, Message
from app.models.user import User


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Bouwnce system user + inbox conversation"
    )
    parser.add_argument(
        "--email",
        default=settings.BOUWNCE_SYSTEM_EMAIL,
        help="Bouwnce system email (default: settings.BOUWNCE_SYSTEM_EMAIL)",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Optional user id to check Bouwnce conversation/message count with",
    )
    parser.add_argument(
        "--user-email",
        default=None,
        help="Optional user email to check Bouwnce conversation/message count with",
    )
    args = parser.parse_args()

    async with get_async_session() as db:
        bouwnce = (
            await db.execute(select(User).where(User.email == str(args.email)))
        ).scalar_one_or_none()

        if bouwnce is None:
            print("BOUWNCE_USER: NOT_FOUND")
            print(f"email={args.email}")
            return

        print("BOUWNCE_USER: FOUND")
        print(f"id={bouwnce.id}")
        print(f"email={bouwnce.email}")
        print(f"username={bouwnce.username}")
        print(f"full_name={bouwnce.full_name}")

        target_user_id = None
        if args.user_email:
            u = (
                await db.execute(select(User).where(User.email == str(args.user_email)))
            ).scalar_one_or_none()
            if u is None:
                print("USER: NOT_FOUND")
                print(f"email={args.user_email}")
                return
            target_user_id = u.id
        elif args.user_id:
            try:
                target_user_id = uuid.UUID(str(args.user_id))
            except Exception:
                # Treat as email for convenience
                u = (
                    await db.execute(
                        select(User).where(User.email == str(args.user_id))
                    )
                ).scalar_one_or_none()
                if u is None:
                    print("USER: NOT_FOUND")
                    print(f"email={args.user_id}")
                    return
                target_user_id = u.id

        if not target_user_id:
            return

        conv = await Conversation.get_between(db, bouwnce.id, target_user_id)
        if conv is None:
            print("CONVERSATION: NOT_FOUND")
            return

        count_stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conv.id)
        )
        msg_count = int((await db.execute(count_stmt)).scalar() or 0)
        print("CONVERSATION: FOUND")
        print(f"conversation_id={conv.id}")
        print(f"messages={msg_count}")


if __name__ == "__main__":
    asyncio.run(main())
