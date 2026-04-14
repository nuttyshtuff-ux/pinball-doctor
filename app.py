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

# Optional: Custom Search Engine ID for deep search
SEARCH_ENGINE_ID = st.secrets.get("SEARCH_ENGINE_ID", None)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- 2. DEEP TOOLS ---

def scrape_thread_content(url: str) -> str:
    """Scrape limited content from allowed pinball forums/wiki pages."""
    try:
        allowed_domains = ["pinside.com", "pinwiki.com", "arcade-museum.com"]
        if not any(domain in url for domain in allowed_domains):
            return ""

        headers = {"User-Agent": "DoctorPinballDiagnosticBot/1.2 (Educational Use)"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            return ""

        soup = BeautifulSoup(r.text, "html.parser")

        # Pinside forum posts
        if "pinside.com" in url:
            posts = soup.find_all("div", class_="forum-post-content")
            if not posts:
                return ""
            return "\n".join([p.get_text(strip=True)[:600] for p in posts[:8]])

        # Fallback: generic text
        return soup.get_text()[:2000]
    except Exception:
        return ""


def get_wiki_context(system: str, is_em: bool):
    """Fetch relevant PinWiki content based on system and EM flag."""
    wiki_map = {
        "-35 MPU": "Bally/Stern",
        "-17 MPU": "Bally/Stern",
        "AS-2518": "Bally/Stern",
        "MPU-100": "Bally/Stern",
        "MPU-200": "Bally/Stern",
        "WPC": "Williams_WPC",
        "SYSTEM 11": "Williams_System_11",
        "SYSTEM 3": "Gottlieb_System_3",
        "WHITESTAR": "Sega/Stern_White_Star",
        "SAM": "Stern_SAM",
        "SPIKE": "Stern_SPIKE",
    }

    sys_upper = (system or "").upper()
    path = (system or "General").replace(" ", "_")

    for key, official_path in wiki_map.items():
        if key in sys_upper:
            path = official_path
            break

    if is_em:
        path = "EM_Repair"

    full_url = f"https://pinwiki.com/wiki/index.php/{path}"

    try:
        r = requests.get(full_url, timeout=5)
        if r.status_code != 200:
            return "Wiki entry unavailable.", full_url

        soup = BeautifulSoup(r.text, "html.parser")
        content_div = soup.find(id="mw-content-text")
        if not content_div:
            return "Wiki entry unavailable.", full_url

        text = content_div.get_text(separator="\n", strip=True)
        return text[:2500], full_url
    except Exception:
        return "Wiki entry unavailable.", full_url


def get_deep_search_data(query: str, mfg: str, sys: str) -> str:
    """Use Google Custom Search to find relevant Pinside threads and scrape them."""
    if not SEARCH_ENGINE_ID:
        return "Deep search disabled (missing SEARCH_ENGINE_ID)."

    search_terms = f"{mfg} {sys} {query} pinball repair board troubleshooting site:pinside.com"
    try:
        url = (
            "https://www.googleapis.com/customsearch/v1"
            f"?key={st.secrets['GOOGLE_API_KEY']}"
            f"&cx={SEARCH_ENGINE_ID}"
            f"&q={requests.utils.quote(search_terms)}"
        )
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return "No verified deep search data found."

        data = res.json()
        if "items" not in data:
            return "No verified deep search data found."

        results = []
        for item in data["items"][:3]:
            link = item.get("link", "")
            title = item.get("title", "Untitled")
            content = scrape_thread_content(link)
            results.append(
                f"SOURCE: {title}\nURL: {link}\nDEEP DATA: {content}\n---"
            )

        return "\n".join(results) if results else "No verified deep search data found."
    except Exception:
        return "No verified deep search data found."


def identify_machine(prompt: str):
    """Ask Gemini to identify mfg/system/game in strict JSON."""
    model = genai.GenerativeModel(
        MODEL_NAME,
        generation_config={"response_mime_type": "application/json"},
    )

    id_prompt = {
        "role": "user",
        "parts": [
            (
                "Identify the pinball machine and system from this text.\n"
                "Return ONLY valid JSON with this exact schema:\n"
                "{"
                "\"mfg\": \"\", "
                "\"system\": \"\", "
                "\"is_em\": false, "
                "\"game\": \"\""
                "}"
                "\n\nText: "
                f"\"{prompt}\""
            )
        ],
    }

    try:
        res = model.generate_content(id_prompt)
        specs = json.loads(res.text)
        # Basic sanity defaults
        specs.setdefault("mfg", "Unknown")
        specs.setdefault("system", "General")
        specs.setdefault("is_em", False)
        specs.setdefault("game", prompt)
        return specs
    except Exception:
        return {"mfg": "Unknown", "system": "General", "is_em": False, "game": prompt}


# --- 3. UI RENDERING ---
st.title("🩺 Doctor Pinball")

# --- AUTH ---
if not st.session_state.authenticated:
    pw = st.text_input("Tech Password", type="password")
    if st.button("Login"):
        if pw == st.secrets.get("TECH_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Repair Bench")
    up_files = st.file_uploader(
        "Upload Manuals/Photos",
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=True,
    )
    if st.button("🆕 New Repair Case"):
        st.session_state.messages = []
        st.session_state.specs = None
        st.rerun()

# --- DISPLAY CHAT HISTORY ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. CHAT LOGIC ---
prompt = st.chat_input("Describe the issue (include Mfg + Game + System if known)")
if prompt:
    # Log user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("CONSULTING DOCUMENTATION..."):
            model = genai.GenerativeModel(MODEL_NAME)

            # --- SAFE IDENTIFICATION ---
            if not st.session_state.specs:
                st.session_state.specs = identify_machine(prompt)

            spec = st.session_state.specs

            # --- SAFE DATA GATHERING ---
            wiki_text, wiki_url = get_wiki_context(
                spec.get("system", "General"), spec.get("is_em", False)
            )
            deep_data = get_deep_search_data(
                prompt, spec.get("mfg", ""), spec.get("system", "")
            )

            # --- CONTEXT BUILDING ---
            ctx = f"""
You are a Senior Pinball Specialist.

Machine: {spec.get('mfg')} {spec.get('game')} ({spec.get('system')})

STRICT CITATION RULE:
- You MUST credit Pinside/Wiki sources found in the data.
- Provide clickable links: [Title](URL).

CONTEXT:
Wiki (PinWiki): {wiki_text}
(Source: {wiki_url})

Community (Pinside / others):
{deep_data}
"""

            # --- INPUTS FOR GEMINI ---
            inputs = [ctx, prompt]

            # Attach uploaded files correctly
            if up_files:
                for up in up_files:
                    file_bytes = up.read()
                    if not file_bytes:
                        continue

                    if up.type == "application/pdf":
                        inputs.append(
                            {
                                "mime_type": "application/pdf",
                                "data": file_bytes,
                            }
                        )
                    else:
                        # Assume image
                        inputs.append(
                            {
                                "mime_type": up.type,
                                "data": file_bytes,
                            }
                        )

            # --- GENERATE ANSWER ---
            try:
                ans = model.generate_content(inputs).text
                st.markdown(ans)
                st.session_state.messages.append(
                    {"role": "assistant", "content": ans}
                )
            except Exception as e:
                st.error(f"Diagnostic Error: {str(e)}")
