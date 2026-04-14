import streamlit as st
import google.generativeai as genai
import requests, json, os
from bs4 import BeautifulSoup
from PIL import Image

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Doctor Pinball", page_icon="🩺")

# Ensure API Key exists before proceeding
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in secrets.")
    st.stop()

MODEL_NAME = 'gemini-2.5-flash' 

# Initialize Session States
if "messages" not in st.session_state: st.session_state.messages = []
if "specs" not in st.session_state: st.session_state.specs = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# --- 2. ROBUST TOOLS ---
def get_raw_search_data(query, mfg, sys):
    search_query = f"{mfg} {sys} {query} pinball repair"
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={search_query}"
        res = requests.get(url, timeout=5).json()
        if "items" in res:
            return "\n".join([f"SOURCE: {i['title']}\nURL: {i['link']}\nCONTENT: {i['snippet']}\n---" for i in res['items'][:3]])
    except:
        pass
    return "No additional community data found via search."

def get_wiki_context(system, is_em):
    # Try multiple path variations to avoid 404s
    path = system.replace(" ", "_")
    try:
        r = requests.get(f"https://pinwiki.com/wiki/index.php/{path}", timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            content = soup.find(id="mw-content-text")
            return content.get_text()[:2000] if content else "Wiki content found but empty."
    except:
        pass
    return "Specific PinWiki entry unavailable."

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

# Restore Specs from session
spec = st.session_state.specs

# Display History
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 6. CHAT LOGIC ---
if prompt := st.chat_input("Enter Mfg + Game (e.g. Bally Addams Family)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("ANALYZING..."):
            model = genai.GenerativeModel(MODEL_NAME)
            
            # A. Identification Safety
            if not spec:
                id_p = f"Identify the pinball machine: '{prompt}'. Return JSON ONLY: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
                try:
                    res = model.generate_content(id_p)
                    # Robust JSON extraction
                    raw_text = res.text.strip().replace('```json', '').replace('```', '')
                    spec = json.loads(raw_text)
                except:
                    spec = {"mfg": "Unknown", "system": "General", "is_em": False, "game": prompt}
                st.session_state.specs = spec

            # B. Data Gathering
            m_val = spec.get('mfg', 'Unknown')
            s_val = spec.get('system', 'General')
            g_val = spec.get('game', 'Game')
            em_val = spec.get('is_em', False)

            tech_data = get_raw_search_data(prompt, m_val, s_val)
            wiki_data = get_wiki_context(s_val, em_val)
            
            # C. Specialist Prompt
            ctx = f"""
            You are a Senior Pinball Specialist (30+ years experience).
            Machine: {m_val} {g_val} ({s_val})
            
            RULES:
            1. GROUND TRUTH: If the user provides a pin # or measurement, it is FACT.
            2. CITATIONS: You MUST provide clickable links for search data: [Title](URL).
            3. TECHNICAL: Cite manual pages/quadrants. Admit if visuals are blurry.
            4. TONE: Professional, neutral, no sarcasm.
            
            CONTEXT:
            Wiki: {wiki_data}
            Community: {tech_data}
            """
            
            # D. Generate Response
            inputs = [ctx, prompt]
            if up_files:
                for up in up_files:
                    if up.type == "application/pdf":
                        inputs.append({"mime_type": "application/pdf", "data": up.getvalue()})
                    else:
                        inputs.append(Image.open(up))
            
            try:
                response = model.generate_content(inputs)
                ans = response.text
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
            except Exception as e:
                st.error(f"Diagnostic failed: {str(e)}")
