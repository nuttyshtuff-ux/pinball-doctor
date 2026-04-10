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
genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- UI: SECURE TECH ACCESS ---
with st.sidebar:
    st.header("🔐 Tech Access")
    tech_pass = st.text_input("Enter Tech Password", type="password")
    
    # We now check against the Secret, not a hardcoded string
    if tech_pass == st.secrets["TECH_PASSWORD"]:
        st.success("Access Granted")
        st.header("Visual Aid")
        uploaded_file = st.file_uploader("Upload Schematic/Photo", type=['png', 'jpg', 'jpeg'])
        if st.session_state.specs:
            if st.button("New Repair Case"):
                st.session_state.clear()
                st.rerun()
    elif tech_pass != "":
        st.error("Incorrect Password")

# --- MAIN APP LOGIC ---
if tech_pass == st.secrets.get("TECH_PASSWORD"):
    # ... (All your existing diagnosis and chat logic goes here) ...
    st.title("🩺 Pinball Doctor")
    # [Rest of the code remains exactly the same]
else:
    st.title("🩺 Pinball Doctor")
    st.warning("Please enter the Tech Password in the sidebar to begin diagnosis.")
