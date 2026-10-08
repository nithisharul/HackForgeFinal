import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "kisanpool.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
    DROP TABLE IF EXISTS impact_records;
    DROP TABLE IF EXISTS bookings;
    DROP TABLE IF EXISTS requests;
    DROP TABLE IF EXISTS resources;
    DROP TABLE IF EXISTS farmers;

    -- Entity 1: Farmer
    CREATE TABLE farmers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        village TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        preferred_language TEXT NOT NULL DEFAULT 'ta'
    );

    -- Entity 2: Resource (Unified across MachineShare, SolarPump, InputLoop)
    CREATE TABLE resources (
        id TEXT PRIMARY KEY,
        owner_id TEXT NOT NULL,
        module TEXT NOT NULL, -- 'MachineShare', 'SolarPump', 'InputLoop'
        type TEXT NOT NULL,
        subtype TEXT NOT NULL,
        capacity_or_quantity REAL NOT NULL,
        unit TEXT NOT NULL,
        avail_start TEXT,
        avail_end TEXT,
        price REAL NOT NULL,
        location TEXT NOT NULL,
        lat REAL,
        lon REAL,
        verification_status TEXT NOT NULL -- 'VERIFIED', 'PENDING', 'PROHIBITED'
    );

    -- Entity 3: Request
    CREATE TABLE requests (
        id TEXT PRIMARY KEY,
        farmer_id TEXT NOT NULL,
        module TEXT NOT NULL,
        farm_task TEXT NOT NULL,
        required_qty REAL NOT NULL,
        urgency TEXT NOT NULL, -- 'HIGH', 'MEDIUM', 'STANDARD'
        deadline TEXT NOT NULL,
        crop TEXT NOT NULL,
        raw_text TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPEN'
    );

    -- Entity 4: Booking
    CREATE TABLE bookings (
        id TEXT PRIMARY KEY,
        resource_id TEXT NOT NULL,
        borrower_id TEXT NOT NULL,
        module TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        quantity_reserved REAL NOT NULL,
        priority_score INTEGER NOT NULL,
        status TEXT NOT NULL, -- 'PROPOSED', 'RESERVED', 'REALLOCATED', 'CANCELLED'
        FOREIGN KEY(resource_id) REFERENCES resources(id),
        FOREIGN KEY(borrower_id) REFERENCES farmers(id)
    );

    -- Entity 5: Impact Record (Deterministic Calculations)
    CREATE TABLE impact_records (
        id TEXT PRIMARY KEY,
        booking_id TEXT NOT NULL,
        cost_baseline REAL NOT NULL,
        cost_optimized REAL NOT NULL,
        travel_baseline_km REAL NOT NULL,
        travel_optimized_km REAL NOT NULL,
        solar_hours REAL NOT NULL,
        reused_input_quantity REAL NOT NULL,
        FOREIGN KEY(booking_id) REFERENCES bookings(id)
    );
    """)

    # 1. Farmers Seed (5 in Guduvanchery baseline)
    farmers = [
        ("F-101", "Ravi Kumar", "Guduvanchery", 12.8438, 80.0583, "ta"),
        ("F-102", "S. Selvam", "Guduvanchery", 12.8452, 80.0611, "ta"),
        ("F-103", "K. Anbazhagan", "Guduvanchery", 12.8421, 80.0559, "ta"),
        ("F-104", "Murugan", "Guduvanchery", 12.8465, 80.0634, "ta"),
        ("F-105", "P. Natarajan", "Guduvanchery", 12.8409, 80.0542, "ta"),
    ]
    c.executemany("INSERT INTO farmers VALUES (?, ?, ?, ?, ?, ?)", farmers)

    # 2. Resources across MachineShare, SolarPump, InputLoop
    resources = [
        # Module 4.1: MachineShare AI
        ("RES-TRAC-01", "F-101", "MachineShare", "Tractor", "Sonalika 45HP + Rotavator", 45.0, "HP", "07:00", "18:00", 900.0, "Guduvanchery", 12.8400, 80.0500, "VERIFIED"),
        ("RES-TRAC-02", "F-105", "MachineShare", "Tractor", "Mahindra 35HP Cultivator", 35.0, "HP", "08:00", "16:00", 750.0, "Guduvanchery", 12.8410, 80.0510, "VERIFIED"),
        ("RES-HARV-01", "CHC-CENTRAL", "MachineShare", "Harvester", "Preet 987 Combine", 100.0, "HP", "09:00", "17:00", 2200.0, "Chengalpattu", 12.8300, 80.0400, "VERIFIED"),

        # Module 4.2: SolarPump Pool
        ("RES-PUMP-01", "COMMUNITY-01", "SolarPump", "SurfacePump", "Kirloskar 5HP Solar Surface", 5.0, "HP", "06:00", "11:00", 120.0, "Guduvanchery North", 12.8440, 80.0590, "VERIFIED"),
        ("RES-PUMP-02", "COMMUNITY-02", "SolarPump", "Submersible", "Shakti 5HP Deep Well Solar", 5.0, "HP", "11:30", "17:00", 120.0, "Guduvanchery South", 12.8415, 80.0560, "VERIFIED"),

        # Module 4.3: InputLoop (Safe inputs ONLY; pesticides explicitly prohibited)
        ("RES-INP-01", "F-102", "InputLoop", "CertifiedSeeds", "Sealed Paddy Seeds (BPT-5204)", 250.0, "kg", None, None, 38.0, "Guduvanchery Hub", None, None, "VERIFIED"),
        ("RES-INP-02", "F-103", "InputLoop", "PlantingMaterial", "Certified Groundnut Kernels", 120.0, "kg", None, None, 80.0, "Guduvanchery Hub", None, None, "VERIFIED"),
        ("RES-INP-03", "CHC-CENTRAL", "InputLoop", "OrganicCompost", "Enriched Farmyard Compost", 800.0, "kg", None, None, 6.0, "Guduvanchery Hub", None, None, "VERIFIED"),
        ("RES-INP-04", "F-105", "InputLoop", "IrrigationSupplies", "Drip Lateral Tubing (16mm)", 500.0, "meters", None, None, 12.0, "Guduvanchery Hub", None, None, "VERIFIED"),
    ]
    c.executemany("INSERT INTO resources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", resources)

    # 3. Seed Existing Base Bookings
    bookings = [
        ("BK-01", "RES-TRAC-01", "F-101", "MachineShare", "08:00", "10:00", 1.0, 10, "RESERVED"),
        ("BK-02", "RES-TRAC-01", "F-102", "MachineShare", "10:30", "13:30", 1.0, 10, "RESERVED"),
        ("BK-03", "RES-PUMP-01", "F-103", "SolarPump", "06:30", "09:30", 1.0, 10, "RESERVED"),
    ]
    c.executemany("INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", bookings)

    conn.commit()
    conn.close()
    print("Database re-seeded with MachineShare, SolarPump Pool, and InputLoop resources.")

if __name__ == "__main__":
    init_db()