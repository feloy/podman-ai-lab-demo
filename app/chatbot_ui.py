from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain_community.callbacks import StreamlitCallbackHandler
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
import streamlit as st
import requests
import time
import json
import os 

model_service = os.getenv("MODEL_ENDPOINT",
                          "http://localhost:8001")
model_service = f"{model_service}/v1"

@st.cache_resource(show_spinner=False)
def checking_model_service():
    start = time.time()
    print("Checking Model Service Availability...")
    ready = False
    while not ready:
        try:
            request_cpp = requests.get(f'{model_service}/models')
            request_ollama = requests.get(f'{model_service[:-2]}api/tags')
            if request_cpp.status_code == 200:
                server = "Llamacpp_Python"
                ready = True
            elif request_ollama.status_code == 200:
                server = "Ollama"
                ready = True        
        except:
            pass
        time.sleep(1)
    print(f"{server} Model Service Available")
    print(f"{time.time()-start} seconds")
    return server 

def get_models():
    try:
        response = requests.get(f"{model_service[:-2]}api/tags")
        return [i["name"].split(":")[0] for i in  
            json.loads(response.content)["models"]]
    except:
        return None

with st.spinner("Checking Model Service Availability..."):
    server = checking_model_service()

def enableInput():
    st.session_state["input_disabled"] = False

def disableInput():
    st.session_state["input_disabled"] = True

st.title("💬 Search podman-desktop.io")  
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", 
                                     "content": "what do you want to search on podman-desktop.io?"}]
if "input_disabled" not in st.session_state:
    enableInput()

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

@st.cache_resource()
def memory():
    memory = ConversationBufferWindowMemory(return_messages=True,k=3)
    return memory

model_name = os.getenv("MODEL_NAME", "") 

if server == "Ollama":
    models = get_models()
    with st.sidebar:
        model_name = st.radio(label="Select Model",
            options=models)

llm = ChatOpenAI(base_url=model_service, 
        api_key="sk-no-key-required",
        model=model_name,
        streaming=True,
        callbacks=[StreamlitCallbackHandler(st.empty(),
                                            expand_new_thoughts=True,
                                            collapse_completed_thoughts=True)])

prompt = ChatPromptTemplate.from_messages([
    ("system", "reply in JSON format with an array of objects with 2 fields name and URL (and with no more text than the JSON output), with a list of pages in the website podman-desktop.io related to my query"),
    MessagesPlaceholder(variable_name="history"),
    ("user", "{input}")
])

chain = LLMChain(llm=llm, 
                prompt=prompt,
                verbose=False,
                memory=memory())

if prompt := st.chat_input(disabled=st.session_state["input_disabled"],on_submit=disableInput):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)
    response = chain.invoke(prompt)
    st.chat_message("assistant").markdown(response["text"])    
    st.session_state.messages.append({"role": "assistant", "content": response["text"]})
    enableInput()
    st.rerun()