import streamlit as st
import google.generativeai as genai
import requests
import json
from bs4 import BeautifulSoup

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Doctor Pinball", page_icon="🩺")

# --- API CONFIG ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in secrets.")
    st.stop()

MODEL_NAME = "gemini-2.5-flash"
SEARCH_ENGINE_ID = st.secrets.get("SEARCH_ENGINE_ID", None)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages =
