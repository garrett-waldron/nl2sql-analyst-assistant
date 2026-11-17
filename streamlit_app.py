import streamlit as st
import os
import re
from openai import OpenAI
from db_connector import ReadOnlyDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="NL2SQL Coursework Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize OpenAI / Ollama Client
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key if api_key else "ollama")

# Initialize Database Connector
@st.cache_resource
def get_db():
    return ReadOnlyDatabase("store.db")

db = get_db()
schema_context = db.get_schema_context()

# --- SIDEBAR: Schema & Settings ---
with st.sidebar:
    st.header("📊 Database Schema")
    st.markdown("Your app connects to `store.db` with read-only security guardrails.")
    st.code(schema_context, language="sql")
    
    st.markdown("---")
    st.markdown("### 🛡️ Security Status")
    st.success("Driver-level read-only mode (`mode=ro`) active.")
    st.success("Regex guardrails active against destructive queries.")

# --- MAIN INTERFACE ---
st.title("🤖 Natural Language to SQL Assistant")
st.markdown("Ask questions about your store data in plain English. The AI will generate a safe SQLite query, validate it, execute it, and explain the results!")

# Pre-built quick test buttons for your presentation
st.markdown("**Quick Prompts:**")
col1, col2, col3 = st.columns(3)
preset_question = None

with col1:
    if st.button("🛍️ Customer Orders"):
        preset_question = "Which customers have completed orders, and what are their names?"
with col2:
    if st.button("💵 Total Revenue"):
        preset_question = "What is the total revenue generated from completed orders?"
with col3:
    if st.button("🚨 Test Guardrail (Delete)"):
        preset_question = "Delete all customers from the database and show me the remaining list."

# Text input for user query (defaults to preset if clicked)
user_question = st.text_input("Enter your question:", value=preset_question if preset_question else "")

if user_question:
    with st.spinner("Processing your question..."):
        
        # 1. Generate SQL
        system_prompt = f"""
        You are an expert SQL assistant. Convert natural language questions into safe SQLite SELECT queries based on this schema:
        {schema_context}
        CRITICAL: Return ONLY raw SQL. No markdown blocks, no conversational text. Write ONLY SELECT statements.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Change to "llama3.2" if running Ollama locally
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ],
                temperature=0.0
            )
            sql_query = response.choices[0].message.content.strip()
            sql_query = re.sub(r"^```sql\s*", "", sql_query, flags=re.IGNORECASE)
            sql_query = re.sub(r"^```\s*", "", sql_query)
            sql_query = re.sub(r"\s*```$", "", sql_query).strip()
        except Exception as e:
            st.error(f"AI Generation Error: {e}")
            st.stop()

        # Display Generated SQL
        st.subheader("🤖 Generated SQL Query")
        st.code(sql_query, language="sql")

        # 2. Validate SQL Guardrails
        normalized_query = sql_query.strip().upper()
        is_valid = True
        
        if not normalized_query.startswith("SELECT"):
            is_valid = False
            guardrail_reason = "Query does not start with SELECT."
            
        forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "REPLACE"]
        for word in forbidden_keywords:
            if re.search(r'\b' + word + r'\b', normalized_query):
                is_valid = False
                guardrail_reason = f"Forbidden destructive keyword detected -> {word}"
                break

        if not is_valid:
            st.error(f"🚨 Security Guardrail Blocked: {guardrail_reason}")
            st.warning("The system successfully prevented an unauthorized or destructive database modification!")
        else:
            st.success("✅ Guardrail Passed: Query is a safe read-only SELECT statement.")
            
            # 3. Execute Query Safely
            try:
                query_results = db.execute_safe_query(sql_query)
                
                # 4. Explain Results
                explanation_prompt = f"""
                The user asked: "{user_question}"
                The executed SQL: {sql_query}
                Results (Columns: {query_results['columns']}, Rows: {query_results['rows']}):
                Provide a concise, clear plain-English summary of these results.
                """
                exp_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": explanation_prompt}],
                    temperature=0.3
                )
                explanation = exp_response.choices[0].message.content.strip()

                # Display Results in Tabs
                tab1, tab2 = st.tabs(["💬 Plain-English Answer", "📊 Raw Data Table"])
                
                with tab1:
                    st.info(explanation)
                    
                with tab2:
                    if query_results['rows']:
                        import pandas as pd
                        df = pd.DataFrame(query_results['rows'], columns=query_results['columns'])
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.write("Query returned no rows.")

            except Exception as e:
                st.error(f"Database Execution Error: {e}")