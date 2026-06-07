from fastapi import APIRouter
from backend.core.database import get_db_connection

router = APIRouter()

@router.get("/roles")
def get_roles():
    conn = get_db_connection()
    roles = conn.execute("SELECT * FROM roles").fetchall()
    role_perms = conn.execute("SELECT * FROM role_permissions").fetchall()
    conn.close()
    
    perms_map = {}
    for rp in role_perms:
        role_id = rp['role_id']
        if role_id not in perms_map:
            perms_map[role_id] = []
        perms_map[role_id].append(rp['permission'])
        
    result = []
    for r in roles:
        result.append({
            "id": r["id"],
            "description": r["description"],
            "permissions": perms_map.get(r["id"], [])
        })
    return {"roles": result}
