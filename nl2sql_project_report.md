NL2SQL Streamlit Application: Architecture, Development, and Engineering Report
1. Executive Summary
This document serves as an exhaustive technical record of the development, security hardening, cloud deployment, and advanced feature engineering implemented for the Natural Language to SQL (NL2SQL) Coursework Assistant. The application bridges the gap between non-technical end-users and structured relational databases by translating natural language queries into safe, executable SQLite statements using Large Language Models (LLMs), with runtime security guardrails and dynamic CSV ingestion.

2. Core Architecture & Tech Stack
Frontend & UI Framework: Streamlit (configured in wide layout with multi-tab data presentation and sidebar profiling).
Backend & Database Engine: Python, Pandas, and SQLite (supporting both persistent file-based databases like store.db and dynamic in-memory databases sqlite3.connect(":memory:") for user-uploaded datasets).
AI & LLM Integration: OpenAI API (gpt-4o-mini) configured via environment variables and Streamlit Cloud Secrets.
Version Control & Deployment: Git, GitHub, and Streamlit Community Cloud.

3. Security & Safety Implementation
Because NL2SQL applications expose database structures to generative AI, ensuring data integrity and preventing destructive operations is paramount. Two layers of security were implemented:
Driver-Level Read-Only Enforcement (mode=ro):
Implemented via a custom ReadOnlyDatabase wrapper around standard SQLite connections to guarantee that baseline databases cannot be modified at the file driver level.
Regex-Based Guardrail Engine:
Before any AI-generated SQL query is executed against a database, it passes through a validation filter:
Prefix Verification: Ensures the normalized query strictly begins with the SELECT keyword.
Keyword Blacklist: Scans for prohibited destructive commands using word boundaries (\b), blocking keywords including DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, and REPLACE.

4. Key Challenges, Debugging, and Iterative Solutions
Challenge 1: Authentication & Local vs. Cloud Environment Discrepancies
Problem: The application functioned correctly when executed locally via terminal with Ollama (client = OpenAI(api_key="ollama")), but threw 401 Unauthorized errors when deployed to Streamlit Cloud or when transitioning to OpenAI's cloud models.
Solution: Decoupled local environment variables (.env) from cloud deployment secrets. Configured Streamlit Cloud's native TOML Secrets manager to securely inject OPENAI_API_KEY without hardcoding sensitive credentials into version-controlled source files.
Challenge 2: Schema Introspection & Zero-Result Query Fails
Problem: When users uploaded custom CSV files (e.g., historical NYC childcare inspection datasets), the LLM had no prior knowledge of specific column names or exact text case formatting (e.g., guessing 'Hospital' when the dataset stored records under different categories or lacked them entirely), resulting in syntactically valid queries that returned zero rows (None).
Solution:
Dynamic Schema Introspection: Programmatically queried sqlite_master and executed PRAGMA table_info() on the active connection.
Sample Data Injection: Enhanced schema extraction to include the first 3 actual rows of the uploaded DataFrame as a text preview inside the LLM system prompt. This taught the model real-world data formatting and naming conventions.
Whitespace Stripping: Automatically sanitized CSV column headers using .str.strip() to eliminate hidden leading/trailing spaces.
Challenge 3: Syntax & Type Casting Issues in SQLite
Problem: Spaces in column names (e.g., "Age Range") caused SQLite syntax errors when unquoted, and CSV imports treating numeric metrics as text broke aggregate functions like AVG().
Solution: Enforced strict system prompt rules requiring the LLM to wrap all column and table names in double quotes ("Column Name") and explicitly cast data types when performing math (CAST("Metric" AS REAL)).

5. Advanced Enhancements for Presentation Impact
To elevate the application into an A+ coursework presentation piece, several high-impact features were integrated:
Dynamic In-Memory CSV Upload:
Utilizes Pandas and sqlite3.connect(":memory:") to instantly spin up temporary, queryable SQL tables from any user-dropped CSV file.
Self-Healing LLM Execution Loop:
Implemented a two-attempt execution wrapper. If a generated query throws a SQLite execution error, the exact error message and schema context are fed back to gpt-4o-mini in a secondary prompt to auto-correct the SQL syntax before re-validating guardrails and executing.
Automated Data Profiler Sidebar:
Automatically inspects uploaded datasets, identifies categorical columns with low cardinality, and displays unique values in the sidebar so users can construct accurate filter queries.
Data Visualization & Export:
Added auto-generated bar charts (st.bar_chart) and a one-click CSV export utility (st.download_button) inside results tabs to turn raw tabular data into actionable business intelligence dashboards.

6. Conclusion
The resulting application is a secure, resilient, and self-contained NL2SQL assistant capable of seamlessly switching between persistent store databases and arbitrary user-uploaded CSV files. It successfully combines strict security guardrails, intelligent prompt engineering, and self-healing execution loops into a polished Streamlit interface.
