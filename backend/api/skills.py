from fastapi import APIRouter
from backend.core.database import get_db_connection
import json

router = APIRouter()

@router.get("/languages")
def get_language_skills():
    conn = get_db_connection()
    skills = conn.execute("SELECT * FROM language_skills").fetchall()
    conn.close()
    
    result = []
    for s in skills:
        item = dict(s)
        try:
            item['file_extensions'] = json.loads(item['file_extensions'])
        except:
            item['file_extensions'] = []
        result.append(item)
    return result
