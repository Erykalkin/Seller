import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from decouple import config
from collections import defaultdict
import datetime
import random
import time
import pytz
import json
from gpt import*
from database import*
from utils import*

bot = Client(
    name=config('LOGIN'),
    api_id=config('API_ID'),
    api_hash=config('API_HASH'),
    phone_number=config('PHONE')
)

with open("config.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

BUFFER_TIME = float(settings.get("BUFFER_TIME", 1.0))
DELAY = float(settings.get("DELAY", 1.0))
TYPING_DELAY = float(settings.get("TYPING_DELAY", 0.1))
INACTIVITY_TIMEOUT = int(settings.get("INACTIVITY_TIMEOUT", 1000))
GREET_PERIOD = int(settings.get("GREET_PERIOD", 1000))
TZ = pytz.timezone(settings.get("TIMEZONE", "Europe/Moscow"))
MORNING = int(settings.get("MORNING", 9))
NIGHT = int(settings.get("NIGHT", 21))

stop_group_parser = asyncio.Event()
stop_greeter = asyncio.Event()

# Буфер сообщений и временные метки
user_tasks = {}  # user_id -> asyncio.Task
message_buffers = defaultdict(list)
last_message_times = {}
inactivity_tasks = {}

# Команды для управления
def stop_parser():
    stop_group_parser.set()

def start_parser():
    stop_group_parser.clear()
    asyncio.create_task(group_parser())

def stop_greeting():
    stop_greeter.set()

def start_greeting():
    stop_greeter.clear()
    asyncio.create_task(periodic_greeting())

def update_settings():
    global BUFFER_TIME, DELAY, TYPING_DELAY, INACTIVITY_TIMEOUT, GREET_PERIOD, TZ, MORNING, NIGHT
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    BUFFER_TIME = float(config.get("BUFFER_TIME", 1.0))
    DELAY = float(config.get("DELAY", 1.0))
    TYPING_DELAY = float(config.get("TYPING_DELAY", 0.1))
    INACTIVITY_TIMEOUT = int(config.get("INACTIVITY_TIMEOUT", 1000))
    GREET_PERIOD = int(config.get("GREET_PERIOD", 1000))
    TZ = pytz.timezone(config.get("TIMEZONE", "Europe/Moscow"))
    MORNING = int(settings.get("MORNING", 0))
    NIGHT = int(settings.get("NIGHT", 24))


async def group_parser():
    while not stop_group_parser.is_set():
        print("[GROUP PARSER] Ищу новых пользователей в группах...")
        # логика парсинга и добавления в БД
        await asyncio.sleep(10)  # пауза между циклами


# Приветствие
async def greet_new_users(bot: Client):
    users_to_greet = get_users_without_contact()
    print(users_to_greet)

    if not users_to_greet:
        return

    user_id = users_to_greet[0]  # Берём первого

    try:
        user = await bot.get_users(user_id)
        await handle_assistant_response(bot, user, f"CLIENT_INFO: {get_user_param(user_id, 'info')}")
        update_user_param(user_id, "contact", 1)
        print(f"Привет отправлен {user.username}")
    except Exception as e:
        print(f"Ошибка при отправке: {e}")


async def periodic_greeting(bot: Client):
    while not stop_greeter.is_set():
        now = datetime.datetime.now(TZ)
        if MORNING <= now.hour < NIGHT:
            await greet_new_users(bot)
        await asyncio.sleep(GREET_PERIOD)


async def inactivity_push(user_id, bot):
    try:
        await asyncio.sleep(INACTIVITY_TIMEOUT)
        user = await bot.get_users(user_id)
        await handle_assistant_response(bot, user, "SYSTEM: Клиент долго не отвечает, напиши ему еще раз", wait_after=False)
    except asyncio.CancelledError:
        pass
    finally:
        inactivity_tasks.pop(user_id, None)


def reset_inactivity_timer(user_id, bot):
    if user_id in inactivity_tasks:
        inactivity_tasks[user_id].cancel()
        del inactivity_tasks[user_id]
    inactivity_tasks[user_id] = asyncio.create_task(inactivity_push(user_id, bot))


# Обработчик входящих сообщений
@bot.on_message(filters.private, filters.text)
async def handle_message(client: Client, message: Message):
    user = message.from_user

    if user is None or user.id not in get_users():
        return  # Неизвестный пользователь
    if get_user_param(user.id, 'banned'):
        return  # Не отвечаем забаненным пользователям
    
    # Добавляем сообщение в буфер
    message_buffers[user.id].append(f"[MESSAGE_ID: {message.id}]\n" + message.text)
    last_message_times[user.id] = time.time()

    # Если уже есть задача — отменяем
    if user.id in user_tasks:
        user_tasks[user.id].cancel()

    # Создаём новую задачу
    user_tasks[user.id] = asyncio.create_task(handle_user_buffer(client, user))


# Обработчик ответа ассистента
async def handle_assistant_response(client, user, message, wait_after=True):
    loop = asyncio.get_event_loop()

    typing_active = True
    async def typing_loop():
        while typing_active:
            await client.send_chat_action(user.id, ChatAction.TYPING)
            await asyncio.sleep(5)

    typing_task = asyncio.create_task(typing_loop())

    try:
        response = await loop.run_in_executor(None, lambda: get_assistant_response_(message, user))

        response = json.loads(response)
        answer = response['answer']
        send_msg = response['send'] 
        send_pdf = response['file']
        wait = response['wait']
        reply = response['reply']

        delay_after_response = min(len(answer) * TYPING_DELAY, 10.0)
        await asyncio.sleep(delay_after_response)

        if send_msg:
            await client.send_message(user.id, answer, reply_to_message_id=reply if reply else None)

        if send_pdf:
            file_path = f"data/catalog.pdf"
            await client.send_document(user.id, document=file_path)

        if wait and wait_after:
            reset_inactivity_timer(user.id, client)

    finally:
        typing_active = False
        await typing_task


# Обработчик буфера сообщений
async def handle_user_buffer(client, user):
    try:
        # Ожидание нескольких сообщений подряд
        while True:
            await asyncio.sleep(1)
            elapsed = time.time() - last_message_times[user.id]
            if elapsed >= BUFFER_TIME:
                break
        await client.read_chat_history(user.id)

        # Ждём ещё немного рандомно - в сети
        await asyncio.sleep(random.randint(0, DELAY))

        combined_input = '\n==========\n'.join(message_buffers[user.id])
        message_buffers[user.id].clear()

        await handle_assistant_response(client, user, combined_input)

    except asyncio.CancelledError:
        pass  # Если задача отменена — просто выходим
