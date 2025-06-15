import pandas as pd
import sqlite3

# 1) Read the CSV
df = pd.read_csv("plants.csv")

# 2) Open a real sqlite3 connection
conn = sqlite3.connect("aqualog.db")
cur = conn.cursor()

# 3) Bulk-insert – it will map CSV columns to table columns one-to-one
cols = ", ".join(df.columns)
placeholders = ", ".join("?" for _ in df.columns)
sql = f"INSERT INTO plants ({cols}) VALUES ({placeholders});"

records = df.to_records(index=False)
cur.executemany(sql, records)
conn.commit()
conn.close()

print("✅ Imported", len(df), "rows into plants")
