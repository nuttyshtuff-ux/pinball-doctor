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
CSE_CX = st.secrets["SEARCH_ENGINE_ID"] # Your new Google Custom Search ID
genai.configure(api_key=API_KEY)

# Using the April 2026 stable model
MODEL_NAME = 'gemini-2.5-flash'

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- SEARCH HELPER: PINSIDE ---
def search_pinside(game, issue):
    """Uses Google Custom Search API to find Pinside forum threads."""
    query = f"{game} {issue} site:pinside.com"
    url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={CSE_CX}&q={query}"
    try:
        res = requests.get(url, timeout=5).json()
        # Extract snippets from the top 3 threads
        threads = [f"Pinside Thread: {item['title']} - {item['snippet']}" for item in res.get('items', [])[:3]]
        return "\n".join(threads)
    except:
        return "No relevant Pinside forum threads found."

# --- SEARCH HELPER: IPDB ---
def find_ipdb_schematics(game_name):
    """Silently checks IPDB for manual/schematic links."""
    search_url = f"https://www.ipdb.org/search.cgi?name={game_name.replace(' ', '+')}&searchtype=advanced"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(search_url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = [f"{a.text}: https://www.ipdb.org{a['href']}" for a in soup.find_all('a', href=True) if "manual" in a.text.lower() or "schematic" in a.text.lower()]
            return "\n".join(links[:2])
    except: return "No IPDB links found."

# --- AI HELPERS ---
def process_request(user_input, history, specs=None, image=None):
    model = genai.GenerativeModel(MODEL_NAME)
    
    # 1. Identity Logic (The Brain)
    if not specs:
        id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
        try:
            res = model.generate_content(id_prompt)
            text = res.text.strip().replace('```json', '').replace('```', '')
            specs = json.loads(text)
            st.session_state.specs = specs
        except:
            if "cactus" in user_input.lower():
                specs = {"mfg": "Gottlieb", "system": "System 3", "is_em": False, "game": "Cactus Jack's"}
            else:
                specs = {"mfg": "Unknown", "system": "General", "is_em": False, "game": "Pinball Machine"}
            st.session_state.specs = specs

    # 2. Data Gathering (The Trinity)
    pinside_data = search_pinside(specs.get('game'), user_input)
    ipdb_data = find_ipdb_schematics(specs.get('game'))
    
    wiki_context = ""
    try:
        sys_name = specs.get('system', 'General').replace(" ", "_")
        wiki_path = "EM_Repair" if specs.get('is_em') else sys_name
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        wiki_context = BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:2000]
    except: pass

    # 3. Multimodal Prompt Construction
    full_prompt = [f"""
    Role: Expert Pinball Doctor.
    Machine: {specs.get('game')} ({specs.get('mfg')} {specs.get('system')})
    
    FORUM SOLUTIONS (Pinside):
    {pinside_data}
    
    FACTORY DOCUMENTATION (IPDB):
    {ipdb_data}
    
    TECHNICAL WIKI DATA:
    {wiki_context}
    
    CONVERSATION HISTORY:
    {history}
    
    CURRENT ISSUE: {user_input}
    
    Diagnose the issue using both factory specs and community wisdom. If a fix failed in the history, suggest an alternative.
    """]
    
    if image:
        full_prompt.append(image)

    response = model.generate_content(full_prompt)
    return response.text, specs

# --- UI & SECURITY ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")

with st.sidebar:
    st.header("🔐 Tech Access")
    tech_pass = st.text_input("Enter Tech Password", type="password")
    if tech_pass == st.secrets["TECH_PASSWORD"]:
        st.success("Access Granted")
        uploaded_file = st.file_uploader("Upload Schematic or Board Photo", type=['png', 'jpg', 'jpeg'])
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
            with st.spinner("Searching Pinside, IPDB, and Wiki..."):
                img = Image.open(uploaded_file) if uploaded_file else None
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
                answer, specs = process_request(prompt, history, st.session_state.specs, image=img)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
else:
    st.title("🩺 Pinball Doctor")
    st.warning("Please enter the Tech Password in the sidebar.")
