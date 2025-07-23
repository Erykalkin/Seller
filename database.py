import sqlite3
from tabulate import tabulate
import os
from pyrogram import Client
from decouple import config

DB_PATH = "users.db"


async def get_username_by_id(bot: Client, user_id: int):
    try:
        user = await bot.get_users(user_id)
        return user.username
    except Exception as e:
        print(f"❌ Ошибка при получении username: {e}")
        return user_id
    
async def get_id_by_username(bot: Client, username: str):
    try:
        user = await bot.get_users(username)
        print(user.id)
        return user.id
    except Exception as e:
        print(f"❌ Ошибка при получении ID: {e}")
        return None


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            contact BOOLEAN,
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
        print(f"✅ База данных '{DB_PATH}' удалена.")
    else:
        print(f"⚠️ База данных '{DB_PATH}' не найдена.")


async def add_user(bot: Client, user_id: int, contact=False, thread_id='', info='', summary=''):
    username = await get_username_by_id(bot, user_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, username, contact, thread_id, info, summary)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, contact, thread_id, info, summary))
    conn.commit()
    conn.close()


async def add_user_by_name(bot: Client, username: str, contact=False, thread_id='', info='', summary=''):
    user_id = await get_id_by_username(bot, username)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, username, contact, thread_id, info, summary)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, contact, thread_id, info, summary))
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
    allowed_columns = {"username", "contact", "thread_id", "description", "summary"}
    
    if column not in allowed_columns:
        raise ValueError(f"Недопустимое имя колонки: {column}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {column} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()


def update_user_param_by_name(username: str, column: str, value):
    """Обновляет значение определённого параметра у username"""
    allowed_columns = {"contact", "thread_id", "description", "summary"}
    
    if column not in allowed_columns:
        raise ValueError(f"Недопустимое имя колонки: {column}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {column} = ? WHERE username = ?", (value, username))
    conn.commit()
    conn.close()


def get_users():
    """Вернёт список всех user_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def get_users_without_contact():
    """Вернёт список user_id, у которых contact = False"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE contact = 0")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def get_user_param(user_id: int, column: str):
    """Возвращает значение определённого параметра для заданного user_id"""
    allowed_columns = {"user_id", "username", "contact", "thread_id", "info", "summary"}
    
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
    conn.close()
    return rows


def show_users(sorted_by_contact=False):
    rows = get_all_users(sorted_by_contact)
    headers = ["Id", "Username", "Contact", "Thread ID", "Info", "Summary"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))