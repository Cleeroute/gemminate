import sqlite3
import json
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()
# We don't know the exact db path, it might be in app/gemminate.db or similar
