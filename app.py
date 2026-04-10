import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# 2026 Model Check: Using 'gemini-3-flash-preview' as it is the current 
# stable alias to avoid the 404s you saw with 1.5 versions.
MODEL_NAME = 'gemini-3-flash-preview'

if not API_KEY:
    st.error("Missing API Key in .env!")
    st.stop()

genai.configure(api_key=API_KEY)

def get_pinwiki_data(category, system):
    """Enhanced scraper for both SS (Solid State) and EM (Electromechanical)."""
    if category == "Electromechanical (EM)":
        url = "https://pinwiki.com/wiki/index.php/EM_Repair"
    else:
        # Formats the system name for the Wiki URL (e.g., Williams_WPC)
        formatted_system = system.replace(" ", "_")
        url = f"https://pinwiki.com/wiki/index.php/{formatted_system}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find(id="mw-content-text")
            return content.get_text()[:6000] # Increased context window
        return f"Note: Direct PinWiki guide for {system} not found. AI will use general knowledge."
    except:
        return "Scraper encountered an issue. AI will proceed with internal training data."

# --- UI SETUP ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor v2.0")

with st.sidebar:
    st.header("Machine Specs")
    
    # Combined category for easier navigation
    game_type = st.radio("Technology", ["Solid State (SS)", "Electromechanical (EM)"])
    
    if game_type == "Solid State (SS)":
        system = st.selectbox("System Architecture", [
            "Williams WPC", "Stern SPIKE 1", "Stern SPIKE 2", 
            "Stern SAM", "Stern Whitestar", "Stern MPU-200",
            "Bally 6803", "Data East", "Gottlieb System 1"
        ])
    else:
        system = st.selectbox("Manufacturer (EM Era)", ["Gottlieb", "Williams", "Bally", "Chicago Coin"])

    model_name = st.text_input("Game Name", "Addams Family")

st.markdown(f"### Diagnosing: **{model_name}**")
issue = st.text_area("What is the machine doing (or not doing)?", placeholder="Example: The score motor keeps spinning and won't start a game...")

if st.button("Run Diagnostic"):
    with st.spinner("Analyzing mechanical relays and circuit logic..."):
        # Fetch knowledge base
        context = get_pinwiki_data(game_type, system)
        
        # Expert Persona Prompt
        prompt = f"""
        You are 'Pinball Doctor'. You have 40 years of experience.
        
        CONTEXT DATA:
        {context}
        
        USER PROBLEM:
        Technology: {game_type}
        System: {system}
        Model: {model_name}
        Symptom: {issue}
        
        INSTRUCTIONS:
        1. If EM: Focus on relay cleaning, score motor 'home' switches, and steppers.
        2. If SS: Focus on MPU LEDs, voltages, and connectors.
        3. Provide: Diagnosis, Step-by-Step Fix, and Parts needed.
        """
        
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            st.success("Analysis Complete")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"API Error: {e}")
