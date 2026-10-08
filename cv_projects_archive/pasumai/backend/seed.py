from database import get_db_connection
from models import create_tables

# Make sure tables exist
create_tables()

# Connect to database
connection = get_db_connection()
cursor = connection.cursor()

# Sample farmers
farmers = [
    ("Ravi Kumar", "Kattankulathur", "9876543210"),
    ("Priya Devi", "Potheri", "9876543211"),
    ("Arun Kumar", "Maraimalai Nagar", "9876543212"),
    ("Meena R", "Kattankulathur", "9876543213"),
    ("Suresh B", "Potheri", "9876543214"),
    ("Lakshmi S", "Maraimalai Nagar", "9876543215"),
]

# Insert farmers
cursor.executemany("""
    INSERT INTO farmers (name, village, phone)
    VALUES (?, ?, ?)
""", farmers)

# Save changes
connection.commit()
connection.close()

print("Farmer data inserted successfully!")
