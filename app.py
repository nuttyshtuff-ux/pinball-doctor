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

# Hide Streamlit's default menu/footer for a cleaner "App" feel
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

load_dotenv()
API_KEY = st.secrets["GOOGLE_API_KEY"]
CSE_CX = st.secrets["SEARCH_ENGINE_ID"]
genai.configure(api_key=API_KEY)

# Using April 2026 Stable Model
MODEL_NAME = 'gemini-2.5-flash'

# Initialize Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- SEARCH HELPERS ---
def search_pinside(game, issue):
    """Searches Pinside Tech Forums via Google Custom Search."""
    query = f"{game} {issue} site:pinside.com"
    url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={CSE_CX}&q={query}"
    try:
        res = requests.get(url, timeout=5).json()
        threads = [f"Pinside: {item['title']} - {item['snippet']}" for item in res.get('items', [])[:3]]
        return "\n".join(threads)
    except: return "No Pinside threads found."

def find_ipdb_schematics(game_name):
    """Locates manuals and schematics on IPDB."""
    search_url = f"https://www.ipdb.org/search.cgi?name={game_name.replace(' ', '+')}&searchtype=advanced"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(search_url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = [f"{a.text}: https://www.ipdb.org{a['href']}" for a in soup.find_all('a', href=True) if "manual" in a.text.lower() or "schematic" in a.text.lower()]
            return "\n".join(links[:2])
    except: return "No IPDB links found."

# --- AI ENGINE ---
def process_request(user_input, history, specs=None, image=None):
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Identify the machine if not already known
    if not specs:
        id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
        try:
            res = model.generate_content(id_prompt)
            text = res.text.strip().replace('```json', '').replace('```', '')
            specs = json.loads(text)
            st.session_state.specs = specs
        except:
            specs = {"mfg": "Unknown", "system": "General", "is_em": False, "game": "Pinball Machine"}
            st.session_state.specs = specs

    # Gather data from the Trinity
    pinside_data = search_pinside(specs.get('game', 'Unknown'), user_input)
    ipdb_data = find_ipdb_schematics(specs.get('game', 'Unknown'))
    
    wiki_context = ""
    try:
        sys_name = specs.get('system', 'General').replace(" ", "_")
        wiki_path = "EM_Repair" if specs.get('is_em') else sys_name
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        wiki_context = BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:2000]
    except: pass

    full_prompt = [f"""
    Role: Expert Pinball Doctor.
    Machine: {specs.get('game')} ({specs.get('mfg')} {specs.get('system')})
    PINSIDE TECH: {pinside_data}
    IPDB MANUALS: {ipdb_data}
    PINWIKI SPECS: {wiki_context}
    HISTORY: {history}
    ISSUE: {user_input}
    """]
    if image: full_prompt.append(image)

    response = model.generate_content(full_prompt)
    return response.text, specs

# --- SIDEBAR (Security & Image Upload) ---
with st.sidebar:
    st.header("🔐 Tech Access")
    if not st.session_state.authenticated:
        tech_pass = st.text_input("Enter Tech Password", type="password")
        if tech_pass == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        elif tech_pass != "":
            st.error("Incorrect Password")
    
    if st.session_state.authenticated:
        st.success("Authorized Tech")
        st.header("Visual Aid")
        uploaded_file = st.file_uploader("Upload Schematic or Board Photo", type=['png', 'jpg', 'jpeg'])
        st.divider()
        if st.button("🆕 New Repair Case"):
            st.session_state.messages = []
            st.session_state.specs = None
            st.rerun()
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

# --- MAIN INTERFACE ---
if st.session_state.authenticated:
    st.title("🩺 Pinball Doctor")
    
    # Static info at the top to keep bottom clear for mobile input
    if not st.session_state.specs:
        st.info("What's the machine and the issue?")
    else:
        s = st.session_state.specs
        with st.expander(f"🔧 Active Case: {s.get('game')}", expanded=False):
            st.write(f"**Manufacturer:** {s.get('mfg')}")
            st.write(f"**System:** {s.get('system')}")
            st.write("**Data Sources Connected:** Pinside Tech, IPDB, PinWiki")

    # Show Chat Messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input(""):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Consulting Pinside, IPDB, and PinWiki..."):
                img = Image.open(uploaded_file) if uploaded_file else None
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
                answer, specs = process_request(prompt, history, st.session_state.specs, image=img)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.toast(f"Diagnostics complete for {specs.get('game')}", icon='🧠')

else:
    st.title("🩺 Pinball Doctor")
    st.warning("Please enter the Tech Password in the sidebar to begin diagnosis.")
