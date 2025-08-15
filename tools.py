from database import*
from crm import*


def get_plot_link(plot_id):
    links = {
        "Междуморье": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/midsea",
        "Победный берег": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/pobednyi",
        "Королёвские дачи": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/korolevo",
        "Усадьба Джарылгач": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/dzharylgach",
        "Великие Луга": "https://xn----7sbbqebqelognciq2b4r.xn--p1ai/velikieluga"
    }
    return links.get(plot_id, "Неизвестный участок")


def send_tg_link():
    return "https://t.me/nasledie_company"


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

