import asyncio
from pyrogram import idle
from bot import bot, periodic_greeting

async def main():
    await bot.start()
    print("БОТ ЗАПУЩЕН")
    asyncio.create_task(periodic_greeting(bot))
    await idle()

if __name__ == "__main__":
    bot.run(main())