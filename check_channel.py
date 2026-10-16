
import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

_api_id = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

if not _api_id or not API_HASH:
    raise RuntimeError(
        "Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in .env"
    )

API_ID = int(_api_id)

CHANNEL_NAME = "SK VAULT"


async def main():
    async with TelegramClient(
        "skvault_session", API_ID, API_HASH
    ) as client:
        print("\nConnected to Telegram.")

        matches = []
        async for dialog in client.iter_dialogs():
            if CHANNEL_NAME.lower() in dialog.name.lower():
                matches.append(dialog)

        if not matches:
            print("Channel not found in your Telegram dialogs.")
            return

        for dialog in matches:
            entity = dialog.entity
            print(f"\nChannel: {dialog.name}")
            print(f"Channel ID: {entity.id}")

            total = 0
            with_media = 0

            async for message in client.iter_messages(entity):
                total += 1
                if message.media:
                    with_media += 1

                if total % 100 == 0:
                    print(f"Checked {total} messages...")

            print(f"Messages accessible: {total}")
            print(f"Messages containing media: {with_media}")

        print(
            "\nConnection test complete. "
            "No media files were downloaded."
        )


if __name__ == "__main__":
    asyncio.run(main())
