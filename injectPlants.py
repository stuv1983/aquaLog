import pandas as pd
import sqlite3

# 1) Read the CSV
df = pd.read_csv("plants.csv")

# 2) Define exactly the columns your CSV provides (omit plant_id, created_at, updated_at)
csv_columns = [
    "plant_name",
    "origin",
    "origin_info",
    "growth_rate",
    "growth_info",
    "height_cm",
    "height_info",
    "light_demand",
    "light_info",
    "co2_demand",
    "co2_info",
    "thumbnail_url",
]

# Ensure your CSV has exactly these headers:
missing = set(csv_columns) - set(df.columns)
if missing:
    raise RuntimeError(f"Missing columns in CSV: {missing}")

# 3) Prepare the insert
cols_sql = ", ".join(csv_columns)
placeholders = ", ".join("?" for _ in csv_columns)
sql = f"INSERT INTO plants ({cols_sql}) VALUES ({placeholders});"

# Convert DataFrame to list of tuples, in the right order
records = [tuple(row) for row in df[csv_columns].itertuples(index=False, name=None)]

# 4) Execute against the DB
conn = sqlite3.connect("aqualog.db")
cur = conn.cursor()
cur.executemany(sql, records)
conn.commit()

# 5) Verify
count = cur.execute("SELECT COUNT(*) FROM plants;").fetchone()[0]
sample = cur.execute("SELECT * FROM plants LIMIT 5;").fetchall()
conn.close()

print(f"✅ Imported {len(records)} rows.  Table now has {count} rows.")
print("Sample rows:", sample)
