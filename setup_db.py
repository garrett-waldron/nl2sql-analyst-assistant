#for building your SQLite database schema and sample data
import sqlite3

def create_sample_database(db_path="store.db"):
    # Connect to SQLite (this automatically creates the store.db file)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Create Tables
    cursor.executescript("""
    DROP TABLE IF EXISTS order_items;
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS customers;

    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        country TEXT NOT NULL,
        signup_date DATE NOT NULL
    );

    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL
    );

    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        order_date DATE NOT NULL,
        status TEXT CHECK(status IN ('completed', 'pending', 'cancelled')) NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)

    # 2. Add Sample Data
    customers = [
        ("Alice Johnson", "alice@example.com", "USA", "2025-01-15"),
        ("Bob Smith", "bob@example.com", "Canada", "2025-02-20"),
        ("Charlie Davis", "charlie@example.com", "UK", "2025-03-10"),
        ("Diana Prince", "diana@example.com", "USA", "2025-04-05"),
    ]
    cursor.executemany(
        "INSERT INTO customers (full_name, email, country, signup_date) VALUES (?, ?, ?, ?)",
        customers
    )

    products = [
        ("Mechanical Keyboard", "Electronics", 120.00),
        ("Ergonomic Mouse", "Electronics", 65.00),
        ("Standing Desk Mat", "Office", 45.00),
        ("USB-C Hub", "Accessories", 35.00),
    ]
    cursor.executemany(
        "INSERT INTO products (product_name, category, unit_price) VALUES (?, ?, ?)",
        products
    )

    orders = [
        (1, "2025-05-01", "completed"),
        (1, "2025-06-12", "completed"),
        (2, "2025-06-15", "cancelled"),
        (3, "2025-07-01", "completed"),
    ]
    cursor.executemany(
        "INSERT INTO orders (customer_id, order_date, status) VALUES (?, ?, ?)",
        orders
    )

    order_items = [
        (1, 1, 1, 120.00),
        (1, 2, 1, 65.00),
        (2, 3, 2, 90.00),
        (3, 1, 1, 120.00),
        (4, 4, 3, 105.00),
    ]
    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, subtotal) VALUES (?, ?, ?, ?)",
        order_items
    )

    conn.commit()
    conn.close()
    print("SUCCESS! Your database 'store.db' has been created.")

if __name__ == "__main__":
    create_sample_database()