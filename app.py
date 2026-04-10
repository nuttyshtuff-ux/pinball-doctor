import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from dotenv import load_dotenv

# --- 2026 SETUP ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

# This is the 2026 stable model that replaces 'gemini-1.5-flash'
MODEL_NAME = 'gemini-2.5-flash'

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- AI HELPERS ---
def process_request(user_input, history, specs=None):
    model = genai.GenerativeModel(MODEL_NAME)
    
    # 1. Identify machine if first time
    if not specs:
        id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
        try:
            res = model.generate_content(id_prompt)
            clean_text = res.text.strip().replace('```json', '').replace('```', '')
            specs = json.loads(clean_text)
            st.session_state.specs = specs
        except: 
            return "Doctor: I couldn't identify that machine. Please try again with the full name.", None

    # 2. Get Knowledge Base Context
    context = ""
    wiki_path = "EM_Repair" if specs.get('is_em') else specs.get('system', '').replace(" ", "_")
    try:
        wiki_res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        context = BeautifulSoup(wiki_res.text, 'html.parser').find(id="mw-content-text").get_text()[:2500]
    except: pass

    # 3. Diagnosis
    full_prompt = f"""
    You are Pinball Doctor. 
    Machine: {specs.get('game')} ({specs.get('mfg')} {specs.get('system')})
    History: {history}
    Current Input: {user_input}
    Technical Context: {context}
    
    If the user says a fix failed, offer a different technical path.
    """
    response = model.generate_content(full_prompt)
    return response.text, specs

# --- UI ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")

if not st.session_state.specs:
    st.info("What's the machine and the issue?")
else:
    s = st.session_state.specs
    st.caption(f"🔧 Repairing: **{s.get('game')}** | {s.get('mfg')} {s.get('system')}")
    if st.sidebar.button("New Case"):
        st.session_state.clear()
        st.rerun()

# Display Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Single Combined Input Box
if prompt := st.chat_input("Machine and Issue..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Diagnosing..."):
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            answer, specs = process_request(prompt, history, st.session_state.specs)
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
