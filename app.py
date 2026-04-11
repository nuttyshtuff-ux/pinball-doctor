import streamlit as st
import google.generativeai as genai
import requests, json, os
from bs4 import BeautifulSoup
from PIL import Image
from dotenv import load_dotenv

# --- SETUP ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
load_dotenv()
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Models
ID_MODEL = 'gemini-1.5-pro'
DIAG_MODEL = 'gemini-1.5-flash'

# Session States
for key in ["messages", "specs", "authenticated"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "messages" else False

# --- TOOLS ---
def search_trinity(game, issue, system, is_em):
    # Pinside Search
    res = requests.get(f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={game}+{issue}+site:pinside.com").json()
    pinside = "\n".join([f"{i['title']}: {i['snippet']}" for i in res.get('items', [])[:3]])
    
    # PinWiki Context
    wiki = ""
    try:
        path = "EM_Repair" if is_em else system.replace(" ", "_")
        r = requests.get(f"https://pinwiki.com/wiki/index.php/{path}", timeout=5)
        wiki = BeautifulSoup(r.text, 'html.parser').find(id="mw-content-text").get_text()[:1500]
    except: pass
    return pinside, wiki

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("🩺 Pinball Doctor")
    pw = st.text_input("Tech Password", type="password")
    if st.button("Login"):
        if pw == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Denied")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🛠️ Tools")
    up = st.file_uploader("Upload Photo", type=['png', 'jpg', 'jpeg'])
    if st.button("🆕 New Case"):
        st.session_state.messages, st.session_state.specs = [], False
        st.rerun()

# --- MAIN ---
st.title("🩺 Pinball Doctor")
spec = st.session_state.specs
placeholder = f"🔧 {spec['game']} - Ask..." if spec else "Machine + Issue (e.g. Blackwater 100 won't boot)"

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input(placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Diagnosing..."):
            # ID Machine
            if not spec:
                m_id = genai.GenerativeModel(ID_MODEL)
                prompt_id = f"Identify: '{prompt}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
                res_id = m_id.generate_content(prompt_id)
                spec = json.loads(res_id.text.strip().replace('```json', '').replace('```', ''))
                st.session_state.specs = spec

            # Trinity Search
            pins, wiki = search_trinity(spec['game'], prompt, spec['system'], spec['is_em'])
            
            # Diagnostic
            m_diag = genai.GenerativeModel(DIAG_MODEL)
            hist = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            ctx = f"Game: {spec['game']} ({spec['system']})\nPinside: {pins}\nWiki: {wiki}\nIssue: {prompt}"
            
            inputs = [ctx]
            if up: inputs.append(Image.open(up))
            
            ans = m_diag.generate_content(inputs).text
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
