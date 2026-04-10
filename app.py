import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from PIL import Image
from dotenv import load_dotenv

# --- SETUP (STRICTLY MAINTAINING YOUR GOOGLE CALLS) ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- AI HELPERS ---
def process_request(user_input, history, specs=None, image=None):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 1. Identity Logic
    if not specs:
        id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":bool, \"game\":\"\"}}"
        try:
            res = model.generate_content(id_prompt)
            specs = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
            st.session_state.specs = specs
        except: 
            return "Doctor: I couldn't identify the machine. Please try again.", None

    # 2. Scraper Context
    context = ""
    wiki_path = "EM_Repair" if specs.get('is_em') else specs.get('system', '').replace(" ", "_")
    try:
        wiki_res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        context = BeautifulSoup(wiki_res.text, 'html.parser').find(id="mw-content-text").get_text()[:2500]
    except: pass

    # 3. Vision + Text Logic
    full_prompt = [f"""
    You are Pinball Doctor. 
    Machine: {specs['game']} ({specs['mfg']} {specs['system']})
    History: {history}
    Technical Context: {context}
    
    USER INPUT: {user_input}
    """]
    
    # If an image was uploaded, add it to the AI call
    if image:
        full_prompt.append(image)
        full_prompt.append("Analyze this schematic or photo for the user's issue.")

    response = model.generate_content(full_prompt)
    return response.text, specs

# --- UI ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")

# Sidebar for Image Upload & Reset
with st.sidebar:
    st.header("Visual Aid")
    uploaded_file = st.file_uploader("Upload Schematic or Board Photo", type=['png', 'jpg', 'jpeg'])
    if uploaded_file:
        st.image(uploaded_file, caption="Technical Reference", use_column_width=True)
    
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
        with st.spinner("Analyzing data and images..."):
            img = Image.open(uploaded_file) if uploaded_file else None
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            answer, specs = process_request(prompt, history, st.session_state.specs, image=img)
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
