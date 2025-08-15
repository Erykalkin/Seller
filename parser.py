import asyncio
from pyrogram import Client
from pyrogram.types import Message
from decouple import config
from collections import defaultdict
from database import save_user_data  # твоя функция для записи в таблицу
from gpt import analyze_user_messages  # GPT-вызов (см. ниже)

bot = Client(
    name=config('LOGIN'),
    api_id=config('API_ID'),
    api_hash=config('API_HASH'),
    phone_number=config('PHONE')
)

GROUPS = config("GROUPS", cast=lambda v: v.split(","), default=[])

async def group_parser():
    user_messages = defaultdict(list)

    for group in GROUPS:
        print(f"[PARSER] Читаю сообщения из {group}")
        async for msg in bot.get_chat_history(group, limit=500):  # можно увеличить лимит
            if not msg.from_user or not msg.text:
                continue
            user_id = msg.from_user.id
            user_messages[user_id].append(msg.text)

    print(f"[PARSER] Собрано {len(user_messages)} пользователей")

    # Обработка GPT
    for user_id, msgs in user_messages.items():
        combined_text = "\n".join(msgs)
        try:
            gpt_result = analyze_user_messages(combined_text)

            save_user_data(
                user_id=user_id,
                target=gpt_result["target"],
                info=gpt_result["info"],
                messages=combined_text
            )
            print(f"[OK] {user_id} сохранён")
        except Exception as e:
            print(f"[ERROR] {user_id}: {e}")


# 🔹 GPT-анализ сообщений
def analyze_user_messages(messages: str) -> dict:
    """
    Отправляет текст в GPT и возвращает словарь:
    {
        "target": 0/1,
        "info": "...",
        "messages": "..."
    }
    """
    prompt = f"""
Ты анализируешь переписку пользователя из разных чатов.
Сообщения:
{messages}

1. target — заинтересован ли человек в нашей теме (0 или 1).
2. info — кратко опиши, о чём пишет пользователь.
Ответь в JSON формате: {{"target": int, "info": str}}
"""
    response = get_assistant_response_(prompt)  # твой GPT вызов
    return {
        "target": response["target"],
        "info": response["info"],
        "messages": messages
    }