import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from dotenv import load_dotenv

# --- SETUP (NO CHANGES TO GOOGLE CALLS) ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

# PERSISTENCE
if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- CSS HACK FOR SPACING ---
st.markdown("""
    <style>
    .block-container {
        padding-bottom: 5rem;
    }
    .stCaption {
        margin-top: -20px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- AI HELPERS ---
def process_request(user_input, history, specs=None):
    # Your locked-in working model call
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    if not specs:
        id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":bool, \"game\":\"\"}}"
        try:
            res = model.generate_content(id_prompt)
            specs = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
            st.session_state.specs = specs
        except: 
            return "Doctor: I couldn't identify that machine. Please try again.", None

    context = ""
    wiki_path = "EM_Repair" if specs.get('is_em') else specs.get('system', '').replace(" ", "_")
    try:
        wiki_res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        context = BeautifulSoup(wiki_res.text, 'html.parser').find(id="mw-content-text").get_text()[:2500]
    except: pass

    full_prompt = f"""
    You are Pinball Doctor. 
    Machine: {specs['game']} ({specs['mfg']} {specs['system']})
    History: {history}
    Current Input: {user_input}
    Technical Context: {context}
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
    st.caption(f"🔧 Repairing: **{s['game']}** | {s['mfg']} {s['system']}")
    if st.sidebar.button("New Case"):
        st.session_state.clear()
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# FIXED LINE: 
# Removed 'placeholder=' keyword. Just an empty string "" works to keep it blank.
if prompt := st.chat_input(""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Diagnosing..."):
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            answer, specs = process_request(prompt, history, st.session_state.specs)
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
