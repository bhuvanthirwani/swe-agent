from fastapi import APIRouter
from backend.core.database import get_db_connection
import json

router = APIRouter()

@router.get("/documents")
def get_documents():
    conn = get_db_connection()
    docs = conn.execute("SELECT * FROM knowledge_base").fetchall()
    conn.close()
    
    result = []
    for d in docs:
        item = dict(d)
        try:
            item['tags'] = json.loads(item['tags']) if item['tags'] else []
        except:
            item['tags'] = []
        result.append(item)
    return result
