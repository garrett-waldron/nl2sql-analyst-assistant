#for running your LLM pipeline and validation checks
import os
import re
import sqlite3
from openai import OpenAI
from db_connector import ReadOnlyDatabase
from dotenv import load_dotenv
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class NL2SQLAssistant:
    def __init__(self, db_path="store.db"):
        self.db = ReadOnlyDatabase(db_path)
        self.schema_context = self.db.get_schema_context()

    def generate_sql(self, user_question: str) -> str:
        """Prompts the LLM to convert plain English into an SQLite SELECT query."""
        system_prompt = f"""
        You are an expert SQL assistant. Your job is to convert natural language questions into safe, accurate SQLite SELECT queries based on the database schema below.
        
        CRITICAL RULES:
        1. Return ONLY the raw SQL query. Do not include markdown code blocks (like ```sql), conversational text, or explanations.
        2. Write ONLY `SELECT` statements. Never write INSERT, UPDATE, DELETE, DROP, or ALTER statements.
        3. Use the exact table names and column names provided in the schema.

        DATABASE SCHEMA:
        {self.schema_context}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0.0
        )
        
        # Clean up any accidental markdown formatting from the LLM
        sql_query = response.choices[0].message.content.strip()
        sql_query = re.sub(r"^```sql\s*", "", sql_query, flags=re.IGNORECASE)
        sql_query = re.sub(r"^```\s*", "", sql_query)
        sql_query = re.sub(r"\s*```$", "", sql_query)
        return sql_query.strip()

    def validate_sql(self, sql_query: str) -> bool:
        """Security guardrail: Ensures the query is strictly a read-only SELECT statement."""
        normalized_query = sql_query.strip().upper()
        
        # Guardrail 1: Must start with SELECT
        if not normalized_query.startswith("SELECT"):
            print("🚨 Guardrail Blocked: Query does not start with SELECT.")
            return False
            
        # Guardrail 2: Check for forbidden destructive keywords anywhere
        forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "REPLACE"]
        for word in forbidden_keywords:
            if re.search(r'\b' + word + r'\b', normalized_query):
                print(f"🚨 Guardrail Blocked: Forbidden keyword detected -> {word}")
                return False
                
        return True

    def explain_results(self, user_question: str, sql_query: str, results: dict) -> str:
        """Asks the LLM to translate raw database rows into a friendly, plain-English summary."""
        explanation_prompt = f"""
        The user asked: "{user_question}"
        The system executed this SQL query: 
        {sql_query}
        
        The query returned these results (Columns: {results['columns']}, Rows: {results['rows']}):
        
        Provide a concise, clear plain-English explanation or summary of these results for the user.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": explanation_prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    def run_pipeline(self, user_question: str):
        print(f"\n👤 User Question: \"{user_question}\"")
        
        # Step A: Generate SQL
        sql = self.generate_sql(user_question)
        print(f"🤖 Generated SQL: {sql}")
        
        # Step B: Validate SQL Guardrails
        if not self.validate_sql(sql):
            print("❌ Query rejected by validation guardrails.")
            return
        
        # Step C: Execute Query safely against read-only DB
        try:
            query_results = self.db.execute_safe_query(sql)
            print(f"📊 Raw Results: {query_results['rows']}")
        except Exception as e:
            print(f"❌ Execution Error: {e}")
            return
            
        # Step D: Explain Results
        explanation = self.explain_results(user_question, sql, query_results)
        print(f"💬 Plain-English Explanation:\n{explanation}")

# --- Test the Full Pipeline ---
if __name__ == "__main__":
    assistant = NL2SQLAssistant("store.db")
    
    # Test case 1: Standard analytical query
    assistant.run_pipeline("Which customers have completed orders, and what are their names?")
    
    # Test case 2: Attempting a malicious/destructive injection prompt to test guardrails
    assistant.run_pipeline("Delete all customers from the database and show me the remaining list.")