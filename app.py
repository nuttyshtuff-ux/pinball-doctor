import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

# Use the model that has been working for you
MODEL_NAME = 'gemini-1.5-flash'

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- AI HELPERS ---
def identify_machine(user_input):
    model = genai.GenerativeModel(MODEL_NAME)
    id_prompt = f"Identify pinball machine for: '{user_input}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
    
    try:
        res = model.generate_content(id_prompt)
        # Clean the output of markdown code blocks
        clean_text = res.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_text)
        
        # Defensive check: ensure all keys exist or provide defaults
        return {
            "mfg": data.get("mfg", "Unknown Mfg"),
            "system": data.get("system", "Unknown System"),
            "is_em": data.get("is_em", False),
            "game": data.get("game", "Unknown Game")
        }
    except Exception as e:
        # If parsing fails entirely, return a safe fallback
        return {"mfg": "Unknown", "system": "General", "is_em": False, "game": "Unknown Machine"}

def get_wiki_data(specs):
    wiki_path = "EM_Repair" if specs.get('is_em') else specs.get('system', '').replace(" ", "_")
    try:
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        if res.status_code == 200:
            return BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:2500]
    except: pass
    return "Technical guides unavailable."

# --- UI ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")

# Sidebar for reset
if st.session_state.specs:
    if st.sidebar.button("New Repair Case"):
        st.session_state.clear()
        st.rerun()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Single Combined Input Box
if prompt := st.chat_input("Machine and Issue..."):
    # Store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Diagnosing..."):
            # 1. Identify machine if first time
            if not st.session_state.specs:
                st.session_state.specs = identify_machine(prompt)
            
            specs = st.session_state.specs
            
            # Show the caption safely using .get() just in case
            st.caption(f"🔧 Repairing: **{specs.get('game')}** | {specs.get('mfg')} {specs.get('system')}")
            
            # 2. Get Knowledge Base
            context = get_wiki_data(specs)
            
            # 3. Construct Repair Logic
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
            full_prompt = f"""
            You are Pinball Doctor. 
            Machine: {specs['game']} ({specs['mfg']} {specs['system']})
            Context: {context}
            History: {history}
            
            New Input: {prompt}
            
            Provide a technical diagnosis and repair steps.
            """
            
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"API Error: {e}")
