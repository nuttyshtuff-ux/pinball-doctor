import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from PIL import Image
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
API_KEY = st.secrets["GOOGLE_API_KEY"]
CSE_CX = st.secrets["SEARCH_ENGINE_ID"]
genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

# Initializing Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- UI: SIDEBAR (Password & Persistent Controls) ---
with st.sidebar:
    st.header("🔐 Tech Access")
    
    # Check if already authenticated to skip password field
    if not st.session_state.authenticated:
        tech_pass = st.text_input("Enter Tech Password", type="password")
        if tech_pass == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        elif tech_pass != "":
            st.error("Incorrect Password")
    
    # If authenticated, show the tools
    if st.session_state.authenticated:
        st.success("Authorized Tech")
        st.header("Visual Aid")
        uploaded_file = st.file_uploader("Upload Schematic or Photo", type=['png', 'jpg', 'jpeg'])
        
        st.divider()
        if st.button("🆕 New Repair Case"):
            # We reset the game data but keep authenticated = True
            st.session_state.messages = []
            st.session_state.specs = None
            st.rerun()
            
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

# --- MAIN APP LOGIC ---
if st.session_state.authenticated:
    st.title("🩺 Pinball Doctor")
    
    if not st.session_state.specs:
        st.info("What's the machine and the issue? (e.g. 'Cactus Jack's - sound is distorted')")
    else:
        s = st.session_state.specs
        st.caption(f"🔧 Repairing: **{s.get('game')}** | {s.get('mfg')} {s.get('system')}")

    # Display Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input(""):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Searching Pinside Tech & PinWiki..."):
                # Your existing process_request logic goes here...
                # (Assuming you are pasting the process_request function from v7.6)
                img = Image.open(uploaded_file) if uploaded_file else None
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
                # For brevity, I'm calling your existing function logic
                # answer, specs = process_request(prompt, history, st.session_state.specs, image=img)
                # st.markdown(answer)
                # st.session_state.messages.append({"role": "assistant", "content": answer})
                st.write("Diagnostic Engine active...") 

else:
    st.title("🩺 Pinball Doctor")
    st.warning("Please enter the Tech Password in the sidebar to access the diagnostic tools.")
