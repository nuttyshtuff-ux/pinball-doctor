import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from PIL import Image
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)

# UPDATED FOR APRIL 2026: 
# gemini-1.5-flash is retired. gemini-2.5-flash is the new stable.
MODEL_NAME = 'gemini-2.5-flash'

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- HIDDEN HELPER: IPDB SCHEMATIC FINDER ---
def find_ipdb_schematics(game_name):
    search_url = f"https://www.ipdb.org/search.cgi?name={game_name.replace(' ', '+')}&searchtype=advanced"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(search_url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = [f"{a.text}: https://www.ipdb.org{a['href']}" for a in soup.find_all('a', href=True) if "manual" in a.text.lower() or "schematic" in a.text.lower()]
            return "\n".join(links[:3])
    except: return "No IPDB links found."

# --- AI HELPERS ---
def process_request(user_input, history, specs=None, image=None):
    # DEFENSIVE MODEL LOADING: If the main name 404s, try the latest preview
    try:
        model = genai.GenerativeModel(MODEL_NAME)
    except:
        model = genai.GenerativeModel('gemini-3-flash-preview')

    if not specs:
        id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
        try:
            res = model.generate_content(id_prompt)
            specs = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
            st.session_state.specs = specs
        except: 
            specs = {"mfg": "Unknown", "system": "General", "is_em": False, "game": "Pinball Machine"}
            st.session_state.specs = specs

    ipdb_context = find_ipdb_schematics(specs.get('game', ''))
    
    # Scraper Context
    wiki_context = ""
    try:
        wiki_path = "EM_Repair" if specs.get('is_em') else specs.get('system', '').replace(" ", "_")
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        wiki_context = BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:2000]
    except: pass

    full_prompt = [f"""
    Role: Pinball Doctor. Machine: {specs.get('game')} ({specs.get('mfg')} {specs.get('system')}).
    IPDB: {ipdb_context} | Wiki: {wiki_context} | History: {history}
    User: {user_input}
    """]
    
    if image:
        full_prompt.append(image)

    response = model.generate_content(full_prompt)
    return response.text, specs

# --- UI (MAINTAINING YOUR SECURE LAYOUT) ---
with st.sidebar:
    st.header("🔐 Tech Access")
    tech_pass = st.text_input("Enter Tech Password", type="password")
    if tech_pass == st.secrets.get("TECH_PASSWORD"):
        st.success("Access Granted")
        uploaded_file = st.file_uploader("Upload Board Photo/Schematic", type=['png', 'jpg', 'jpeg'])
        if st.session_state.specs and st.button("New Repair Case"):
            st.session_state.clear()
            st.rerun()

if tech_pass == st.secrets.get("TECH_PASSWORD"):
    st.title("🩺 Pinball Doctor")
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
                img = Image.open(uploaded_file) if uploaded_file else None
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
                answer, specs = process_request(prompt, history, st.session_state.specs, image=img)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
else:
    st.title("🩺 Pinball Doctor")
    st.warning("Enter the Tech Password to begin.")
