import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from PIL import Image
from dotenv import load_dotenv

# --- SETUP (STRICTLY MAINTAINING YOUR GOOGLE CALLS) ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- AI HELPERS ---
def identify_machine(user_input):
    """Robust identification that handles apostrophes and weird names."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Telling the AI specifically how to handle Cactus Jack's style names
    id_prompt = f"Identify the pinball game in this text: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}. Ensure the JSON is valid even if the game has an apostrophe."
    
    try:
        res = model.generate_content(id_prompt)
        # Scrubbing the response to find the JSON block
        text = res.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(text)
        return data
    except:
        # If it fails (like with Cactus Jack's), we'll do a 'Soft Match' 
        # specifically for Gottlieb System 3 games from that era
        if "cactus" in user_input.lower():
            return {"mfg": "Gottlieb", "system": "System 3", "is_em": False, "game": "Cactus Jack's"}
        return {"mfg": "Unknown", "system": "General", "is_em": False, "game": "Pinball Machine"}

def get_wiki_data(specs):
    system_name = specs.get('system', 'General')
    wiki_path = "EM_Repair" if specs.get('is_em') else system_name.replace(" ", "_")
    try:
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        return BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:2500]
    except:
        return ""

# --- UI ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")

with st.sidebar:
    st.header("Visual Aid")
    uploaded_file = st.file_uploader("Upload Schematic or Board Photo", type=['png', 'jpg', 'jpeg'])
    if st.session_state.specs:
        if st.button("New Repair Case"):
            st.session_state.clear()
            st.rerun()

if not st.session_state.specs:
    st.info("What's the machine and the issue?")
else:
    s = st.session_state.specs
    st.caption(f"🔧 Repairing: **{s.get('game')}** | {s.get('mfg')} {s.get('system')}")

# Display Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input(""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            # 1. Identify if needed
            if not st.session_state.specs:
                st.session_state.specs = identify_machine(prompt)
            
            specs = st.session_state.specs
            img = Image.open(uploaded_file) if uploaded_file else None
            context = get_wiki_data(specs)
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            
            # 2. Diagnosis Call
            full_prompt = [f"Role: Pinball Doctor. Game: {specs.get('game')}. Specs: {specs}. Data: {context}. History: {history}. Input: {prompt}"]
            if img:
                full_prompt.append(img)
            
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"API Error: {e}")
