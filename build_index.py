
import asyncio
import sqlite3
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import PeerChannel

# Reuse credentials from your existing connection script.
import os
from dotenv import load_dotenv

load_dotenv()

_api_id = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

if not _api_id or not API_HASH:
    raise RuntimeError(
        "Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in .env"
    )

API_ID = int(_api_id)
CHANNEL_ID = 3860912482
DB_PATH = Path(__file__).with_name("skvault.db")


async def main():
    connection = sqlite3.connect(DB_PATH)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS files (
            message_id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT,
            mime_type TEXT,
            size_bytes INTEGER,
            message_date TEXT,
            caption TEXT
        )
    """)

    client = TelegramClient("skvault_session", API_ID, API_HASH)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            print("Session expired. Run check_channel.py to sign in again.")
            return

        channel = await client.get_entity(PeerChannel(CHANNEL_ID))

        count = 0

        async for message in client.iter_messages(channel):
            if not message.media:
                continue

            file = message.file

            if file:
                filename = file.name or f"telegram_{message.id}"
                extension = file.ext or ""
                mime_type = file.mime_type or ""
                size = file.size or 0
            else:
                filename = f"telegram_{message.id}"
                extension = ""
                mime_type = ""
                size = 0

            connection.execute("""
                INSERT OR REPLACE INTO files
                (message_id, filename, file_type, mime_type,
                 size_bytes, message_date, caption)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                filename,
                extension,
                mime_type,
                size,
                message.date.isoformat() if message.date else "",
                message.message or ""
            ))

            count += 1

            if count % 100 == 0:
                connection.commit()
                print(f"Indexed {count} files...")

        connection.commit()

        print("\nIndexing complete!")
        print(f"Media messages indexed: {count}")
        print(f"Database: {DB_PATH}")
        print("Original media downloaded: 0")

    finally:
        await client.disconnect()
        connection.close()


if __name__ == "__main__":
    asyncio.run(main())
