import streamlit as st
import os
import re
import pandas as pd
import sqlite3
from openai import OpenAI
from db_connector import ReadOnlyDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page Configuration (MUST be the very first Streamlit command)
st.set_page_config(
    page_title="NL2SQL Coursework Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize OpenAI / Ollama Client
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key if api_key else "ollama")

# --- SIDEBAR: Data Source Upload ---
st.sidebar.header("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload a custom CSV dataset", type=["csv"])

# Helper function to extract schema + sample rows from an arbitrary sqlite connection
def get_connection_schema(connection, df):
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    schema_info = []
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [col[1] for col in cursor.fetchall()]
        schema_info.append(f"Table: {table_name}, Columns: {', '.join(columns)}")
    
    # Add actual sample rows so the LLM sees real formatting & values!
    sample_data = "\nSample Data (First 3 rows):\n" + df.head(3).to_string(index=False)
    
    return "\n".join(schema_info) + "\n" + sample_data

# --- HANDLE DATABASE CONNECTION & DYNAMIC SCHEMA ---
if uploaded_file is not None:
    # Read uploaded CSV into pandas and strip hidden whitespace from headers
    df_upload = pd.read_csv(uploaded_file)
    df_upload.columns = df_upload.columns.str.strip()
    
    # Create an in-memory SQLite database for the custom CSV
    conn = sqlite3.connect(":memory:")
    df_upload.to_sql("user_data", conn, index=False, if_exists="replace")
    st.sidebar.success("Custom dataset loaded into memory!")
    
    # Get schema context with sample rows included
    schema_context = get_connection_schema(conn, df_upload)
    active_db_source = conn

    # Suggested Columns & Quick Profiler in sidebar
    st.sidebar.markdown("### 💡 Suggested Columns")
    st.sidebar.markdown(f"Available: `{', '.join(df_upload.columns)}`")
    
    st.sidebar.markdown("### 🔍 Dataset Quick Profiler")
    for col in df_upload.select_dtypes(include=['object', 'category']).columns:
        unique_vals = df_upload[col].unique()
        if len(unique_vals) < 10:  # Only show if there are a reasonable number of categories
            st.sidebar.text(f"{col}: {list(unique_vals)}")

else:
    # Fallback to default store.db via your custom class
    @st.cache_resource
    def get_db():
        return ReadOnlyDatabase("store.db")
    
    db_obj = get_db()
    schema_context = db_obj.get_schema_context()
    active_db_source = db_obj

# --- SIDEBAR: Schema & Settings ---
with st.sidebar:
    st.header("📊 Database Schema")
    if uploaded_file is not None:
        st.markdown("Connected to **Custom Uploaded CSV** (`user_data` table).")
    else:
        st.markdown("Connected to `store.db` with read-only security guardrails.")
    st.code(schema_context, language="sql")
    
    st.markdown("---")
    st.markdown("### 🛡️ Security Status")
    st.success("Driver-level / In-memory security active.")
    st.success("Regex guardrails active against destructive queries.")

# --- MAIN INTERFACE ---
st.title("🤖 Natural Language to SQL Assistant")
st.markdown("Ask questions about your store data or uploaded CSV in plain English. The AI will generate a safe SQLite query, validate it, execute it, and explain the results!")

# Pre-built quick test buttons (Only show if using default store.db)
if uploaded_file is None:
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
else:
    preset_question = None
    st.info("💡 Tip: Since you uploaded a custom CSV, check the sidebar quick profiler for valid filter terms like facility types!")

# Text input for user query
user_question = st.text_input("Enter your question:", value=preset_question if preset_question else "")

# --- SELF-HEALING RETRY FUNCTION ---
def run_sql_with_retry(sql_query, active_source, is_csv, user_q, schema_ctx):
    for attempt in range(2):  # Initial try + 1 auto-fix retry
        try:
            if is_csv:
                cursor = active_source.cursor()
                cursor.execute(sql_query)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return {"columns": columns, "rows": rows}, sql_query
            else:
                return active_source.execute_safe_query(sql_query), sql_query
                
        except Exception as db_error:
            if attempt == 0:
                # Ask the LLM to fix its own SQL using the exact SQLite error message
                fix_prompt = f"""
                The following SQLite query failed:
                Query: {sql_query}
                Error: {db_error}
                Schema: {schema_ctx}
                User Question: {user_q}
                
                Fix the SQLite SELECT query so it executes without errors. Return ONLY raw SQL.
                """
                fix_resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": fix_prompt}],
                    temperature=0.0
                )
                sql_query = fix_resp.choices[0].message.content.strip()
                sql_query = re.sub(r"^```sql\s*|^```\s*|\s*```\$", "", sql_query, flags=re.IGNORECASE).strip()
                
                # Re-validate guardrails on the fixed query!
                if not sql_query.upper().startswith("SELECT") or any(
                    re.search(r'\b' + w + r'\b', sql_query.upper()) 
                    for w in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "REPLACE"]
                ):
                    raise ValueError("Self-healed query violated read-only guardrails.")
            else:
                raise db_error

if user_question:
    with st.spinner("Processing your question..."):
        
        # 1. Generate SQL with Advanced Rules
        system_prompt = f"""
        You are an expert SQLite data analyst. Convert natural language questions into safe, accurate SQLite SELECT queries based on this schema:
        {schema_context}
        
        CRITICAL RULES:
        1. Return ONLY raw SQL. No markdown blocks, no conversational text, and no trailing semicolons. Write ONLY SELECT statements.
        2. ALWAYS wrap every column name and table name in double quotes (e.g., SELECT "Column Name" FROM "user_data") to prevent syntax errors from spaces or special characters.
        3. FUZZY TEXT MATCHING: Never use exact '=' matches for string filters unless matching an ID or exact code. Always use case-insensitive LIKE with wildcards (e.g., WHERE LOWER("Facility Type") LIKE '%hospital%') so partial or differently capitalized values still match.
        4. NULL & BLANK HANDLING: Exclude NULLs and empty strings when calculating averages, minimums, or grouping.
        5. SAFE MATH & TYPE CASTING: Cast numeric columns explicitly when aggregating (e.g., AVG(CAST("Violation Rate" AS REAL))) and use NULLIF to prevent division-by-zero errors.
        6. RESULT LIMITS: If the user asks for "all", "list", or doesn't specify a limit on a raw row query, append LIMIT 50 so the UI doesn't freeze on massive CSVs.
        7. SQLITE DIALECT ONLY: Only use valid SQLite functions.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
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
            
            # 3. Execute Query Safely with Self-Healing Retry Loop
            try:
                is_csv_source = (uploaded_file is not None)
                query_results, final_executed_sql = run_sql_with_retry(
                    sql_query, active_db_source, is_csv_source, user_question, schema_context
                )
                
                # 4. Explain Results
                explanation_prompt = f"""
                The user asked: "{user_question}"
                The executed SQL: {final_executed_sql}
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
                tab1, tab2 = st.tabs(["💬 Plain-English Answer", "📊 Raw Data Table & Visuals"])
                
                with tab1:
                    st.info(explanation)
                    
                with tab2:
                    if query_results['rows']:
                        df_res = pd.DataFrame(query_results['rows'], columns=query_results['columns'])
                        st.dataframe(df_res, use_container_width=True)
                        
                        # CSV Download Button
                        csv_data = df_res.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Results as CSV",
                            data=csv_data,
                            file_name="query_results.csv",
                            mime="text/csv",
                        )
                        
                        # Auto-Chart Visualization
                        if len(df_res.columns) >= 2:
                            st.markdown("### Quick Visualization")
                            try:
                                st.bar_chart(df_res.set_index(df_res.columns[0]))
                            except Exception:
                                st.info("Chart generation skipped (requires numerical data in columns).")
                    else:
                        st.warning("⚠️ The query executed successfully but returned 0 rows.")
                        st.info("💡 **Tip:** Check the sidebar quick profiler to see the exact text values used in your CSV categories!")

            except Exception as e:
                st.error(f"Database Execution Error: {e}")