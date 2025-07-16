import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from decouple import config

bot = Client(
    name=config('LOGIN'),
    api_id=config('API_ID'),
    api_hash=config('API_HASH'),
    phone_number=config('PHONE')
)

# Приветствие
async def greet_user(id='@abracadabra12331'):
    await asyncio.sleep(2)
    try:
        await bot.send_message(id, "Привет")
        print(f"Привет отправлен {id}")
    except Exception as e:
        print(f"Ошибка при отправке приветствия: {e}")

# Обработчик входящих сообщений
@bot.on_message(filters.text)
async def handle_message(client: Client, message: Message):
    await client.send_chat_action(message.chat.id, ChatAction.TYPING)
    await asyncio.sleep(1.5)  # Имитируем набор текста
    await message.reply(f"Повторяю без цитаты: {message.text}")
    await message.reply(f"Повторяю с цитатой: {message.text}", quote=True)

# Запуск бота
async def main():
    await bot.start()
    await greet_user()
    await idle()
    await bot.stop()

bot.run(main())
