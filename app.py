# --- UPDATED SEARCH TOOL (v1.1.11) ---
def get_raw_search_data(query, mfg, sys):
    # Specifically target schematics in the search query
    search_query = f"{mfg} {query} pinball schematic manual arcade-museum ipdb"
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={search_query}"
        res = requests.get(url, timeout=5).json()
        if "items" in res:
            # We strictly pair the Title with the LIVE URL found by Google
            return "\n".join([f"VERIFIED SOURCE: {i['title']}\nVERIFIED URL: {i['link']}\nCONTENT: {i['snippet']}\n---" for i in res['items'][:4]])
    except:
        pass
    return "No verified external links found."

# --- UPDATED PROMPT (The "Anti-Hallucination" Rule) ---
ctx = f"""
...
STRICT LINKING RULE:
1. You are FORBIDDEN from inventing or 'guessing' URLs for IPDB or Arcade-Museum.
2. Only use the 'VERIFIED URL' links provided in the Search Data section below.
3. If a schematic link is not in the Search Data, tell the user to check the 'Documentation' section on IPDB manually.
...
SEARCH DATA:
{tech_data}
"""
