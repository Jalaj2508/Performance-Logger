import sqlite3

DB = 'database/compressor.db'  # Adjust path if needed

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("DELETE FROM tests")
conn.commit()
conn.close()

print("All records cleared.")
