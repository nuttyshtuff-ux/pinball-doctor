import streamlit as st
import google.generativeai as genai
import requests, json, os
from bs4 import BeautifulSoup
from PIL import Image

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Doctor Pinball", page_icon="🩺")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in secrets.")
    st.stop()

MODEL_NAME = 'gemini-2.5-flash' 

if "messages" not in st.session_state: st.session_state.messages = []
if "specs" not in st.session_state: st.session_state.specs = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# --- 2. IMPROVED TOOLS ---

def get_raw_search_data(query, mfg, sys):
    search_query = f"{mfg} {query} pinball schematic manual arcade-museum ipdb pinside"
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={search_query}"
        res = requests.get(url, timeout=5).json()
        if "items" in res:
            return "\n".join([f"VERIFIED SOURCE: {i['title']}\nVERIFIED URL: {i['link']}\nCONTENT: {i['snippet']}\n---" for i in res['items'][:4]])
    except:
        pass
    return "No verified external links found via search."

def get_wiki_context(system, is_em):
    wiki_map = {
        "WPC": "Williams_WPC", "SYSTEM 11": "Williams_System_11", "SYSTEM 3": "Gottlieb_System_3",
        "SYSTEM 80": "Gottlieb_System_80", "WHITESTAR": "Sega/Stern_White_Star", "SAM": "Stern_SAM",
        "SPIKE": "Stern_SPIKE", "6803": "Bally_6803", "DATA EAST": "Data_East/Sega"
    }
    
    sys_upper = system.upper()
    path = system.replace(" ", "_")
    for key, official_path in wiki_map.items():
        if key in sys_upper:
            path = official_path
            break
    if is_em: path = "EM_Repair"

    full_url = f"https://pinwiki.com/wiki/index.php/{path}"
    try:
        r = requests.get(full_url, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            content = soup.find(id="mw-content-text")
            return content.get_text()[:2000], full_url
    except:
        pass
    return "Specific PinWiki entry unavailable.", full_url

# --- 3. LOGIN GATE ---
if not st.session_state.authenticated:
    st.title("🩺 Doctor Pinball")
    pw = st.text_input("Tech Password", type="password")
    if st.button("Login"):
        if pw == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("Repair Bench")
    up_files = st.file_uploader("Upload Manuals/Photos", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
    if st.button("🆕 New Repair Case"):
        st.session_state.messages, st.session_state.specs = [], None
        st.rerun()

# --- 5. MAIN INTERFACE ---
st.title("🩺 Doctor Pinball")
spec = st.session_state.specs

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 6. CHAT LOGIC ---
if prompt := st.chat_input("Enter Mfg + Game"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("CONSULTING DOCUMENTATION..."):
            model = genai.GenerativeModel(MODEL_NAME)
            
            # --- INITIALIZE SCOPE TO PREVENT NameError ---
            tech_data = "Pending search..."
            wiki_text = "Pending wiki..."
            verified_wiki_url = "https://pinwiki.com"
            
            # 1. Identification
            if not spec:
                id_p = f"Identify: '{prompt}'. Return JSON ONLY: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
                try:
                    res = model.generate_content(id_p)
                    raw_text = res.text.strip().replace('```json', '').replace('```', '')
                    spec = json.loads(raw_text)
                except:
                    spec = {"mfg": "Unknown", "system": "General", "is_em": False, "game": prompt}
                st.session_state.specs = spec

            # 2. Re-assign identifiers safely
            m_val = st.session_state.specs.get('mfg', 'Unknown')
            s_val = st.session_state.specs.get('system', 'General')
            g_val = st.session_state.specs.get('game', 'Game')
            em_val = st.session_state.specs.get('is_em', False)

            # 3. Data Retrieval
            tech_data = get_raw_search_data(prompt, m_val, s_val)
            wiki_text, verified_wiki_url = get_wiki_context(s_val, em_val)
            
            # 4. Specialist Prompt
            ctx = f"""
            You are a Senior Pinball Specialist (30+ years experience).
            Machine: {m_val} {g_val} ({s_val})
            
            STRICT LINKING RULES:
            1. Provide clickable Markdown links for ALL search data: [Title](URL).
            2. DO NOT invent URLs for Arcade-Museum or IPDB. ONLY use 'VERIFIED URL' links from the Search Data.
            3. Cite the verified PinWiki URL: {verified_wiki_url}
            4. Credit community members by name if they appear in search snippets.

            TECHNICAL RULES:
            1. User-provided data is GROUND TRUTH.
            2. Cite specific manual pages/quadrants.
            3. Admit if visuals are blurry; recommend a multimeter test.
            4. TONE: Professional, neutral, no sarcasm.
            
            CONTEXT:
            Wiki: {wiki_text}
            Search Data: {tech_data}
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
                st.error(f"Diagnostic failed: {str(e)}")
