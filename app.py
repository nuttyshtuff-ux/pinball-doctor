import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from PIL import Image
from dotenv import load_dotenv

# --- SETUP & CONFIG ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺", layout="centered")

# Zero-Gap CSS
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    h1 { margin-bottom: -20px !important; }
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

load_dotenv()
API_KEY = st.secrets["GOOGLE_API_KEY"]
CSE_CX = st.secrets["SEARCH_ENGINE_ID"]
genai.configure(api_key=API_KEY)

# Use these models for the best balance of stability and pinball knowledge
ID_MODEL = 'gemini-1.5-pro'   
DIAG_MODEL = 'gemini-1.5-flash' 

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- SEARCH HELPERS ---
def search_pinside(game, issue):
    query = f"{game} {issue} site:pinside.com"
    url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={CSE_CX}&q={query}"
    try:
        res = requests.get(url, timeout=5).json()
        items = res.get('items', [])
        return "\n".join([f"Pinside: {i['title']} - {i['snippet']}" for i in items[:3]])
    except:
        return "No Pinside threads found."

def find_ipdb_schematics(game_name):
    search_url = f"https://www.ipdb.org/search.cgi?name={game_name.replace(' ', '+')}&searchtype=advanced"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(search_url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = [f"{a.text}: https://www.ipdb.org{a['href']}" for a in soup.find_all('a', href=True) if "manual" in a.text.lower() or "schematic" in a.text.lower()]
            return "\n".join(links[:2])
    except:
        return "No IPDB links found."

# --- AI ENGINE ---
def process_request(user_input, history, specs=None, image=None):
    if not specs:
        model_id = genai.GenerativeModel(ID_MODEL)
        id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
        try:
            res = model_id.generate_content(id_prompt)
            clean_text = res.text.strip().replace('```json', '').replace('```', '')
            specs = json.loads(clean_text)
            st.session_state.specs = specs
        except:
            specs = {"mfg": "Unknown", "system": "General", "is_em": False, "game": "Pinball Machine"}
            st.session_state.specs = specs

    pinside_data = search_pinside(specs.get('game', 'Unknown'), user_input)
    ipdb_data = find_ipdb_schematics(specs.get('game', 'Unknown'))
    
    wiki_context = ""
    try:
        sys_name = specs.get('system', 'General').replace(" ", "_")
        wiki_path = "EM_Repair" if specs.get('is_em') else sys_name
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        wiki_context = BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:2000]
    except:
        pass

    model_diag = genai.GenerativeModel(DIAG_MODEL)
    prompt_content = f"Role: Expert Pinball Doctor. Machine: {specs.get('game')} ({specs.get('mfg')} {specs.get('system')})\nPINSIDE: {pinside_data}\nIPDB: {ipdb_data}\nWIKI: {wiki_context}\nHISTORY: {history}\nISSUE: {user_input}"
    
    parts = [prompt_content]
    if image:
        parts.append(image)
    
    response = model_diag.generate_content(parts)
    return response.text, specs

# --- AUTH SCREEN ---
if not st.session_state.authenticated:
    st.title("🩺 Pinball Doctor")
    st.info("Authorized Technicians Only")
    tech_pass = st.text_input("Enter Tech Password", type="password")
    if st.button("Login"):
        if tech_pass == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Access Denied.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🛠️ Tech Tools")
    uploaded_file = st.file_uploader("Upload Board Photo", type=['png', 'jpg', 'jpeg'])
    st.divider()
    if st.button("🆕 New Repair Case"):
        st.session_state.messages = []
        st.session_state.specs = None
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# --- MAIN INTERFACE ---
st.title("🩺 Pinball Doctor")

# Build the placeholder string carefully
if st.session_state.specs:
    s = st.session_state.specs
    box_placeholder = f"🔧 {s.get('game')} - Ask the Doctor..."
else:
    box_placeholder = "What's the machine and the issue?"

# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input logic
if prompt := st.chat_input(box_placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Consulting the Trinity..."):
            img = Image.open(uploaded_file) if uploaded_file else None
            # Extract history string
            history_str = ""
            for m in st.session_state.messages[:-1]:
                history_str += f"{m['role']}: {m['content']}\n"
            
            answer, current_specs = process_request(prompt, history_str, st.session_state.specs, image=img)
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content":h
