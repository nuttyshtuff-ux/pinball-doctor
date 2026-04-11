import streamlit as st
import google.generativeai as genai
import requests, json, os
from bs4 import BeautifulSoup
from PIL import Image

# --- SETUP ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# APRIL 2026 STABLE MODELS (Confirmed active on v1beta)
# gemini-2.5-flash is currently the recommended stable path for high-volume apps.
MODEL_NAME = 'gemini-2.5-flash' 

if "messages" not in st.session_state: st.session_state.messages = []
if "specs" not in st.session_state: st.session_state.specs = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# --- SEARCH TOOLS ---
def get_raw_search_data(query):
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={query}+pinball"
        res = requests.get(url, timeout=10).json()
        if "items" in res:
            return "\n".join([f"{i['title']}: {i['snippet']}" for i in res['items'][:5]])
        return "No specific web results found."
    except Exception as e:
        return f"Search error: {str(e)}"

def get_wiki_context(system, is_em):
    try:
        path = "EM_Repair" if is_em else system.replace(" ", "_")
        r = requests.get(f"https://pinwiki.com/wiki/index.php/{path}", timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        content = soup.find(id="mw-content-text")
        return content.get_text()[:1500] if content else "Wiki page empty."
    except: return "Wiki unavailable."

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
    if st.button("🆕 New Repair Case"):
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
            # Use 2.5-flash for both ID and Diagnosis to minimize API handshakes
            try:
                model = genai.GenerativeModel(MODEL_NAME)
            except:
                # Absolute emergency fallback string
                model = genai.GenerativeModel('gemini-pro-latest')

            # STEP 1: Identification (Powered by Web Search)
            if not st.session_state.specs:
                search_evidence = get_raw_search_data(prompt)
                id_p = f"Analyze: {search_evidence}\nIdentify machine for: '{prompt}'. Return JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":true/false, \"game\":\"\"}}"
                
                try:
                    res = model.generate_content(id_p)
                    clean_res = res.text.strip().replace('```json', '').replace('```', '')
                    st.session_state.specs = json.loads(clean_res)
                except Exception as e:
                    # Generic fallback so the app continues
                    st.session_state.specs = {"mfg":"Unknown", "system":"General", "is_em":True, "game":"Pinball Machine"}
            
            spec = st.session_state.specs
            
            # STEP 2: Specific Data Gathering
            search_evidence = get_raw_search_data(f"{spec['mfg']} {spec['game']} {prompt}")
            wiki = get_wiki_context(spec['system'], spec['is_em'])
            
            # STEP 3: Final Diagnostic
            hist = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            ctx = f"Machine: {spec['game']} ({spec['mfg']})\nSearch: {search_evidence}\nWiki: {wiki}\nIssue: {prompt}\nHistory: {hist}"
            
            inputs = [ctx]
            if up: inputs.append(Image.open(up))
            
            try:
                ans_res = model.generate_content(inputs)
                st.markdown(ans_res.text)
                st.session_state.messages.append({"role": "assistant", "content": ans_res.text})
            except Exception as e:
                st.error(f"AI Handshake failed with {MODEL_NAME}. Error: {str(e)}")
