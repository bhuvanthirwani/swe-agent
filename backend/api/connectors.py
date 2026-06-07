from fastapi import APIRouter
from backend.core.database import get_db_connection
import json

router = APIRouter()

@router.get("")
def get_connectors():
    conn = get_db_connection()
    connectors = conn.execute("SELECT * FROM connectors").fetchall()
    conn.close()
    
    result = []
    for c in connectors:
        item = dict(c)
        item['enabled'] = bool(item['enabled'])
        if item['config']:
            try:
                item['config'] = json.loads(item['config'])
            except:
                pass
        result.append(item)
    return result
