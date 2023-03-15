import sqlite3
import pandas as pd

DB_NAME = 'static/data/users.db'

# with sqlite3.connect(DB_NAME) as conn:
#             cur = conn.cursor()
#             cur.execute("SELECT * FROM sid3 LIMIT 10")
#             print(cur.fetchall())

conn = sqlite3.connect(DB_NAME)
cmd = """SELECT * from {}""".format('sid2')
df = pd.read_sql(cmd, conn)
print(df.head())
