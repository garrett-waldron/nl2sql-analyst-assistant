#for handling the read-only security connection
import sqlite3

class ReadOnlyDatabase:
    def __init__(self, db_path="store.db"):
        # URI format with ?mode=ro enforces strict read-only access at the engine level
        self.db_uri = f"file:{db_path}?mode=ro"

    def get_connection(self):
        return sqlite3.connect(self.db_uri, uri=True)

    def get_schema_context(self) -> str:
        """Extracts CREATE TABLE statements to feed into the LLM system prompt."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%';
        """)
        tables = cursor.fetchall()
        conn.close()

        # Combine all DDL statements into a clean string for the AI prompt
        schema_str = "\n\n".join(table[0] for table in tables if table[0])
        return schema_str

    def execute_safe_query(self, sql_query: str):
        """Executes a query against the read-only connection."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sql_query)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            return {"columns": columns, "rows": rows}
        finally:
            conn.close()

# Quick verification test
if __name__ == "__main__":
    db = ReadOnlyDatabase("store.db")
    
    print("--- EXTRACTED SCHEMA FOR LLM PROMPT ---")
    print(db.get_schema_context())
    
    print("\n--- TESTING READ-ONLY GUARDRAIL ---")
    try:
        db.execute_safe_query("DELETE FROM customers WHERE customer_id = 1;")
    except sqlite3.OperationalError as e:
        print(f"Guardrail worked! Blocked write attempt with error: {e}")