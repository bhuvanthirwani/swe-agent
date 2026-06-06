class RBACManager:
    """Role-Based Access Control logic migrated from rbac.ts"""
    ROLES = ["admin", "member", "viewer"]

    @staticmethod
    def can_manage_settings(role: str) -> bool:
        return role == "admin"

    @staticmethod
    def can_run_pipeline(role: str) -> bool:
        return role in ["admin", "member"]

    @staticmethod
    def can_manage_workflows(role: str) -> bool:
        return role in ["admin", "member"]
