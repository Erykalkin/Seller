import asyncio
from pyrogram import Client
from decouple import config

api_id = config("API_ID", cast=int)
api_hash = config("API_HASH")
session_name = "chat_parser"

chat_username = "your_chat_username_or_id"

async def main():
    async with Client(session_name, api_id=api_id, api_hash=api_hash) as app:
        chat = await app.get_chat(chat_username)
        print(f"📌 Название чата: {chat.title}")
        print(f"👥 Участников: {chat.members_count}")

        print("\n📄 Список участников:")
        async for member in app.get_chat_members(chat_username):
            user = member.user
            print(f"- {user.first_name} @{user.username} (ID: {user.id})")


if __name__ == "__main__":
    asyncio.run(main())