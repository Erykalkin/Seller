# from PIL import Image
import os
import json


def save_dialog(file, messages):
    log_dir = "dialog_logs"
    os.makedirs(log_dir, exist_ok=True)
    filename = os.path.join(log_dir, f"{file}.txt")

    with open(filename, "w", encoding="utf-8") as f:    
        for message in messages:
            role = message.role.upper()
            content = message.content[0].text.value if message.content else "[пусто]"
            f.write(f"[{role}]\n{content}\n\n")


# def update_prompt(text, file='assistant'):
#     try:
#         txt_file = Rf"prompts\{file}.txt"

#         with open(txt_file, "w", encoding="utf-8") as f:
#             f.write(text)
    
#     except Exception as e:
#         print(f'update_prompt error: {e}')


# def get_prompt_from_PC():
#     input_md_file = R"C:\Users\George.LAPTOP-TLP259VH\Base\ML\Проекты\Financial bot\Prompt.md"
#     output_txt_file = R"C:\Users\George.LAPTOP-TLP259VH\Documents\GitHub\Bot\prompts\assistant.txt"

#     with open(input_md_file, "r", encoding="utf-8") as md_file:
#         content = md_file.read()

#     with open(output_txt_file, "w", encoding="utf-8") as txt_file:
#         txt_file.write(content)
    
#     with open(output_txt_file, "r", encoding="utf-8") as prompt_file:
#         prompt = prompt_file.read()
    
#     return prompt



# def log(msg):
#     try:
#         with open('log.txt', 'w', encoding="utf-8") as txt_file:
#             txt_file.write(str(list(msg)[0].role) + 
#                        '\n\n' + 
#                        str(list(msg)[0].content[0].text.value))
#     except Exception as e:
#         try:
#             with open('log.txt', 'w', encoding="utf-8") as txt_file:
#                 txt_file.write(msg)
#         except Exception as e:
#             pass



# def admin(marker):
#     msg = "%ADMIN%: "

#     if marker == "JSON_ERROR":
#         msg += "REPEAT PREVIOUS ANSWER IN JSON FORMAT!"

#     elif marker == "CLIENT_PREF":
#         msg += "THIS IS A CLIENT PREFERENCES LIST:"

#     elif marker == "CLIENT_INFO":
#         msg += "MAKE DESCRIPTION OF CLIENT IN THE FOLLOWING JSON FORMAT:\n"
#         with open('client_list.txt', 'r', encoding="utf-8") as txt_file:
#             msg += txt_file.read()
        
#     return msg



# def load_image(image_id):
#     image_path = fR"C:\Users\George.LAPTOP-TLP259VH\Documents\GitHub\Bot\content\images\{image_id}.png"

#     try:
#         image = Image.open(image_path)
#         return image
#     except FileNotFoundError:
#         print(f"Image with id {image_id} not found.")
#         return None
#     except Exception as e:
#         print(f"An error occurred while loading the image: {e}")
#         return None
