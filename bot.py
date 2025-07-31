import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from decouple import config
from collections import defaultdict
import random
import time
import json
from gpt import*
from database import*

bot = Client(
    name=config('LOGIN'),
    api_id=config('API_ID'),
    api_hash=config('API_HASH'),
    phone_number=config('PHONE')
)

AUTHORIZED_USERS = get_users()
USERS_TO_GREET = get_users_without_contact()
print(AUTHORIZED_USERS)

# Приветствие
async def greet_new_users(bot: Client):
    async def greet(user_id):
        user = await bot.get_users(user_id)
        thread_id = get_or_create_thread(user_id)
        username = await get_username_by_id(bot, user_id)
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: get_assistant_response(
                    f"CLIENT_INFO: {get_user_param(user_id, 'info')}",
                    thread_id
                )
            )
            answer = json.loads(response)['answer']
            await bot.send_message(user_id, answer)

            update_user_param(user_id, "contact", 1)
            update_user_param(user_id, 'thread_id', thread_id)

            print(f"✅ Привет отправлен {username}")
        except Exception as e:
            print(f"❌ Ошибка при отправке {username}: {e}")

    await asyncio.gather(*[greet(user) for user in USERS_TO_GREET])

# Буфер сообщений и временные метки
user_tasks = {}  # user_id -> asyncio.Task
message_buffers = defaultdict(list)
last_message_times = {}

BUFFER_TIME = 1  # время ожидания перед ответом
DELAY_MIN = 0
DELAY_MAX = 1
TYPING_DELAY = 0.1

# Обработчик входящих сообщений
@bot.on_message(filters.text)
async def handle_message(client: Client, message: Message):
    if message.from_user is None or message.from_user.id not in AUTHORIZED_USERS:
        return  # Неизвестный пользователь
    if message.from_user.id == client.me.id:
        return  # Не отвечаем самому себе
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = get_or_create_thread(user_id)

    # Добавляем сообщение в буфер
    message_buffers[user_id].append(f"[MESSAGE_ID: {message.id}]\n" + message.text)
    last_message_times[user_id] = time.time()

    # Если уже есть задача — отменяем
    if user_id in user_tasks:
        user_tasks[user_id].cancel()

    # Создаём новую задачу
    user_tasks[user_id] = asyncio.create_task(handle_user_buffer(client, chat_id, user_id, thread_id))


async def handle_user_buffer(client, chat_id, user_id, thread_id):
    try:
        # Ожидание нескольких сообщений подряд
        print(1)
        while True:
            await asyncio.sleep(1)
            elapsed = time.time() - last_message_times[user_id]
            if elapsed >= BUFFER_TIME:
                break
        await client.read_chat_history(chat_id)
        print(2)

        # Ждём ещё немного рандомно - в сети
        await asyncio.sleep(random.randint(DELAY_MIN, DELAY_MAX))
        print(3)

        # Печатает...
        typing_active = True

        async def typing_loop():
            while typing_active:
                await client.send_chat_action(chat_id, ChatAction.TYPING)
                await asyncio.sleep(5)

        task = asyncio.create_task(typing_loop())

        combined_input = '\n==========\n'.join(message_buffers[user_id])
        message_buffers[user_id].clear()

        loop = asyncio.get_event_loop()
        
        try:
            print(4)
            response = await loop.run_in_executor(None, lambda: get_assistant_response(combined_input, thread_id, user_id))
            reply = 0

            try:
                response = json.loads(response)
                answer = response['answer']
                reply = response['reply']
            except json.JSONDecodeError:
                answer = response

            print(5)
            delay_after_response = min(len(answer) * TYPING_DELAY, 10.0)
            await asyncio.sleep(delay_after_response)

            await client.send_message(chat_id, answer, reply_to_message_id=reply if reply else None)

        finally:
            typing_active = False
            await task
    except asyncio.CancelledError:
        pass  # Если задача отменена — просто выходим

# Запуск бота
async def main():
    await bot.start()
    await greet_new_users(bot)
    await idle()
    await bot.stop()

bot.run(main())
