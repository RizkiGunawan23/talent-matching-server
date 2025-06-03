from typing import Dict, List, Optional
from .base_service import BaseNeo4jService


class SkillService(BaseNeo4jService):
    """Service untuk semua operasi Skill-related"""

    def get_all_skills(self) -> List[Dict]:
        """Get all skills in the system"""
        query = """
            MATCH (s:Skill)
            RETURN s.name as name
            ORDER BY s.name ASC
        """
        
        return self.execute_query(query)

    def get_skills_for_dropdown(self) -> List[str]:
        """Get skill names for dropdown"""
        query = """
            MATCH (s:Skill)
            RETURN s.name as name
            ORDER BY s.name ASC
        """
        
        results = self.execute_query(query)
        return [result['name'] for result in results]

    def search_skills(self, search_term: str, limit: int = 20) -> List[Dict]:
        """Search skills by name"""
        query = """
            MATCH (s:Skill)
            WHERE toLower(s.name) CONTAINS toLower($search_term)
            RETURN s.name as name
            ORDER BY s.name ASC
            LIMIT $limit
        """
        
        return self.execute_query(query, {"search_term": search_term, "limit": limit})


# Global instance
skill_service = SkillService()