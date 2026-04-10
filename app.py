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

# Using the 2026 'stable alias' to prevent 404 errors
MODEL_NAME = 'gemini-3-flash-preview' 

# --- STEP 1: THE CLASSIFIER ---
def identify_machine(game_name):
    """Hidden logic that replaces the sidebar dropdowns."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""
    Act as a pinball historian. For the game "{game_name}", identify:
    1. Manufacturer (e.g., Williams, Stern, Bally)
    2. System Architecture (e.g., WPC, SPIKE 2, System 11)
    3. Technology (Is it 'EM' or 'Solid State'?)
    
    Return ONLY a JSON object: {{"mfg": "Name", "system": "System", "is_em": true/false}}
    """
    try:
        response = model.generate_content(prompt)
        # Cleaning the AI output to ensure valid JSON
        clean_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_text)
    except:
        # Fallback if AI struggles with a weird name
        return {"mfg": "Unknown", "system": "General", "is_em": False}

# --- STEP 2: THE SCRAPER ---
def get_wiki_data(specs):
    wiki_path = "EM_Repair" if specs['is_em'] else specs['system'].replace(" ", "_")
    try:
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        return BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:3000]
    except:
        return "Manual data unavailable."

# --- UI SETUP (No Sidebar!) ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")
st.info("No more dropdowns. Just tell me what's broken.")

game_input = st.text_input("Machine Name", placeholder="e.g., Addams Family, 1974 Fireball, or Foo Fighters")
issue_input = st.text_area("Diagnosis Request", value="Describe the issue")

if st.button("Fix It"):
    if not game_input or issue_input == "Describe the issue":
        st.warning("I need both the game name and the issue to help!")
    else:
        with st.spinner("Identifying machine specs..."):
            specs = identify_machine(game_input)
            st.caption(f"**Detected:** {specs['mfg']} {specs['system']} ({'EM' if specs['is_em'] else 'Solid State'})")
            
        with st.spinner("Analyzing repair databases..."):
            context = get_wiki_data(specs)
            
            # Final Expert Diagnosis
            prompt = f"""
            You are Pinball Doctor. 
            Machine: {game_input} ({specs['mfg']} {specs['system']})
            Issue: {issue_input}
            Context: {context}
            
            Provide:
            1. Likely Cause
            2. Step-by-Step Repair
            3. Required Parts
            """
            
            try:
                doctor = genai.GenerativeModel(MODEL_NAME)
                result = doctor.generate_content(prompt)
                st.success(f"Diagnosis for {game_input} Ready")
                st.markdown(result.text)
            except Exception as e:
                st.error(f"API Error: {e}")
