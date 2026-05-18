
from app.database import SessionLocal
from app import models

db = SessionLocal()
try:
    visuals = db.query(models.Visual).all()
    for v in visuals:
        if 'treemap' in v.html_content.lower():
            print(f"--- VISUAL ID: {v.id} ---")
            print(v.html_content)
            print("-" * 40)
finally:
    db.close()
