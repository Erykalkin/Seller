import os
import asyncio
from pyrogram import idle
from bot import bot, periodic_greeting, group_parser

os.environ["http_proxy"] = os.getenv("HTTP_PROXY", "socks5h://127.0.0.1:1082")
os.environ["https_proxy"] = os.getenv("HTTPS_PROXY", "socks5h://127.0.0.1:1082")

async def main():
    await bot.start()
    print("БОТ ЗАПУЩЕН")
    asyncio.create_task(group_parser())
    asyncio.create_task(periodic_greeting())
    await idle()

if __name__ == "__main__":
    bot.run(main())