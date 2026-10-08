try:
    from .database import get_db_connection
except ImportError:  # Direct execution from the backend directory.
    from database import get_db_connection


def create_tables():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Farmers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            village TEXT NOT NULL,
            phone TEXT
        )
    """)

    # Resources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            owner_id INTEGER,
            village TEXT NOT NULL,
            price_per_hour REAL DEFAULT 0,
            available INTEGER DEFAULT 1,
            FOREIGN KEY (owner_id) REFERENCES farmers(id)
        )
    """)

    # Bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            hours REAL DEFAULT 1,
            total_cost REAL DEFAULT 0,
            status TEXT DEFAULT 'confirmed',
            FOREIGN KEY (farmer_id) REFERENCES farmers(id),
            FOREIGN KEY (resource_id) REFERENCES resources(id)
        )
    """)

    connection.commit()
    connection.close()
