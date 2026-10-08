from database import get_db_connection

connection = get_db_connection()
cursor = connection.cursor()

resources = [
    # Tractors
    ("Mahindra Tractor", "tractor", 1, "Kattankulathur", 800),
    ("Swaraj Tractor", "tractor", 2, "Potheri", 750),
    ("John Deere Tractor", "tractor", 3, "Maraimalai Nagar", 900),

    # Rotavator / Harvester
    ("Rotavator", "rotavator", 4, "Kattankulathur", 600),

    # Solar Pumps
    ("Solar Pump 1", "solar_pump", 5, "Potheri", 200),
    ("Solar Pump 2", "solar_pump", 6, "Maraimalai Nagar", 180),
    ("Solar Pump 3", "solar_pump", 1, "Kattankulathur", 220),

    # Agricultural inputs
    ("Tomato Seeds - 10 kg", "seed", 2, "Potheri", 500),
    ("Paddy Seeds - 20 kg", "seed", 3, "Maraimalai Nagar", 700),
    ("Organic Compost - 50 kg", "compost", 4, "Kattankulathur", 300),
    ("Organic Compost - 50 kg", "compost", 5, "Potheri", 300),
    ("Mulch - 25 kg", "mulch", 6, "Maraimalai Nagar", 250),
]

cursor.executemany("""
    INSERT INTO resources
    (name, resource_type, owner_id, village, price_per_hour, available)
    VALUES (?, ?, ?, ?, ?, 1)
""", resources)

connection.commit()
connection.close()

print("Resource data inserted successfully!")
