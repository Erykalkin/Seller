import os
import asyncio
from pyrogram import idle
from bot import bot, periodic_greeting, group_parser

async def main():
    await bot.start()
    print("БОТ ЗАПУЩЕН")
    asyncio.create_task(group_parser())
    asyncio.create_task(periodic_greeting())
    await idle()

if __name__ == "__main__":
    bot.run(main())
