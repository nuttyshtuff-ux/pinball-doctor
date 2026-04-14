# --- UPDATED SEARCH TOOL (Captures URLs) ---
def get_raw_search_data(query, is_modern_stern=False):
    search_query = f"{query} pinball"
    if is_modern_stern:
        search_query = f"{query} Stern Pinball Tech School official troubleshooting"
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={search_query}"
        res = requests.get(url, timeout=10).json()
        if "items" in res:
            # We bundle the Title, Link, and Snippet so the AI has the full 'citation'
            return "\n".join([f"TITLE: {i['title']}\nLINK: {i['link']}\nINFO: {i['snippet']}\n---" for i in res['items'][:5]])
        return "No specific community data found."
    except: return "Search unavailable."

# --- UPDATED PROMPT (Forces Links) ---
ctx = f"""
You are a Senior Pinball Bench Specialist. 
TONE: Professional, analytical, neutral.

CITATION & LINK RULE:
1. When using advice from the search data, you MUST provide a clickable Markdown link to the source.
2. Format it clearly at the end of your advice, e.g., "Source: [Thread Title](URL)".
3. If multiple sources are used, list them as 'References.'

TECHNICAL RULES:
1. Accept user measurements/pins as GROUND TRUTH.
2. Cite manual page numbers/quadrants.
3. No sarcasm or judgment.

Machine: {spec['mfg']} {spec['game']}
System: {spec['system']}
Wiki: {wiki}
Search Data: {technical_data}
"""
