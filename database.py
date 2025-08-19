import sqlite3
from tabulate import tabulate
import os
from pyrogram import Client
from pyrogram.errors import PeerIdInvalid
from pyrogram.raw import functions, types
from decouple import config

DB_PATH = R"data/users.db"


async def connect_user(bot: Client, user_id: int, access_hash: int = None):
    """
    Возвращает pyrogram.types.User при наличии доступа.
    Возвращает pyrogram.raw.types.User при отсутствии доступа, если есть access_hash.
    """
    access_hash = await get_access_hash(bot, user_id)

    try:
        # Пробуем high-level API
        user = await bot.get_users(user_id)
        return user

    except PeerIdInvalid:
        # Если стандартный способ не прошёл, используем raw API
        if access_hash is None:
            print(f"connect_user: Невозможно получить пользователя {user_id}, не найден access_hash")
            return None
            
        input_peer = await bot.resolve_peer(user_id)
        result = await bot.invoke(functions.users.GetUsers(id=[input_peer]))
        if result:
            return result[0]
        return None


async def get_access_hash(bot: Client, user_id: int):
    """
    Возвращает access_hash из БД, если он там есть.
    Иначе — получает его через resolve_peer после того, как пользователь написал боту.
    """

    access_hash = get_user_param(user_id, "access_hash")
    
    if access_hash is None:
        try:
            input_peer = await bot.resolve_peer(user_id)
            result = await bot.invoke(functions.users.GetUsers(id=[input_peer]))
            if result:
                raw_user = result[0]
                access_hash = raw_user.access_hash
                update_user_param(user_id, "access_hash", access_hash)
        except Exception as e:
            print(f"get_access_hash: Не удалось получить access_hash для {user_id}: {e}")

    return access_hash


async def get_username_by_id(bot: Client, user_id: int, access_hash: int = None):
    try:
        user = await connect_user(bot, user_id, access_hash)
        if user.username:
            return user.username
        elif user.phone_number:
            return f"+{user.phone_number}"
        else:
            return f"User_{user.id}"
    except Exception as e:
        return str(user_id)
 
    
async def get_id_by_username(bot: Client, username: str):
    try:
        user = await bot.get_users(username)
        if user.id > 100:
            return user.id
        return None
    except Exception as e:
        return None
    

async def get_phone_by_id(bot: Client, user_id: int, access_hash: int = None):
    try:
        user = await connect_user(bot, user_id, access_hash)
        return f"+{user.phone_number}" if getattr(user, "phone_number", None) else \
               f"+{user.phone}" if getattr(user, "phone", None) else None
    except Exception as e:
        return None


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            access_hash INTEGER,
            username TEXT,
            telephone TEXT,
            name TEXT,
            contact BOOLEAN,
            banned BOOLEAN,
            crm BOOLEAN,
            thread_id TEXT,
            info TEXT,
            summary TEXT
        )
    """)
    conn.commit()
    conn.close()


def delete_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"База данных '{DB_PATH}' удалена.")
    else:
        print(f"База данных '{DB_PATH}' не найдена.")


async def add_user(bot: Client, user_id: int, access_hash: int, info=''):
    username = await get_username_by_id(bot, user_id, access_hash)
    telephone = await get_phone_by_id(bot, user_id, access_hash)
    info += f"\n\nTG TELEPHONE NUBMER: {telephone}"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, access_hash, username, telephone, name, contact, banned, crm, thread_id, info, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, access_hash, username, telephone, '', False, False, False, '', info, ''))
    conn.commit()
    conn.close()


async def add_user_by_name(bot: Client, username: str, info=''):
    user_id = await get_id_by_username(bot, username)
    if user_id is None:
        return
    telephone = await get_phone_by_id(bot, user_id)
    info += f"\n\nTG TELEPHONE NUBMER: {telephone}"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, access_hash, username, telephone, name, contact, banned, crm, thread_id, info, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, None, username, telephone, '', False, False, False, '', info, ''))
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def delete_user_by_name(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def update_user_param(user_id: int, column: str, value):
    """Обновляет значение определённого параметра у user_id"""
    allowed_columns = {"access_hash", "username", "telephone", "name", "contact", "banned", "crm", "thread_id", "info", "summary"}
    
    if column not in allowed_columns:
        raise ValueError(f"Недопустимое имя колонки: {column}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {column} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()


def update_user_param_by_name(username: str, column: str, value):
    """Обновляет значение определённого параметра у username"""
    allowed_columns = {"telephone", "name", "contact", "banned", "crm", "thread_id", "info", "summary"}
    
    if column not in allowed_columns:
        raise ValueError(f"Недопустимое имя колонки: {column}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {column} = ? WHERE username = ?", (value, username))
    conn.commit()
    conn.close()


def get_users():
    """Вернёт список всех (user_id, access_hash)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, access_hash FROM users")
    users = [(row[0], row[1]) for row in cursor.fetchall()]
    conn.close()
    return users


def get_ids():
    """Вернёт список всех user_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def get_users_without_contact():
    """Вернёт список (user_id, access_hash), у которых contact = False"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, access_hash FROM users WHERE contact = 0")
    users = [(row[0], row[1]) for row in cursor.fetchall()]
    conn.close()
    return users


def get_user_param(user_id: int, column: str):
    """Возвращает значение определённого параметра для заданного user_id"""
    allowed_columns = {"access_hash", "username", "telephone", "name", "contact", "banned", "crm", "thread_id", "info", "summary"}
    
    if column not in allowed_columns:
        raise ValueError(f"Недопустимое имя колонки: {column}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT {column} FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    else:
        return None


def get_user(user_id):
    """Вернёт информацию о user_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_all_users(sorted_by_contact=False):
    """Вернёт информацию о всех usernames"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if sorted_by_contact:
        cursor.execute("SELECT * FROM users ORDER BY contact DESC, username ASC")
    else:
        cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    conn.close
    return rows


def show_users(sorted_by_contact=False):
    rows = get_all_users(sorted_by_contact)
    headers = ["Id", "Access Hash", "Username", "Telephone", "Name", "Contact", "Banned", "Added to CRM", "Thread ID", "Info", "Summary"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))


# Связь с БД парсера
def get_target_users_with_info():
    conn = sqlite3.connect("/home/appuser/parser/data/users.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, access_hash, info
        FROM users
        WHERE target = 1
          AND info IS NOT NULL
          AND info != ''
    """)
    rows = cur.fetchall()
    conn.close()
    return rows