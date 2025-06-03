from .base_service import BaseNeo4jService

class MaintenanceService(BaseNeo4jService):
    def get_maintenance_status(self) -> dict:
        """
        Ambil node Maintenance dan property isMaintenance
        """
        query = """
            MATCH (m:Maintenance)
            RETURN m.isMaintenance AS is_maintenance
            LIMIT 1
        """
        results = self.execute_query(query)
        if results:
            return {"is_maintenance": results[0].get("is_maintenance", False)}
        return {"is_maintenance": False}

# Global instance
maintenance_service = MaintenanceService()