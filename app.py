import streamlit as st
import google.generativeai as genai
import requests, json, os
from bs4 import BeautifulSoup
from PIL import Image

# --- SETUP ---
st.set_page_config(page_title="Doctor Pinball", page_icon="🩺")
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
MODEL_NAME = 'gemini-2.5-flash' 

# Session States
if "messages" not in st.session_state: st.session_state.messages = []
if "specs" not in st.session_state: st.session_state.specs = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# --- SEARCH TOOLS ---
def get_raw_search_data(query, is_stern=False):
    """Enhanced search that targets Stern Tech School for modern machines."""
    search_query = f"{query} pinball"
    if is_stern:
        search_query = f"{query} Stern Tech School official service troubleshooting"
        
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={search_query}"
        res = requests.get(url, timeout=10).json()
        if "items" in res:
            return "\n".join([f"{i['title']}: {i['snippet']}" for i in res['items'][:5]])
        return "No specific technical data found."
    except: return "Search unavailable."

def get_wiki_context(system, is_em):
    try:
        path = "EM_Repair" if is_em else system.replace(" ", "_")
        r = requests.get(f"https://pinwiki.com/wiki/index.php/{path}", timeout=8)
        content = BeautifulSoup(r.text, 'html.parser').find(id="mw-content-text")
        return content.get_text()[:1500] if content else "Wiki data empty."
    except: return "Wiki unavailable."

# --- LOGIN ---
if not st.session_state.authenticated:
    st.title("🩺 Doctor Pinball")
    pw = st.text_input("Tech Password", type="password")
    if st.button("Login"):
        if pw == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    up = st.file_uploader("Upload Board/Part Photo", type=['png', 'jpg', 'jpeg'])
    if st.button("🆕 New Repair Case"):
        st.session_state.messages, st.session_state.specs = [], None
        st.rerun()

# --- MAIN ---
st.title("🩺 Doctor Pinball")
spec = st.session_state.specs

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

placeholder = "Enter Mfg + Game (e.g., Stern Godzilla)" if not spec else f"Analyzing {spec['game']}..."

if prompt := st.chat_input(placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Doctor Pinball is Thinking..."):
            model = genai.GenerativeModel(MODEL_NAME)
            
            # STEP 1: Identification
            if not spec:
                # Blind search to help ID
                search_evidence = get_raw_search_data(prompt)
                id_p = f"Identify machine: '{prompt}'. Evidence: {search_evidence}. Return JSON ONLY: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
                try:
                    res = model.generate_content(id_p)
                    clean_res = res.text.strip().replace('```json', '').replace('```', '')
                    spec = json.loads(clean_res)
                    st.session_state.specs = spec
                except:
                    spec = {"mfg":"Unknown", "system":"General", "is_em":True, "game":"Pinball Machine"}
                    st.session_state.specs = spec

            # STEP 2: Targeted Diagnostics (Now checks for Stern Tech Videos)
            is_stern = spec.get('mfg', '').lower() == 'stern'
            technical_data = get_raw_search_data(f"{spec['mfg']} {spec['game']} {prompt}", is_stern=is_stern)
            wiki = get_wiki_context(spec['system'], spec['is_em'])
            
            # STEP 3: Final Analysis
            hist = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            ctx = f"Machine: {spec['mfg']} {spec['game']}\nTech Data/Videos: {technical_data}\nWiki: {wiki}\nIssue: {prompt}\nHistory: {hist}"
            
            inputs = [ctx]
            if up: inputs.append(Image.open(up))
            
            try:
                ans = model.generate_content(inputs).text
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
            except Exception as e:
                st.error(f"Handshake failed: {str(e)}")
