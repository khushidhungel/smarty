import streamlit as st
import requests
import json
import bcrypt
import google.generativeai as genai
from streamlit_option_menu import option_menu
import streamlit_authenticator as stauth
import time
import requests

# ---- CUSTOM THEME ----
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #1e1e2f, #2e2e48);
            color: white;
        }
        section[data-testid="stSidebar"] {
            background-color: #181828;
        }
        .stTextInput textarea, .stTextArea textarea {
            background-color: #2c2c3e !important;
            color: #ffffff !important;
            border-radius: 10px;
            border: 1px solid #444 !important;
        }
        .stButton button {
            background-color: #6a5acd;
            color: white;
            padding: 0.7rem 1.2rem;
            border-radius: 10px;
            border: none;
            transition: 0.2s;
        }
        .stButton button:hover {
            background-color: #8377ff;
        }
        h1, h2, h3, h4 {
            color: #dcdcff !important;
            text-shadow: 0px 0px 15px rgba(180,180,255,0.4);
        }
        .stAlert {
            border-radius: 10px !important;
        }
         /* ⭐ Highlight the UniProt ID label */
        label[for="protein_id"] {
            color: #ffcb6b !important;
            font-weight: 600 !important;
            font-size: 1.05rem !important;
            text-shadow: 0px 0px 6px rgba(255,200,100,0.4);
        }
        /* ⭐ Highlight ALL Streamlit input labels */
.css-16idsys, .css-1kyxreq, label {
    color: #ffcb6b !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    text-shadow: 0px 0px 6px rgba(255,200,100,0.4);
        }


    </style>
""", unsafe_allow_html=True)

# ==============================
# CONFIGURATION
# ==============================
st.set_page_config(page_title="🧬 BioAI Explorer", page_icon="🧬", layout="wide")

# ---- NICE HEADER (paste it RIGHT HERE) ----
st.markdown("""
    <div style='text-align:center; padding: 20px 0;'>
        <h1 style='font-size: 3rem;'>🧬 BioAI Explorer</h1>
        <p style='font-size: 1.2rem; color: #cfcfff;'>AI-powered sequence analysis & BLAST search</p>
    </div>
""", unsafe_allow_html=True)

genai_key = None
try:
    # safe access (st.secrets raises if no valid TOML found)
    if "api" in st.secrets and "gemini_key" in st.secrets["api"]:
        genai_key = st.secrets["api"]["gemini_key"]
        #st.info(f"Gemini key found — length={len(genai_key)}; masked={genai_key[:4]}...{genai_key[-4:]}")
        try:
            genai.configure(api_key=genai_key)
            #st.success("genai.configure succeeded (key loaded).")
        except Exception as e:
            st.error("Failed to configure Gemini client: " + str(e))
            genai_key = None
    else:
        st.warning("Gemini API key not present in st.secrets.")
except Exception as e:
    st.warning("Could not read secrets.toml: " + str(e))
    genai_key = None
 #blast function    
def run_blast(sequence, program="blastp", database="nr"):
    url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
    params = {
        "CMD": "Put",
        "PROGRAM": program,
        "DATABASE": database,
        "QUERY": sequence,
        "FORMAT_TYPE": "JSON2_Summary"
    }
    r = requests.post(url, data=params)
    r.raise_for_status()
    
    # Get RID (search ID)
    rid_line = [line for line in r.text.splitlines() if "RID =" in line]
    if not rid_line:
        raise ValueError("Failed to get BLAST RID")
    rid = rid_line[0].split("=")[1].strip()
    
    # Wait until BLAST finishes
    while True:
        time.sleep(5)
        r2 = requests.get(url, params={"CMD": "Get", "RID": rid, "FORMAT_TYPE": "JSON2_Summary"})
        if "Status=WAITING" in r2.text:
            continue
        elif "Status=FAILED" in r2.text:
            raise ValueError("BLAST search failed")
        else:
            break
    
    return r2.json()
    
# ==============================
# LOAD OR INITIALIZE USER DATA
# ==============================
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

users = load_users()

# ==============================
# SIGNUP FUNCTION
# ==============================
def signup(email, password):
    if email in users:
        return False, "User already exists!"
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[email] = hashed_pw
    save_users(users)
    return True, "Account created successfully!"

# ==============================
# LOGIN FUNCTION
# ==============================
def login(email, password):
    if email not in users:
        return False, "No account found!"
    stored_hash = users[email].encode()
    if bcrypt.checkpw(password.encode(), stored_hash):
        return True, "Login successful!"
    return False, "Invalid password!"

# ==============================
# AUTH SECTION
# ==============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if not st.session_state.logged_in:
    st.title("🧬 BioAI Explorer Login Portal")

    tab1, tab2 = st.tabs(["🔑 Login", "🧾 Sign Up"])

    with tab1:
        email = st.text_input("📧 Email", key="login_email")
        password = st.text_input("🔒 Password", type="password", key="login_pw")
        if st.button("Login"):
            success, msg = login(email, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.user = email
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with tab2:
        new_email = st.text_input("📨 Create Email", key="signup_email")
        new_password = st.text_input("🔐 Create Password", type="password", key="signup_pw")
        if st.button("Sign Up"):
            success, msg = signup(new_email, new_password)
            if success:
                st.success(msg)
            else:
                st.error(msg)

else:
    # ==============================
    # MAIN DASHBOARD
    # ==============================
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/1/1e/Protein_structure.png", width='stretch')
        st.title(f"Welcome, {st.session_state.user.split('@')[0].capitalize()} 👋")
        choice = option_menu(
            "Navigation",
            ["Home", "Protein Explorer","BLAST Search", "AI Assistant", "Logout"],
            icons=["house", "dna", "robot", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
        )

    if choice == "Home":
        st.title("🧬 BioAI Explorer")
        st.markdown("""
        Welcome to **BioAI Explorer** — your smart AI companion for bioinformatics exploration.

        🔹 **Search Proteins** from UniProt  
        🔹 **Ask AI** about biological terms or drug/herbal insights  
        🔹 **Visualize** sequences, IDs, and functions  

        ---
        """)

    elif choice == "Protein Explorer":
        st.header("🔍 Explore Protein Data from UniProt")
        protein_id = st.text_input("Enter a UniProt ID (e.g., P69905 for Hemoglobin alpha):", key="protein_id")
        if st.button("Fetch Data", key="fetch_uniprot"):
            if not protein_id:
                st.warning("Please enter a UniProt ID.")
            else:
                def fetch_uniprot_json(protein_id, retries=3, timeout=15):
                    session = requests.Session()
                    url = f"https://rest.uniprot.org/uniprotkb/{protein_id}.json"
                    backoff = 1
                    for attempt in range(1, retries + 1):
                        try:
                            resp = session.get(url, timeout=timeout)
                            resp.raise_for_status()
                            return resp.json()
                        except requests.exceptions.Timeout:
                            if attempt == retries:
                                raise
                            time.sleep(backoff)
                            backoff *= 2
                        except requests.exceptions.HTTPError as e:
                            # return None for 404 (not found) so caller can show a friendly message
                            if resp.status_code == 404:
                                return None
                            raise
                        except requests.exceptions.RequestException:
                            if attempt == retries:
                                raise
                            time.sleep(backoff)
                            backoff *= 2

                try:
                    data = fetch_uniprot_json(protein_id, retries=3, timeout=15)
                except requests.exceptions.Timeout:
                    st.error("UniProt request timed out after multiple attempts. Try again or increase timeout.")
                except Exception as e:
                    st.error(f"Request failed: {e}")
                else:
                    if not data:
                        st.error("Protein not found (404). Check the UniProt ID.")
                    else:
                        # safe nested extraction
                        protein_name = (data.get("proteinDescription", {}) \
                                           .get("recommendedName", {}) \
                                           .get("fullName", {}) \
                                           .get("value")) or "Name not available"
                        organism = (data.get("organism", {}) \
                                        .get("scientificName")) or "Organism not available"
                        seq = (data.get("sequence", {}) \
                                  .get("value"))
                        length = (data.get("sequence", {}) \
                                    .get("length")) or (len(seq) if seq else "N/A")
                        preview = (seq[:300] + "...") if seq and len(seq) > 300 else (seq or "Sequence not available")
                        st.subheader("Protein Information:")
                        st.json({
                            "Protein Name": protein_name,
                            "Organism": organism,
                            "Length": length,
                            "Sequence (preview)": preview,
                            "Raw JSON (partial)": {k: data.get(k) for k in ("accession", "dbReferences", "comments") if k in data}
                    })

    elif choice == "AI Assistant":
        st.header("🤖 BioAI Chat Assistant")
        query = st.text_area("Ask anything about bioinformatics, herbs, or proteins:", key="ai_query")
        if st.button("Ask AI", key="ask_ai"):
            if not query.strip():
                st.warning("Please enter a question.")
            elif not genai_key:
                st.error("Gemini API key not configured.")
            else:
                try:
                    # Use gemini-2.5-flash (latest supported model)
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    resp = model.generate_content(query)
                    # Extract text safely
                    text = getattr(resp, "text", None)
                    if not text and isinstance(resp, dict):
                        text = (resp.get("candidates") or [{}])[0].get("content") or resp.get("output") or resp.get("text")
                    st.write(text or "No text returned from model.")
                except Exception as e:
                    st.error(f"AI call failed: {e}")
                    
    elif choice == "BLAST Search":
        st.header("🔬 BLAST Sequence Search")
    
        seq_input = st.text_area("Enter your sequence:", height=150)
        program = st.selectbox("BLAST Program", ["blastn", "blastp", "blastx", "tblastn", "tblastx"])
        database = st.text_input("Database", "nr")  # default NCBI database

        if st.button("Run BLAST"):
            if not seq_input.strip():
                st.warning("Please enter a sequence.")
            else:
                with st.spinner("Running BLAST..."):
                    try:
                        results = run_blast(seq_input, program, database)
                        hits = results.get("BlastOutput2", [{}])[0].get("report", {}).get("results", {}).get("search", {}).get("hits", [])
                        if hits:
                            table = []
                            for h in hits[:10]:  # top 10 hits
                                accession = h["description"][0]["accession"]
                                desc = h["description"][0]["title"]
                                score = h["hsps"][0]["bit_score"]
                                evalue = h["hsps"][0]["evalue"]
                                table.append({"Accession": accession, "Description": desc, "Score": score, "E-value": evalue})
                            st.table(table)
                        else:
                            st.info("No hits found.")
                    except Exception as e:
                        st.error(f"BLAST failed: {e}")


    elif choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.user = None
        st.success("You have been logged out successfully!")
        st.rerun()









