import openai
from openai import OpenAI
import streamlit as st
import time
import json
from json import JSONDecodeError
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from sklearn.metrics.pairwise import cosine_similarity
from utils import*
import numpy as np
import pandas as pd
from ast import literal_eval


def load_client_and_assistant():
    prompt = get_prompt('assistant')

    client = OpenAI(api_key=st.secrets['openai_api_key'])

    assistant = client.beta.assistants.update(assistant_id=st.secrets['assistant_id'], instructions=prompt)
    assistant_thread = client.beta.threads.create()

    df = pd.read_csv(R"C:\Users\George.LAPTOP-TLP259VH\Documents\GitHub\Bot\content\parsed_pdf_docs_with_embeddings.csv")
    df["embeddings"] = df.embeddings.apply(literal_eval).apply(np.array)
    
    return client, assistant, assistant_thread, df

client, assistant, assistant_thread, companion, companion_thread, df = st.session_state['API']


def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run


def make_output_from_response(response):
    response_content = response[0].content[0].text
    annotations = response_content.annotations
    citations = []
    for index, annotation in enumerate(annotations):
        response_content.value = response_content.value.replace(annotation.text, '')
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {cited_file.filename}")
    
    response = response_content.value

    try:
        response = json.loads(response.replace("```", '').replace("json", ''))
        experts = response['experts'][0]
        experts = (experts['expert_1']['answer'], experts['expert_2']['answer'], experts['expert_3']['answer'])
        img_id = response['final_answer']['image']['id']
        response = response['final_answer']['chief_expert_choice']
    except Exception as e:
        print(e)
        print(f"bad response: {response[:100]}")
        st.session_state['msg_errors'] += 1
        if st.session_state['msg_errors'] < 3:
            return get_assistant_response(admin('JSON_ERROR'))
        else:
            return e, False, ['']*3

    return response, img_id, experts


def get_embeddings(text):
    embeddings = client.embeddings.create(
      model="text-embedding-3-large",
      input=text,
      encoding_format="float"
    )
    return embeddings.data[0].embedding


def search_content(df, input_text, top_k):
    embedded_value = get_embeddings(input_text)
    df["similarity"] = df.embeddings.apply(lambda x: cosine_similarity(np.array(x).reshape(1,-1), np.array(embedded_value).reshape(1, -1)))
    res = df.sort_values('similarity', ascending=False).head(top_k)
    print(df.head())
    return res


def get_similarity(row):
    similarity_score = row['similarity']
    if isinstance(similarity_score, np.ndarray):
        similarity_score = similarity_score[0][0]
    return similarity_score


def get_companion_response(user_input):
    message = client.beta.threads.messages.create(
        thread_id=companion_thread.id,
        role="user",
        content=user_input
    )

    run = client.beta.threads.runs.create(
        thread_id=companion_thread.id,
        assistant_id=companion.id,
    )

    run = wait_on_run(run, companion_thread)

    messages = client.beta.threads.messages.list(
        thread_id=companion_thread.id, order="asc", after=message.id
    )

    try:
        response = json.loads(list(messages)[0].content[0].text.value.replace("```", '').replace("json", ''))

        initial_client_question = response['vector_search_assistance']['initial_client_question']
        refined_client_question = response['vector_search_assistance']['refined_client_question']
    except Exception as e:
        return user_input, 'broken'

    return user_input, refined_client_question


from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
def get_assistant_response(user_input):
    content = ''
    user_input, refined_input = get_companion_response(user_input)
    # refined_input = 'no'

    if st.session_state['ES'] and "%ADMIN%" not in user_input:
        
        similar_content = search_content(df, user_input+'\n'+refined_input, st.session_state['top_k'])
        content += "\n\n%CONTENT%:\n"
        
        st.session_state['len_content'] = 0

        for i, row in similar_content.iterrows():
            similarity_score = get_similarity(row)
            if similarity_score > st.session_state['threshold']:
                content += f"\n\n{row['content']}"
                st.session_state['len_content'] += 1

    message = client.beta.threads.messages.create(
        thread_id=assistant_thread.id,
        role="user",
        content='initial_client_question:\n'+user_input+'\n\nrefined_client_question:\n'+refined_input+content
    )

    run = client.beta.threads.runs.create(
        thread_id=assistant_thread.id,
        assistant_id=assistant.id,
    )

    run = wait_on_run(run, assistant_thread)

    messages = client.beta.threads.messages.list(
        thread_id=assistant_thread.id, order="asc", after=message.id
    )
    
    log(messages)
    
    return make_output_from_response(list(messages))
