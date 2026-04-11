import streamlit as st
import google.generativeai as genai
import requests, json, os
from bs4 import BeautifulSoup
from PIL import Image

# --- SETUP ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
MODEL_NAME = 'gemini-1.5-flash' # Using the model we know works

if "messages" not in st.session_state: st.session_state.messages = []
if "specs" not in st.session_state: st.session_state.specs = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# --- THE TRINITY SEARCH (Now Step 1) ---
def get_raw_search_data(query):
    """Fetches raw data from the web BEFORE identification."""
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={query}+pinball"
        res = requests.get(url, timeout=5).json()
        return "\n".join([f"{i['title']}: {i['snippet']}" for i in res.get('items', [])[:5]])
    except:
        return ""

def get_wiki_context(system, is_em):
    try:
        path = "EM_Repair" if is_em else system.replace(" ", "_")
        r = requests.get(f"https://pinwiki.com/wiki/index.php/{path}", timeout=5)
        return BeautifulSoup(r.text, 'html.parser').find(id="mw-content-text").get_text()[:1500]
    except: return ""

# --- LOGIN ---
if not st.session_state.authenticated:
    st.title("🩺 Pinball Doctor")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        if pw == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    up = st.file_uploader("Upload Photo", type=['png', 'jpg', 'jpeg'])
    if st.button("🆕 New Case"):
        st.session_state.messages, st.session_state.specs = [], None
        st.rerun()

# --- MAIN ---
st.title("🩺 Pinball Doctor")
spec = st.session_state.specs

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Machine + Issue..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Doctor Pinball is Thinking..."):
            model = genai.GenerativeModel(MODEL_NAME)
            
            # STEP 1: Blind Web Search
            search_evidence = get_raw_search_data(prompt)
            
            # STEP 2: Identification using Search Evidence
            if not spec:
                id_p = f"""
                Analyze this search data:
                {search_evidence}
                
                Based on the data, identify the machine in the user prompt: '{prompt}'
                Return JSON ONLY: {{"mfg":"", "system":"", "is_em":true/false, "game":""}}
                """
                try:
                    res = model.generate_content(id_p)
                    spec = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
                    st.session_state.specs = spec
                except:
                    spec = {"mfg":"Unknown", "system":"General", "is_em":True, "game":"Pinball Machine"}
            
            # STEP 3: Specific Wiki Deep-Dive
            wiki = get_wiki_context(spec['system'], spec['is_em'])
            
            # STEP 4: Diagnostic
            ctx = f"Machine: {spec['game']} ({spec['mfg']})\nEvidence: {search_evidence}\nWiki: {wiki}\nIssue: {prompt}"
            inputs = [ctx]
            if up: inputs.append(Image.open(up))
            
            try:
                ans = model.generate_content(inputs).text
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
            except:
                st.error("Connection lost. Try again.")
