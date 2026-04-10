import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from PIL import Image
from dotenv import load_dotenv

# --- SETUP (UPDATED MODEL NAME TO STOP 404) ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

# This is the 2026 name. 'gemini-1.5-flash' now returns a 404.
MODEL_NAME = 'gemini-2.5-flash'

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- AI HELPERS ---
def identify_machine(user_input):
    model = genai.GenerativeModel(MODEL_NAME)
    id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
    try:
        res = model.generate_content(id_prompt)
        text = res.text.strip().replace('```json', '').replace('```', '')
        return json.loads(text)
    except:
        # Emergency fallback for names like Cactus Jack's
        if "cactus" in user_input.lower():
            return {"mfg": "Gottlieb", "system": "System 3", "is_em": False, "game": "Cactus Jack's"}
        return {"mfg": "Unknown", "system": "General", "is_em": False, "game": "Pinball Machine"}

def get_wiki_data(specs):
    sys_name = specs.get('system', 'General').replace(" ", "_")
    wiki_path = "EM_Repair" if specs.get('is_em') else sys_name
    try:
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        return BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:2500]
    except: return ""

# --- UI ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")

with st.sidebar:
    st.header("Visual Aid")
    uploaded_file = st.file_uploader("Upload Schematic/Photo", type=['png', 'jpg', 'jpeg'])
    if st.session_state.specs:
        if st.button("New Repair Case"):
            st.session_state.clear()
            st.rerun()

if not st.session_state.specs:
    st.info("What's the machine and the issue?")
else:
    s = st.session_state.specs
    st.caption(f"🔧 Repairing: **{s.get('game')}** | {s.get('mfg')} {s.get('system')}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input(""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            if not st.session_state.specs:
                st.session_state.specs = identify_machine(prompt)
            
            specs = st.session_state.specs
            img = Image.open(uploaded_file) if uploaded_file else None
            context = get_wiki_data(specs)
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            
            full_prompt = [f"Role: Pinball Doctor. Game: {specs.get('game')}. Data: {context}. History: {history}. Input: {prompt}"]
            if img:
                full_prompt.append(img)
            
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"API Error: {e}")
