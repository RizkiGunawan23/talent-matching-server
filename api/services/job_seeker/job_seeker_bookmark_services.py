from typing import Dict, List
from neomodel import db
from api.models import User, Job


def toggle_bookmark(user_uid: str, job_url: str) -> Dict:
    """Toggle bookmark status between user and job"""
    try:
        # Start a database transaction
        db.begin()
        
        # Find the user and job
        user = User.nodes.get_or_none(uid=user_uid)
        job = Job.nodes.get_or_none(jobUrl=job_url)
        
        # Check if both exist
        if not user or not job:
            db.rollback()
            return {"success": False, "message": "User or Job not found"}
        
        # Check if bookmark already exists using Cypher for efficiency
        check_query = """
            MATCH (u:User {uid: $user_uid})
            MATCH (j:Job {jobUrl: $job_url})
            OPTIONAL MATCH (u)-[r:HAS_BOOKMARKED]->(j)
            RETURN r IS NOT NULL as is_bookmarked
        """
        
        results, _ = db.cypher_query(
            check_query, {"user_uid": user_uid, "job_url": job_url}
        )
        
        is_currently_bookmarked = results[0][0] if results else False
        
        if is_currently_bookmarked:
            # Remove bookmark relationship
            remove_query = """
                MATCH (u:User {uid: $user_uid})
                MATCH (j:Job {jobUrl: $job_url})
                MATCH (u)-[r:HAS_BOOKMARKED]->(j)
                DELETE r
            """
            
            db.cypher_query(remove_query, {"user_uid": user_uid, "job_url": job_url})
            
            db.commit()
            return {
                "success": True,
                "action": "removed",
                "is_bookmarked": False,
                "message": "Bookmark removed successfully"
            }
        else:
            # Add bookmark relationship
            add_query = """
                MATCH (u:User {uid: $user_uid})
                MATCH (j:Job {jobUrl: $job_url})
                CREATE (u)-[:HAS_BOOKMARKED]->(j)
            """
            
            db.cypher_query(add_query, {"user_uid": user_uid, "job_url": job_url})
            
            db.commit()
            return {
                "success": True,
                "action": "added",
                "is_bookmarked": True,
                "message": "Bookmark added successfully"
            }
            
    except Exception as e:
        db.rollback()
        print(f"Error toggling bookmark: {str(e)}")
        return {"success": False, "message": f"Error toggling bookmark: {str(e)}"}
    
def get_bookmarked_jobs(user_uid: str) -> List[Dict]:
    """Get all jobs bookmarked by user"""
    try:
        query = """
            MATCH (u:User {uid: $user_uid})-[:HAS_BOOKMARKED]->(j:Job)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(a:AdditionalSkill)
            WITH j, collect(DISTINCT s.name) as skills, collect(DISTINCT a.name) as additional_skills
            RETURN j.jobUrl as job_url,
                   j.jobTitle as job_title,
                   j.companyName as company_name,
                   j.city as city,
                   j.province as province,
                   j.subdistrict as subdistrict,
                   j.minimumSalary as minimum_salary,
                   j.maximumSalary as maximum_salary,
                   j.salaryUnit as salary_unit,
                   j.salaryType as salary_type,
                   j.employmentType as employment_type,
                   j.workSetup as work_setup,
                   j.minimumEducation as minimum_education,
                   j.minimumExperience as minimum_experience,
                   j.maximumExperience as maximum_experience,
                   j.imageUrl as image_url,
                   j.jobDescription as job_description,
                   apoc.coll.toSet(skills + additional_skills) as required_skills
            ORDER BY j.jobTitle
        """

        results, _ = db.cypher_query(query, {"user_uid": user_uid})
        
        # Column names from the query
        columns = [
            'job_url', 'job_title', 'company_name', 'city', 'province', 'subdistrict',
            'minimum_salary', 'maximum_salary', 'salary_unit', 'salary_type',
            'employment_type', 'work_setup', 'minimum_education', 'minimum_experience',
            'maximum_experience', 'image_url', 'job_description', 'required_skills'
        ]
        
        # Convert results to dictionaries
        result_dicts = []
        for row in results:
            result_dict = {columns[i]: row[i] for i in range(len(columns))}
            result_dicts.append(result_dict)
            
        return result_dicts

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error getting bookmarked jobs: {str(e)}")
        return []

def check_bookmark_status(user_uid: str, job_urls: List[str]) -> Dict[str, bool]:
    """Check bookmark status for multiple jobs"""
    try:
        # Return empty dict if no job URLs provided
        if not job_urls:
            return {}
            
        query = """
            MATCH (u:User {uid: $user_uid})
            UNWIND $job_urls as job_url
            OPTIONAL MATCH (j:Job {jobUrl: job_url})
            OPTIONAL MATCH (u)-[r:HAS_BOOKMARKED]->(j)
            RETURN job_url, r IS NOT NULL as is_bookmarked
        """

        results, _ = db.cypher_query(query, {"user_uid": user_uid, "job_urls": job_urls})
        
        bookmark_status = {}
        for row in results:
            job_url = row[0]
            is_bookmarked = row[1]
            bookmark_status[job_url] = is_bookmarked

        return bookmark_status

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error checking bookmark status: {str(e)}")
        return {}