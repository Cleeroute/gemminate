from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("DATABASE_URL", "sqlite:///./gemminate.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chat_messages ADD COLUMN chapter_title VARCHAR;"))
    print("Column added")
except Exception as e:
    print("Error:", e)
