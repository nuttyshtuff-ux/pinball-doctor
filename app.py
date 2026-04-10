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
MODEL_NAME = 'gemini-3-flash-preview' # 2026 stable alias

# --- PERSISTENCE: Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [] # Stores chat history
if "specs" not in st.session_state:
    st.session_state.specs = None # Stores machine info

# --- HELPER: Machine Identification ---
def identify_machine(game_name):
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"Identify pinball mfg and system for '{game_name}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":bool}}"
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_text)
    except:
        return {"mfg": "Unknown", "system": "General", "is_em": False}

# --- UI SETUP ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")

# Sidebar: Start New Repair
with st.sidebar:
    if st.button("New Repair Case"):
        st.session_state.messages = []
        st.session_state.specs = None
        st.rerun()

# 1. First time setup: Ask for the machine name
if not st.session_state.specs:
    game_input = st.text_input("Which machine are we looking at today?", placeholder="e.g. Black Knight 2000")
    if st.button("Start Diagnosis"):
        st.session_state.specs = identify_machine(game_input)
        st.session_state.game_name = game_input
        st.rerun()

# 2. Ongoing Diagnosis (The Chat)
else:
    specs = st.session_state.specs
    st.info(f"Diagnosing: **{st.session_state.game_name}** ({specs['mfg']} {specs['system']})")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Describe the issue or update me on the last fix..."):
        # Add user message to state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Doctor Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Construct conversation context for the AI
                history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                
                full_query = f"""
                You are Pinball Doctor. 
                Machine Specs: {specs}
                Conversation History:
                {history_context}
                
                If the user says a fix didn't work, apologize and suggest the next logical step (e.g. check ground wires, transistors, or relay gapping). 
                If they uncover new symptoms, incorporate them into the new diagnosis.
                """
                
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    response = model.generate_content(full_query)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"API Error: {e}")
