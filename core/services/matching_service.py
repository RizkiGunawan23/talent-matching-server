from typing import Dict, List, Optional
from .base_service import BaseNeo4jService


class MatchingService(BaseNeo4jService):
    """Service untuk semua operasi Job Matching"""

    def get_user_job_matches_with_filters(self, user_email: str, filters: dict = None, limit: int = 100) -> List[Dict]:
        """Get job matches for a user with filtering options"""
        # Default filters
        if filters is None:
            filters = {}
        
        job_query = filters.get('job', '')
        location = filters.get('location', '')
        job_types = filters.get('jobTypes', [])
        work_arrangements = filters.get('workArrangements', [])
        education_levels = filters.get('educationLevels', [])
        experiences = filters.get('experiences', [])
        salary_min = filters.get('salaryMin', '')
        salary_max = filters.get('salaryMax', '')
        sort_order = filters.get('sortOrder', 'similarity-desc')
        
        # Build ORDER BY clause based on sort_order
        if sort_order == 'similarity-desc':
            order_clause = "ORDER BY m.similarityScore DESC"
        elif sort_order == 'similarity-asc':
            order_clause = "ORDER BY m.similarityScore ASC"
        elif sort_order == 'descending':  # Fallback for old format
            order_clause = "ORDER BY m.similarityScore DESC"
        elif sort_order == 'ascending':   # Fallback for old format
            order_clause = "ORDER BY m.similarityScore ASC"
        else:
            order_clause = "ORDER BY m.similarityScore DESC"  # default
        
        print(f"🔄 Using sort order: {sort_order} -> {order_clause}")
        
        # Build Cypher query with optional filters
        filter_conditions = []
        params = {"email": user_email, "limit": limit}
        
        # PERBAIKAN: Ubah user_email menjadi email
        query = """
            MATCH (m:UserJobMatch)-[:USER_MATCH]->(u:User {email: $email})
            MATCH (m)-[:JOB_MATCH]->(j:Job)
        """
        
        # Add job title filter - PERBAIKAN: gunakan job_title bukan title
        if job_query and job_query != 'all':
            filter_conditions.append("toLower(j.job_title) CONTAINS toLower($job_query)")
            params["job_query"] = job_query
            
        # Add location filter
        if location and location != 'all':
            filter_conditions.append("toLower(j.province) CONTAINS toLower($location)")
            params["location"] = location
            
        # Add job type filter
        if job_types and len(job_types) > 0:
            filter_conditions.append("j.employment_type IN $job_types")
            params["job_types"] = job_types
            
        # Add work arrangement filter
        if work_arrangements and len(work_arrangements) > 0:
            filter_conditions.append("j.work_setup IN $work_arrangements")
            params["work_arrangements"] = work_arrangements
            
        # Add education level filter
        if education_levels and len(education_levels) > 0:
            filter_conditions.append("j.minimum_education IN $education_levels")
            params["education_levels"] = education_levels
            
        # Add experience filter
        if experiences and len(experiences) > 0:
            has_junior = "Junior (0-2 years)" in experiences
            has_mid = "Mid-level (3-5 years)" in experiences
            has_senior = "Senior (6+ years)" in experiences
            
            exp_conditions = []
            if has_junior:
                exp_conditions.append("(j.minimum_experience >= 0 AND j.maximum_experience <= 2)")
            if has_mid:
                exp_conditions.append("(j.minimum_experience >= 3 AND j.maximum_experience <= 5)")
            if has_senior:
                exp_conditions.append("(j.minimum_experience >= 6)")
                
            if exp_conditions:
                filter_conditions.append("(" + " OR ".join(exp_conditions) + ")")
    
        # Add salary filters - PERBAIKAN: Tambahkan pengecekan None untuk salary
        if salary_min and str(salary_min).isdigit():
            filter_conditions.append("(j.minimum_salary >= $salary_min OR j.maximum_salary >= $salary_min)")
            params["salary_min"] = int(salary_min)
        
        if salary_max and str(salary_max).isdigit():
            filter_conditions.append("(j.minimum_salary <= $salary_max)")
            params["salary_max"] = int(salary_max)
            
        # Apply all filters
        if filter_conditions:
            query += "WHERE " + " AND ".join(filter_conditions) + "\n"
            
        # Get required skills and add match type information
        query += """
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            OPTIONAL MATCH (j)-[:HAS_ADDITIONAL_SKILL]->(a:AdditionalSkill)
            WITH m, j, apoc.coll.toSet(collect(DISTINCT s.name) + collect(DISTINCT a.name)) as required_skills
            RETURN j.job_url as job_url, j.job_title as job_title, j.company_name as company_name,
                   j.city as city, j.province as province, j.image_url as image_url,
                   j.minimum_salary as minimum_salary, j.maximum_salary as maximum_salary,
                   j.salary_unit as salary_unit, j.salary_type as salary_type,
                   j.employment_type as employment_type, j.work_setup as work_setup,
                   j.minimum_education as minimum_education, 
                   j.minimum_experience as minimum_experience, 
                   j.maximum_experience as maximum_experience,
                   required_skills, j.job_description as job_description,
                   m.similarityScore as similarity_score, m.matchType as match_type
        """

        # Add sorting
        query += order_clause + "\n"
        
        # Execute query
        try:
            print(f"🔍 Executing query with email: {user_email}")
            print(f"📝 Query: {query}")
            print(f"📊 Params: {params}")
            
            # PERBAIKAN: Gunakan execute_query bukan execute_read_query
            result = self.execute_query(query, params)
            
            print(f"✅ Found {len(result)} job matches")
            
            if len(result) > 0:
                print(f"🔍 Sample result: {result[0]}")
            
            return result
        except Exception as e:
            print(f"❌ Error executing query: {e}")
            import traceback
            traceback.print_exc()
            return []


# Global instance
matching_service = MatchingService()