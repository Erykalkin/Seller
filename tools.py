from database import*
from crm import*
import json


LINKS_DB = json.loads("Seller/data/links.json")


def get_link(*keys):
    current = LINKS_DB
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return "Ссылка не найдена"
    if isinstance(current, str):
        return current
    return "Ссылка не найдена"


def save_user_phone(user_id: int, phone: str):
    update_user_param(user_id, "telephone", phone)


def save_user_name(user_id: int, name: str):
    update_user_param(user_id, "name", name)


def ban_user(user_id: int):
    update_user_param(user_id, "banned", True)


def process_user_agreement(user_id: int, summary: str):
    update_user_param(user_id, "summary", summary)

    user = get_user(user_id)
    username, telephone, name = user[1], user[2], user[3]
    if name == '':
        name = username

    success = send_to_crm(name=name, phone=telephone, note=summary, telegram=username)

    if success:
        update_user_param(user_id, "crm", True)
    else:
        print(f"Failed to add to CRM: {username}")

