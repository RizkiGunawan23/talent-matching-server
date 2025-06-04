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
        
        # Add job title filter - PERBAIKAN: gunakan jobTitle bukan job_title
        if job_query and job_query != 'all':
            filter_conditions.append("toLower(j.jobTitle) CONTAINS toLower($job_query)")
            params["job_query"] = job_query
            
        # Add location filter
        if location and location != 'all':
            filter_conditions.append("toLower(j.province) CONTAINS toLower($location)")
            params["location"] = location
            
        # Add job type filter
        if job_types and len(job_types) > 0:
            filter_conditions.append("j.employmentType IN $job_types")
            params["job_types"] = job_types
            
        # Add work arrangement filter
        if work_arrangements and len(work_arrangements) > 0:
            filter_conditions.append("j.workSetup IN $work_arrangements")
            params["work_arrangements"] = work_arrangements
            
        # Add education level filter
        if education_levels and len(education_levels) > 0:
            filter_conditions.append("j.minimumEducation IN $education_levels")
            params["education_levels"] = education_levels
            
        # Add experience filter
        if experiences and len(experiences) > 0:
            has_junior = "Junior (0-2 years)" in experiences
            has_mid = "Mid-level (3-5 years)" in experiences
            has_senior = "Senior (6+ years)" in experiences
            
            exp_conditions = []
            if has_junior:
                exp_conditions.append("(j.minimumExperience >= 0 AND j.maximumExperience <= 2)")
            if has_mid:
                exp_conditions.append("(j.minimumExperience >= 3 AND j.maximumExperience <= 5)")
            if has_senior:
                exp_conditions.append("(j.minimumExperience >= 6)")
                
            if exp_conditions:
                filter_conditions.append("(" + " OR ".join(exp_conditions) + ")")
    
        # Add salary filters - PERBAIKAN: Tambahkan pengecekan None untuk salary
        if salary_min and str(salary_min).isdigit():
            filter_conditions.append("(j.minimumSalary >= $salary_min OR j.maximumSalary >= $salary_min)")
            params["salary_min"] = int(salary_min)
        
        if salary_max and str(salary_max).isdigit():
            filter_conditions.append("(j.minimumSalary <= $salary_max)")
            params["salary_max"] = int(salary_max)
            
        # Apply all filters
        if filter_conditions:
            query += "WHERE " + " AND ".join(filter_conditions) + "\n"
            
        # Get required skills and add match type information
        query += """
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(a:AdditionalSkill)
            WITH m, j, apoc.coll.toSet(collect(DISTINCT s.name) + collect(DISTINCT a.name)) as required_skills
            RETURN j.jobUrl as job_url, j.jobTitle as job_title, j.companyName as company_name,
                   j.city as city, j.province as province, j.imageUrl as image_url,
                   j.minimumSalary as minimum_salary, j.maximumSalary as maximum_salary,
                   j.salaryUnit as salary_unit, j.salaryType as salary_type,
                   j.employmentType as employment_type, j.workSetup as work_setup,
                   j.minimumEducation as minimum_education, 
                   j.minimumExperience as minimum_experience, 
                   j.maximumExperience as maximum_experience,
                   required_skills, j.jobDescription as job_description,
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