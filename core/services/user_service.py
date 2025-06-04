import uuid
from datetime import datetime
from typing import Dict, List, Optional

from django.contrib.auth.hashers import make_password

from core.matchers.matchers_functions import create_user_and_calculate_matches

from .base_service import BaseNeo4jService


class UserService(BaseNeo4jService):
    """Service untuk semua operasi User-related"""

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Find user by email"""
        query = """
            MATCH (u:User {email: $email})
            RETURN u.uid as uid, u.email as email, u.user_email as user_email,
                   u.name as name, u.role as role, u.password as password,
                   u.created_at as created_at, u.updated_at as updated_at,
                   u.profilePicture as profile_image
        """

        results = self.execute_query(query, {"email": email})
        return results[0] if results else None

    def get_user_with_profile_picture(self, user_email: str) -> Optional[Dict]:
        """Get user data with profile picture for login"""
        query = """
            MATCH (u:User {email: $email})
            RETURN u.uid as uid, u.email as email, u.name as name, 
                   u.password as password, u.role as role, 
                   u.profilePicture as profile_image_path
        """
        results = self.execute_query(query, {"email": user_email})
        return results[0] if results else None

    def update_user_picture(self, user_uid: str, update_data: Dict) -> bool:
        """
        Update property pada node User berdasarkan uid.
        Contoh: update_data = {"profilePicture": "uploaded_files/profile_images/xxx.jpg"}
        """
        set_clauses = []
        params = {"uid": user_uid}
        for key, value in update_data.items():
            set_clauses.append(f"u.{key} = ${key}")
            params[key] = value
        set_clause = ", ".join(set_clauses)
        query = f"""
            MATCH (u:User {{uid: $uid}})
            SET {set_clause}
            RETURN u.uid as uid
        """
        results = self.execute_write_query(query, params)
        return len(results) > 0

    def update_user_profile(self, user_email: str, profile_data: Dict) -> bool:
        """Update user profile: hanya name dan/atau email"""
        set_clauses = []
        params = {"email": user_email}
        if "name" in profile_data and profile_data["name"] is not None:
            set_clauses.append("u.name = $name")
            params["name"] = profile_data["name"]
        if "email" in profile_data and profile_data["email"] is not None:
            set_clauses.append("u.email = $new_email")
            params["new_email"] = profile_data["email"]
        set_clauses.append("u.updated_at = $updated_at")
        params["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        set_clause = ", ".join(set_clauses)
        query = f"""
            MATCH (u:User {{email: $email}})
            SET {set_clause}
            RETURN u.email as email
        """
        results = self.execute_write_query(query, params)
        return len(results) > 0

    def update_user_skills(self, user_uid: str, skills: List[str]) -> int:
        """Update user skills by UID"""
        # Remove existing skills
        remove_query = """
            MATCH (u:User {uid: $uid})-[r:HAS_SKILL]->()
            DELETE r
            RETURN count(r) as removed
        """

        # Add new skills
        add_query = """
            MATCH (u:User {uid: $uid})
            UNWIND $skills as skill_name 
            MATCH (s:Skill)
            WHERE toLower(s.name) = toLower(skill_name)
            MERGE (u)-[:HAS_SKILL]->(s)
            RETURN count(DISTINCT s) as added
        """

        self.execute_write_query(remove_query, {"uid": user_uid})
        results = self.execute_write_query(
            add_query, {"uid": user_uid, "skills": skills}
        )
        print(f"Updated skills for user {user_uid}: {results}")

        return results[0]["added"] if results else 0

    def get_user_with_skills_and_profile(self, user_email: str) -> dict:
        """
        Ambil data user beserta skills dan foto profil (dari property profile_image)
        """
        query = """
            MATCH (u:User {email: $email})
            OPTIONAL MATCH (u)-[:HAS_SKILL]->(s:Skill)
            RETURN u.uid as uid, u.email as email, u.name as name, collect(s.name) as skills,
                   u.profilePicture as profile_image_path
        """
        results = self.execute_query(query, {"email": user_email})
        if not results:
            return None
        data = results[0]
        # Buat URL foto profil jika ada path-nya
        if data.get("profile_image_path"):
            data["profile_image_url"] = f"/api/profile/image/{user_email}/"
        else:
            data["profile_image_url"] = None
        return data

    def create_admin(self, user_data: dict) -> dict:
        """Create new admin user"""
        uid = str(uuid.uuid4())

        query = """
            CREATE (u:User {
                uid: $uid,
                name: $name,
                email: $email,
                password: $password,
                role: 'admin'
            })
            RETURN u.uid as uid, u.email as email, u.name as name, u.role as role
        """

        params = {
            "uid": uid,
            "name": user_data["name"],
            "email": user_data["email"],
            "password": make_password(user_data["password"]),
        }

        results = self.execute_write_query(query, params)
        return results[0] if results else {}

    def create_user_with_skills(
        self, user_data: dict, skills: list[str] = None
    ) -> dict:
        """Create new user with skills"""
        create_user_and_calculate_matches()

        # Generate UID tanpa dash
        uid = uuid.uuid4()

        query = """
            CREATE (u:User {
                uid: $uid,
                name: $name,
                email: $email,
                password: $password,
                role: $role,
            })
            WITH u
            UNWIND CASE WHEN $skills IS NOT NULL THEN $skills ELSE [] END AS skill_name
            MATCH (s:Skill {name: skill_name})
            CREATE (u)-[:HAS_SKILL]->(s)
            
            RETURN u.uid as uid, u.email as email, u.user_email as user_email, 
                   u.name as name, u.role as role, u.created_at as created_at,
                   u.updated_at as updated_at
        """

        params = {
            "uid": uid,
            "email": user_data["email"],
            "name": user_data["name"],
            "password": user_data["password"],
            "role": user_data["role"],
            "skills": skills,
        }

        results = self.execute_write_query(query, params)
        return results[0] if results else {}

    def toggle_bookmark(self, user_uid: str, job_url: str) -> Dict:
        """Toggle bookmark status between user and job"""
        try:
            # Check if bookmark already exists
            check_query = """
                MATCH (u:User {uid: $user_uid})
                MATCH (j:Job {jobUrl: $job_url})
                OPTIONAL MATCH (u)-[r:HAS_BOOKMARKED]->(j)
                RETURN r IS NOT NULL as is_bookmarked
            """

            result = self.execute_query(
                check_query, {"user_uid": user_uid, "job_url": job_url}
            )

            if not result:
                return {"success": False, "message": "User or Job not found"}

            is_currently_bookmarked = result[0]["is_bookmarked"]

            if is_currently_bookmarked:
                # Remove bookmark
                remove_query = """
                    MATCH (u:User {uid: $user_uid})
                    MATCH (j:Job {jobUrl: $job_url})
                    MATCH (u)-[r:HAS_BOOKMARKED]->(j)
                    DELETE r
                    RETURN "removed" as action
                """

                self.execute_write_query(
                    remove_query, {"user_uid": user_uid, "job_url": job_url}
                )

                return {
                    "success": True,
                    "action": "removed",
                    "is_bookmarked": False,
                    "message": "Bookmark removed successfully",
                }
            else:
                # Add bookmark
                add_query = """
                    MATCH (u:User {uid: $user_uid})
                    MATCH (j:Job {jobUrl: $job_url})
                    CREATE (u)-[:HAS_BOOKMARKED]->(j)
                    RETURN "added" as action
                """

                self.execute_write_query(
                    add_query, {"user_uid": user_uid, "job_url": job_url}
                )

                return {
                    "success": True,
                    "action": "added",
                    "is_bookmarked": True,
                    "message": "Bookmark added successfully",
                }

        except Exception as e:
            print(f"Error toggling bookmark: {e}")
            return {"success": False, "message": f"Error toggling bookmark: {str(e)}"}

    def get_bookmarked_jobs(self, user_uid: str) -> List[Dict]:
        """Get all jobs bookmarked by user"""
        try:
            query = """
                MATCH (u:User {uid: $user_uid})-[:HAS_BOOKMARKED]->(j:Job)
                OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
                WITH j, collect(DISTINCT s.name) as required_skills
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
                       required_skills
                ORDER BY j.jobTitle
            """

            results = self.execute_query(query, {"user_uid": user_uid})
            return results

        except Exception as e:
            print(f"Error getting bookmarked jobs: {e}")
            return []

    def check_bookmark_status(
        self, user_uid: str, job_urls: List[str]
    ) -> Dict[str, bool]:
        """Check bookmark status for multiple jobs"""
        try:
            query = """
                MATCH (u:User {uid: $user_uid})
                UNWIND $job_urls as job_url
                MATCH (j:Job {job_url: job_url})
                OPTIONAL MATCH (u)-[r:HAS_BOOKMARKED]->(j)
                RETURN job_url, r IS NOT NULL as is_bookmarked
            """

            results = self.execute_query(
                query, {"user_uid": user_uid, "job_urls": job_urls}
            )

            bookmark_status = {}
            for result in results:
                bookmark_status[result["job_url"]] = result["is_bookmarked"]

            return bookmark_status

        except Exception as e:
            print(f"Error checking bookmark status: {e}")
            return {}

    def update_user_password(self, user_uid: str, new_password: str) -> bool:
        """Update user password"""
        try:
            # Update current timestamp
            current_date = datetime.now().strftime("%Y-%m-%d")

            query = """
                MATCH (u:User {uid: $user_uid})
                SET u.password = $new_password,
                    u.updated_at = $updated_at
                RETURN u.uid as uid
            """

            params = {
                "user_uid": user_uid,
                "new_password": new_password,
                "updated_at": current_date,
            }

            result = self.execute_write_query(query, params)

            if result:
                print(f"✅ Password updated successfully for user: {user_uid}")
                return True
            else:
                print(f"❌ Failed to update password for user: {user_uid}")
                return False

        except Exception as e:
            print(f"❌ Error updating password: {e}")
            return False

    def report_job(
        self, user_uid: str, job_url: str, report_type: str, report_descriptions: str
    ) -> bool:
        """
        Membuat relasi HAS_REPORTED dari User ke Job dengan property reportType, reportDescriptions, reportDate, reportStatus
        """
        query = """
            MATCH (u:User {uid: $user_uid}), (j:Job {jobUrl: $job_url})
            MERGE (u)-[r:HAS_REPORTED]->(j)
            SET r.reportType = $report_type,
                r.reportDescriptions = $report_descriptions,
                r.reportDate = $report_date,
                r.reportStatus = $report_status
            RETURN r
        """
        params = {
            "user_uid": user_uid,
            "job_url": job_url,
            "report_type": report_type,
            "report_descriptions": report_descriptions,
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_status": "Perlu Ditinjau",
        }
        results = self.execute_write_query(query, params)
        return bool(results)


# Global instance
user_service = UserService()
