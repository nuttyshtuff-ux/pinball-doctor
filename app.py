import streamlit as st
import google.generativeai as genai
import requests, json, os
from bs4 import BeautifulSoup
from PIL import Image

# --- SETUP ---
st.set_page_config(page_title="Doctor Pinball", page_icon="🩺")
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Stable 2026 Model
MODEL_NAME = 'gemini-2.5-flash' 

# Session States
if "messages" not in st.session_state: st.session_state.messages = []
if "specs" not in st.session_state: st.session_state.specs = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# --- SEARCH TOOLS ---
def get_raw_search_data(query, is_modern_stern=False):
    search_query = f"{query} pinball"
    if is_modern_stern:
        search_query = f"{query} Stern Pinball Tech School official troubleshooting"
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
        if "Data East" in system: path = "Data_East/Sega"
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
    up_files = st.file_uploader(
        "Upload Photos, Manuals, or Schematics", 
        type=['png', 'jpg', 'jpeg', 'pdf'],
        accept_multiple_files=True
    )
    
    if st.button("🆕 New Repair Case"):
        st.session_state.messages, st.session_state.specs = [], None
        st.rerun()

# --- MAIN ---
st.title("🩺 Doctor Pinball")
spec = st.session_state.specs

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

placeholder = "Enter Mfg + Game (e.g. Williams Triple Action)"

if prompt := st.chat_input(placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("DOCTOR PINBALL IS CONSULTING..."):
            model = genai.GenerativeModel(MODEL_NAME)
            
            if not spec:
                search_evidence = get_raw_search_data(prompt)
                id_p = f"Identify: '{prompt}'. Evidence: {search_evidence}. Return JSON ONLY: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
                try:
                    res = model.generate_content(id_p)
                    clean_res = res.text.strip().replace('```json', '').replace('```', '')
                    spec = json.loads(clean_res)
                    st.session_state.specs = spec
                except:
                    spec = {"mfg":"Unknown", "system":"General", "is_em":True, "game":"Pinball"}
                    st.session_state.specs = spec

            system_name = spec.get('system', '').upper()
            is_modern_stern = (spec.get('mfg', '').lower() == 'stern') and any(s in system_name for s in ["SPIKE", "SAM", "WHITESTAR"])
            
            technical_data = get_raw_search_data(f"{spec['mfg']} {spec['game']} {prompt}", is_modern_stern=is_modern_stern)
            wiki = get_wiki_context(spec['system'], spec['is_em'])
            
            # THE CORRECTED PROMPT BLOCK
            ctx = f"""
            You are a Senior Pinball Bench Specialist with 30+ years experience in board-level repair and restoration.
            TONE: Professional, analytical, and neutral. 
            RULES:
            1. NO judgment, NO sarcasm, and NO metaphors. 
            2. If the user provides a pin number, wire color, or measurement, ACCEPT it as the ground truth.
            3. Cite specific locations (Page, Connector ID, or Schematic Quadrant).
            4. If a schematic trace is ambiguous/blurry, state it and suggest a continuity test.
            5. Use technical shorthand: IDC, MPU, J-Plugs, IC pins, MOSFET.

            Machine: {spec['mfg']} {spec['game']}
            System: {spec['system']}
            Wiki: {wiki}
            Search Data: {technical_data}
            """
            
            inputs = [ctx, prompt]
            if up_files:
                for up in up_files:
                    if up.type == "application/pdf":
                        inputs.append({"mime_type": "application/pdf", "data": up.getvalue()})
                    else:
                        inputs.append(Image.open(up))
            
            try:
                ans = model.generate_content(inputs).text
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
            except Exception as e:
                st.error(f"Handshake failed. Error: {str(e)}")
