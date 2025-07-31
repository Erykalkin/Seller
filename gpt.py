from decouple import config
from openai import OpenAI
import time
import json
from utils import*
from database import*
from tools import*


def load_client_and_assistant():
    client = OpenAI(api_key=config('OPENAI_API_KEY'))
    assistant = client.beta.assistants.update(
        assistant_id=config('ASSISTANT_ID'), 
        instructions=get_prompt(), 
        response_format=load_response_format()
    )
    return client, assistant

client, assistant = load_client_and_assistant()


def get_or_create_thread(username):
    thread_id = get_user_param(username, "thread_id")

    if thread_id:
        return thread_id
    
    thread = client.beta.threads.create()
    update_user_param(username, "thread_id", thread.id)
    return thread.id


def make_output_from_response(response):
    response_content = response[-1].content[0].text
    annotations = response_content.annotations

    citations = []
    for index, annotation in enumerate(annotations):
        response_content.value = response_content.value.replace(annotation.text, '')
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {cited_file.filename}")
    
    response = response_content.value

    return response


def get_assistant_response(user_input, thread_id):
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input
    )
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant.id,
    )

    if run.status == "requires_action":
        print('TOOL')
        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            function_name = tool_call.function.name
            arguments = tool_call.function.arguments

            try:
                args = json.loads(arguments)
            except Exception as e:
                print("Failed to parse tool arguments:", e)
                continue

            if function_name == "get_plot_link":
                output = get_plot_link_handler(args.get("plot_id"))

            elif function_name == "generate_summary_after_conversation":
                output = make_summary(args.get("summary"))
                print(output)

            tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": output
                })

        # Отправка результатов выполнения инструментов
        if tool_outputs:
            try:
                run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                print("Tool outputs submitted successfully.")
            except Exception as e:
                print("Failed to submit tool outputs:", e)

    if run.status == 'completed':
        messages = client.beta.threads.messages.list(
            thread_id=thread_id, order="asc"
        )
        save_dialog(thread_id, list(messages))
        return make_output_from_response(list(messages))
    else:
        print('бля')
        return "Error"


# if __name__ == "__main__":
#     th = get_or_create_thread(1)
#     print("💬 GPT-ассистент (введите 'выход' чтобы завершить)")
#     while True:
#         user_input = input("Вы: ").strip()
#         if user_input.lower() in ("выход", "exit", "quit"):
#             print("👋 Завершение диалога.")
#             break

#         response = get_assistant_response(user_input, th)
#         print("Бот:", response)