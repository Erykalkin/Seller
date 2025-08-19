import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pyrogram.raw import functions, types
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
    phone_number='+79936321517'
)

with open("config.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

BUFFER_TIME = float(settings.get("BUFFER_TIME", 1.0))
DELAY = float(settings.get("DELAY", 1.0))
TYPING_DELAY = float(settings.get("TYPING_DELAY", 0.1))
INACTIVITY_TIMEOUT = int(settings.get("INACTIVITY_TIMEOUT", 1000))
GREET_PERIOD = int(settings.get("GREET_PERIOD", 1000))
UPDATE_BD_PERIOD = int(settings.get("UPDATE_BD_PERIOD", 1000))
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
    global BUFFER_TIME, DELAY, TYPING_DELAY, INACTIVITY_TIMEOUT, GREET_PERIOD, UPDATE_BD_PERIOD, TZ, MORNING, NIGHT
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    BUFFER_TIME = float(config.get("BUFFER_TIME", 1.0))
    DELAY = float(config.get("DELAY", 1.0))
    TYPING_DELAY = float(config.get("TYPING_DELAY", 0.1))
    INACTIVITY_TIMEOUT = int(config.get("INACTIVITY_TIMEOUT", 1000))
    GREET_PERIOD = int(config.get("GREET_PERIOD", 1000))
    UPDATE_BD_PERIOD = int(settings.get("UPDATE_BD_PERIOD", 1000))
    TZ = pytz.timezone(config.get("TIMEZONE", "Europe/Moscow"))
    MORNING = int(config.get("MORNING", 0))
    NIGHT = int(config.get("NIGHT", 24))


async def group_parser():
    while not stop_group_parser.is_set():
        users = get_target_users_with_info()
        print(f"Найдено {len(users)} новых пользователей")
        for user_id, access_hash, info in users:
            await add_user(bot, user_id, access_hash, info=info)
        await asyncio.sleep(UPDATE_BD_PERIOD)


# Приветствие
async def greet_new_users():
    users_to_greet = get_users_without_contact()

    if not users_to_greet:
        return

    user_id, access_hash = random.choice(users_to_greet)

    try:
        user = await connect_user(bot, user_id, access_hash)
        await handle_assistant_response(user, f"CLIENT_INFO: {get_user_param(user_id, 'info')}", first=True)
        update_user_param(user_id, "contact", 1)
        print(f"Привет отправлен {user.username}")
    except Exception as e:
        print(f"Ошибка при отправке user_id = {user_id}: {e}")


async def periodic_greeting():
    while not stop_greeter.is_set():
        now = datetime.datetime.now(TZ)
        if MORNING <= now.hour < NIGHT:
            await greet_new_users()
        await asyncio.sleep(GREET_PERIOD)


async def inactivity_push(user_id):
    try:
        await asyncio.sleep(INACTIVITY_TIMEOUT)
        user = await connect_user(bot, user_id)
        await handle_assistant_response(user, "SYSTEM: Клиент долго не отвечает, напиши ему еще раз", wait_after=False)
    except asyncio.CancelledError:
        pass
    finally:
        inactivity_tasks.pop(user_id, None)


def reset_inactivity_timer(user_id):
    if user_id in inactivity_tasks:
        inactivity_tasks[user_id].cancel()
        del inactivity_tasks[user_id]
    inactivity_tasks[user_id] = asyncio.create_task(inactivity_push(user_id))


# Обработчик входящих сообщений
@bot.on_message(filters.private, filters.text)
async def handle_message(bot: Client, message: Message):
    user = message.from_user

    if user is None or user.id not in get_ids():
        return  # Неизвестный пользователь
    if get_user_param(user.id, 'banned'):
        return  # Не отвечаем забаненным пользователям

    access_hash = get_user_param(user.id, "access_hash")
    if access_hash is None:
        await connect_user(bot, user.id)
        return  # НЕ отправляем сообщение ассистенту
    
    # Добавляем сообщение в буфер
    message_buffers[user.id].append(f"[MESSAGE_ID: {message.id}]\n" + message.text)
    last_message_times[user.id] = time.time()

    # Если уже есть задача — отменяем
    if user.id in user_tasks:
        user_tasks[user.id].cancel()

    # Создаём новую задачу
    user_tasks[user.id] = asyncio.create_task(handle_user_buffer(user))


# Отправка сообщения
async def send_message(user, text: str = "", reply: int = None, first: bool = False):
    # Если есть доступ к access_hash, используем raw API
    if first and getattr(user, "access_hash", None):
        input_user = types.InputUser(user_id=user.id, access_hash=user.access_hash)
        try:
            await bot.invoke(functions.messages.SendMessage(peer=input_user, message=text, random_id=bot.rnd_id()))
            return True
        except Exception as e:
            print(f"Ошибка при отправке через raw API: {e}")
    # Если access_hash нет, используем обычный send_message
    else:
        try:
            await bot.send_message(chat_id=user.id, text=text, reply_to_message_id=reply)
            return True
        except Exception as e:
            print(f"Ошибка при отправке по user_id без hash: {e}")

    print("Не удалось отправить сообщение — недостаточно данных.")
    return False


# Обработчик ответа ассистента
async def handle_assistant_response(user, message, wait_after=True, first=False):
    loop = asyncio.get_event_loop()
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
        await send_message(user, answer, reply, first)
        # await bot.send_message(me.id, answer, reply_to_message_id=reply if reply else None)

    if send_pdf:
        file_path = f"data/catalog.pdf"
        await bot.send_document(user.id, document=file_path)

    if wait and wait_after:
        reset_inactivity_timer(user.id)


# Обработчик буфера сообщений
async def handle_user_buffer(user):
    typing_active = True

    async def typing_loop():
        while typing_active:
            await bot.send_chat_action(user.id, ChatAction.TYPING)
            await asyncio.sleep(5)

    try:
        # Ожидание нескольких сообщений подряд
        while True:
            await asyncio.sleep(1)
            elapsed = time.time() - last_message_times[user.id]
            if elapsed >= BUFFER_TIME:
                break
        await bot.read_chat_history(user.id)

        combined_input = '\n==========\n'.join(message_buffers[user.id])
        message_buffers[user.id].clear()

        # Ждём ещё немного рандомно - в сети
        await asyncio.sleep(random.randint(0, DELAY))

        typing_task = asyncio.create_task(typing_loop())

        await handle_assistant_response(user, combined_input)

    except asyncio.CancelledError:
        pass  # Если задача отменена — просто выходим

    finally:
        typing_active = False
        await typing_task
