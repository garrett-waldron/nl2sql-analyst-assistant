Markdown
# 🤖 Natural-Language-to-SQL (NL2SQL) Assistant

An intelligent, secure Python pipeline and Streamlit web application that translates plain-English questions into safe, read-only SQLite `SELECT` queries. Built as an AI coursework project emphasizing **defense-in-depth security guardrails**, relational data retrieval, and clean user experience.

---

## 🌟 Key Features

- **Natural Language Translation:** Leverages advanced LLMs (`gpt-4o-mini`) to convert conversational questions into precise SQL syntax.
- **Dual-Layer Security Guardrails:** 
  - *Driver-Level Enforcement:* Connects to SQLite using URI filename parameters (`mode=ro`) to hard-block any filesystem write attempts.
  - *Application-Level Validation:* Regex-based guardrails enforce that queries start strictly with `SELECT` and scan for forbidden destructive keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, etc.).
- **Interactive Web Interface:** A polished Streamlit dashboard featuring live schema inspection, security status badges, pre-built test queries, and tabbed outputs for raw pandas data tables and plain-English summaries.
- **Flexible AI Backend:** Fully compatible with both cloud-based OpenAI API keys and local, zero-cost offline models via Ollama.

---

## 🏗️ System Architecture & Pipeline

[ User Question ]
│
▼
[ LLM Generation (OpenAI) ]
│
▼
[ Security Validator (Regex Guardrails) ] ──(Fail)──> 🚨 Blocked & Logged
│ (Pass)
▼
[ Read-Only Database Connector (mode=ro) ]
│
▼
[ Result Summarizer & Streamlit UI ]


---

## 📂 Project Structure

```text
nl2sql-project/
│
├── store.db                 # Relational SQLite database (customers, products, orders, items)
├── db_connector.py          # Secure read-only database connection handler
├── app.py                   # Core backend pipeline and validation logic
├── streamlit_app.py         # Interactive Streamlit web interface
├── requirements.txt         # Project dependencies
├── .env                     # Local environment variables (API keys - gitignored)
└── README.md                # Project documentation
🚀 Getting Started & Installation
1. Clone the Repository
Bash
git clone [https://github.com/YOUR-USERNAME/nl2sql-coursework-assistant.git](https://github.com/YOUR-USERNAME/nl2sql-coursework-assistant.git)
cd nl2sql-coursework-assistant
2. Install Dependencies
Bash
pip install openai streamlit python-dotenv pandas
3. Configure Your Environment
Create a .env file in the project root and add your OpenAI API key (if using cloud AI):

Code snippet
OPENAI_API_KEY=your-api-key-here
(Note: If running offline for free, ensure Ollama is installed and running llama3.2 locally).

4. Run the Web Application
Launch the interactive Streamlit dashboard using Python's module launcher:

Bash
python -m streamlit run streamlit_app.py
🛡️ Security Implementation
Security was a primary design focus of this project. To prevent prompt injection and unauthorized database manipulation, the system implements:

URI-Based Read-Only Connection: The database connector establishes connections using file:store.db?mode=ro&uri=true. Even if a malicious prompt successfully bypasses application filters, the SQLite engine and filesystem level reject write operations.

Strict Keyword Blacklisting: validate_sql() checks query strings against boundary-checked regex patterns for destructive operations (DELETE, DROP, UPDATE, TRUNCATE, ALTER, CREATE).

💡 Example Queries to Test
"Which customers have completed orders, and what are their names?"

"What is the total revenue generated from completed orders?"

"Delete all customers from the database and show me the remaining list." (Demonstrates security guardrail interception)