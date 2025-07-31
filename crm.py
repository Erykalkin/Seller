import requests
import uuid
import datetime
import json
from decouple import config

# URL формы amoCRM
url = "https://forms.amocrm.ru/queue/add"
form_id = config('CRM_FORM_ID')
hash = config('CRM_HASH')


# Данные от пользователя
user_data = {
    "name": "Иванов Иван Иванович",        # fields[name_1]
    "phone": "+79999999999",               # fields[581821_1][521181]
    "note": "Это примечание из формы",     # fields[note_2]
    "telegram": "ivanov",                  # fields[656491_1]
}

# Формируем тело формы
form_data = {
    "fields[name_1]": user_data["name"],
    "fields[581821_1][521181]": user_data["phone"],
    "fields[note_2]": user_data["note"],
    "fields[656491_1]": user_data["telegram"],
    "form_id": form_id,
    "hash": hash,
    "user_origin": json.dumps({
        "datetime": datetime.datetime.now().strftime('%a %b %d %Y %H:%M:%S GMT%z'),
        "timezone": "Europe/Moscow",
        "referer": "https://yyvladelets.amocrm.ru/"
    }),
    "visitor_uid": str(uuid.uuid4()),              
    "form_request_id": str(uuid.uuid4()),          
    "gso_session_uid": str(uuid.uuid4()),          
}

# Заголовки (эмулируем форму в браузере)
headers = {
    "Origin": "https://forms.amocrm.ru",
    "Referer": "https://forms.amocrm.ru/forms/html/form_1579218_affb08f106552e982527cec4f563692b.html"
}

# Отправляем запрос
response = requests.post(url, data=form_data, headers=headers)

# Ответ
print(f"Status: {response.status_code}")
print(response.text)