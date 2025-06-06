from typing import Dict, List, Optional
from .base_service import BaseNeo4jService


class JobService(BaseNeo4jService):
    """Service untuk semua operasi Job-related"""

    def get_jobs_by_filters(self, filters: Dict) -> List[Dict]:
        """Get jobs with filters applied - Fixed logic for AND/OR"""
        where_conditions = []
        parameters = {}

        # Search filters - Skip if "all"
        if filters.get("job") and filters.get("job") != "all":
            where_conditions.append(
                """
                    (
                        toLower(j.jobTitle) CONTAINS toLower($job_title) OR
                        toLower(j.companyName) CONTAINS toLower($job_title) OR
                        EXISTS {
                            MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
                            WHERE toLower(s.name) CONTAINS toLower($job_title)
                        }
                    )
                """
            )
            
            parameters["job_title"] = filters["job"]

        if filters.get("location") and filters.get("location") != "all":
            where_conditions.append(
                """
                (toLower(j.city) CONTAINS toLower($location) OR 
                 toLower(j.province) CONTAINS toLower($location) OR
                 toLower(j.subdistrict) CONTAINS toLower($location))
            """
            )
            parameters["location"] = filters["location"]

        # Salary filters - AND logic
        if filters.get("salaryMin"):
            try:
                salary_min = int(filters["salaryMin"])
                where_conditions.append("j.minimumSalary >= $salary_min")
                parameters["salary_min"] = salary_min
            except ValueError:
                pass

        if filters.get("salaryMax"):
            try:
                salary_max = int(filters["salaryMax"])
                where_conditions.append("j.maximumSalary <= $salary_max")
                parameters["salary_max"] = salary_max
            except ValueError:
                pass

        # Employment type filter - OR logic (if any of selected types match)
        if filters.get("jobTypes") and len(filters["jobTypes"]) > 0:
            where_conditions.append("j.employmentType IN $employment_types")
            parameters["employment_types"] = filters["jobTypes"]

        # Work setup filter - OR logic (if any of selected setups match)
        if filters.get("workArrangements") and len(filters["workArrangements"]) > 0:
            where_conditions.append("j.workSetup IN $work_setups")
            parameters["work_setups"] = filters["workArrangements"]

        # Experience filter - OR logic (if job fits any of selected experience ranges)
        if filters.get("experiences") and len(filters["experiences"]) > 0:
            experience_conditions = []

            for exp in filters["experiences"]:
                if exp == "no-experience":
                    experience_conditions.append(
                        "(j.minimumExperience = 0 OR j.minimumExperience IS NULL)"
                    )
                elif exp == "fresh-graduate":
                    experience_conditions.append(
                        "(j.minimumExperience <= 1 OR j.minimumExperience IS NULL)"
                    )
                elif exp == "less-than-year":
                    experience_conditions.append(
                        "(j.minimumExperience < 1 OR j.minimumExperience IS NULL)"
                    )
                elif exp == "1-3-years":
                    experience_conditions.append(
                        "(j.minimumExperience >= 1 AND j.minimumExperience <= 3)"
                    )
                elif exp == "3-5-years":
                    experience_conditions.append(
                        "(j.minimumExperience >= 3 AND j.minimumExperience <= 5)"
                    )
                elif exp == "5-10-years":
                    experience_conditions.append(
                        "(j.minimumExperience >= 5 AND j.minimumExperience <= 10)"
                    )
                elif exp == "more-than-10":
                    experience_conditions.append("(j.minimumExperience > 10)")

            if experience_conditions:
                where_conditions.append(f"({' OR '.join(experience_conditions)})")

        # Education filter - OR logic (if any of selected education levels match)
        if filters.get("educationLevels") and len(filters["educationLevels"]) > 0:
            where_conditions.append("j.minimumEducation IN $education_levels")
            parameters["education_levels"] = filters["educationLevels"]

        # Build WHERE clause - AND logic between different filter types
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Sort order
        sort_order = "ASC" if filters.get("sortOrder") == "ascending" else "DESC"

        # UPDATED QUERY - Return ALL fields from Job node
        query = f"""
            MATCH (j:Job)
            WHERE {where_clause}
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(a:AdditionalSkill)
            WITH j, collect(DISTINCT s.name) as required_skills, collect(DISTINCT a.name) as additional_skills
            RETURN 
            j.uri as uid,
            j.jobUrl as job_url,
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
            required_skills,
            additional_skills
            ORDER BY j.scrapedAt {sort_order}
        """

        print(f"Final Query: {query}")
        print(f"Parameters: {parameters}")

        results = self.execute_query(query, parameters)

        # Transform results to ensure all fields are present
        transformed_results = []
        for result in results:
            # Gabungkan required_skills dan additional_skills, hilangkan duplikat
            required_skills = result.get("required_skills", []) or []
            additional_skills = result.get("additional_skills", []) or []
            all_skills = list({*required_skills, *additional_skills})
            job_data = {
                "uid": result.get("uid"),
                "job_url": result.get("job_url"),
                "job_title": result.get("job_title"),
                "company_name": result.get("company_name"),
                "city": result.get("city"),
                "province": result.get("province"),
                "subdistrict": result.get("subdistrict"),
                "minimum_salary": result.get("minimum_salary"),
                "maximum_salary": result.get("maximum_salary"),
                "salary_unit": result.get("salary_unit"),
                "salary_type": result.get("salary_type"),
                "employment_type": result.get("employment_type"),
                "work_setup": result.get("work_setup"),
                "minimum_education": result.get("minimum_education"),
                "minimum_experience": result.get("minimum_experience"),
                "maximum_experience": result.get("maximum_experience"),
                "image_url": result.get("image_url"),
                "job_description": result.get("job_description"),
                "required_skills": all_skills,
            }
            transformed_results.append(job_data)

        return transformed_results

    def get_filter_options(self) -> Dict[str, List[Dict]]:
        """Get all available filter options from Job nodes in database with case-insensitive deduplication"""

        # Get unique employment types
        employment_types_query = """
            MATCH (j:Job)
            WHERE j.employmentType IS NOT NULL AND j.employmentType <> ''
            RETURN DISTINCT j.employmentType as value
            ORDER BY j.employmentType
        """

        # Get unique work setups
        work_setups_query = """
            MATCH (j:Job)
            WHERE j.workSetup IS NOT NULL AND j.workSetup <> ''
            RETURN DISTINCT j.workSetup as value
            ORDER BY j.workSetup
        """

        # Get unique education levels
        education_levels_query = """
            MATCH (j:Job)
            WHERE j.minimumEducation IS NOT NULL AND j.minimumEducation <> ''
            RETURN DISTINCT j.minimumEducation as value
            ORDER BY j.minimumEducation
        """

        # Get unique provinces
        provinces_query = """
            MATCH (j:Job)
            WHERE j.province IS NOT NULL AND j.province <> ''
            RETURN DISTINCT j.province as value
            ORDER BY j.province
        """

        # Execute queries
        employment_results = self.execute_query(employment_types_query)
        work_setup_results = self.execute_query(work_setups_query)
        education_results = self.execute_query(education_levels_query)
        provinces_results = self.execute_query(provinces_query)

        # Function to create ID from label
        def create_id(label):
            return (
                label.lower()
                .replace(" ", "-")
                .replace("(", "")
                .replace(")", "")
                .replace("/", "-")
            )

        # Function to deduplicate by lowercase comparison
        def deduplicate_case_insensitive(results):
            unique_values = {}
            for result in results:
                value = result["value"]
                # Use lowercase version as key to detect duplicates
                lowercase_value = value.lower()
                # Only add if this lowercase value hasn't been seen yet
                if lowercase_value not in unique_values:
                    unique_values[lowercase_value] = value
            return unique_values.values()

        # Process employment types - deduplicate case-insensitive
        employment_options = []
        for value in deduplicate_case_insensitive(employment_results):
            employment_options.append(
                {"id": create_id(value), "label": value, "value": value}
            )

        # Process work setups - deduplicate case-insensitive
        work_setup_options = []
        for value in deduplicate_case_insensitive(work_setup_results):
            work_setup_options.append(
                {"id": create_id(value), "label": value, "value": value}
            )

        # Process education levels - deduplicate case-insensitive
        education_options = []
        for value in deduplicate_case_insensitive(education_results):
            education_options.append(
                {"id": create_id(value), "label": value, "value": value}
            )

        # Process provinces - deduplicate case-insensitive
        province_options = []
        for value in deduplicate_case_insensitive(provinces_results):
            province_options.append(
                {"id": create_id(value), "label": value, "value": value}
            )

        # Fixed experience options (tidak dari database)
        experience_options = [
            {
                "id": "no-experience",
                "label": "Tidak Berpengalaman",
                "min_exp": 0,
                "max_exp": 0,
            },
            {
                "id": "fresh-graduate",
                "label": "Fresh Graduate",
                "min_exp": 0,
                "max_exp": 1,
            },
            {
                "id": "less-than-year",
                "label": "Kurang dari setahun",
                "min_exp": 0,
                "max_exp": 1,
            },
            {"id": "1-3-years", "label": "1 - 3 tahun", "min_exp": 1, "max_exp": 3},
            {"id": "3-5-years", "label": "3 - 5 tahun", "min_exp": 3, "max_exp": 5},
            {"id": "5-10-years", "label": "5 - 10 tahun", "min_exp": 5, "max_exp": 10},
            {
                "id": "more-than-10",
                "label": "Lebih dari 10 tahun",
                "min_exp": 10,
                "max_exp": 99,
            },
        ]

        return {
            "jobTypes": employment_options,
            "workArrangements": work_setup_options,
            "experiences": experience_options,
            "educationLevels": education_options,
            "provinces": province_options,
        }

    # TAMBAH: Method khusus untuk mengambil provinces saja
    def get_provinces(self) -> List[Dict]:
        """Get all unique provinces from Job nodes"""
        provinces_query = """
            MATCH (j:Job)
            WHERE j.province IS NOT NULL AND j.province <> ''
            RETURN DISTINCT j.province as province
            ORDER BY j.province
        """

        results = self.execute_query(provinces_query)

        provinces = []
        for result in results:
            province = result["province"]
            provinces.append(
                {
                    "id": province.lower().replace(" ", "-"),
                    "label": province,
                    "value": province,
                }
            )

        return provinces

    def get_job_by_url_suffix(self, url: str) -> Dict:
        """Get job data from Neo4j database by URL suffix (last 36 characters)"""
        try:
            print(f"🔍 Searching for job with URL suffix: {url}")

            # Query untuk mencari job berdasarkan suffix dari job_url
            query = """
            MATCH (j:Job)
            WHERE j.jobUrl = $url
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(a:AdditionalSkill)
            WITH j, collect(DISTINCT s.name) as required_skills, collect(DISTINCT a.name) as additional_skills
            RETURN j.jobUrl as job_url, 
                   j.jobTitle as title, 
                   j.companyName as company_name,
                   j.city as city, 
                   j.province as province, 
                   j.imageUrl as image_url,
                   j.minimumSalary as minimum_salary, 
                   j.maximumSalary as maximum_salary,
                   j.salaryUnit as salary_unit, 
                   j.salaryType as salary_type,
                   j.employmentType as employment_type, 
                   j.workSetup as work_setup,
                   j.minimumEducation as minimum_education, 
                   j.minimumExperience as minimum_experience, 
                   j.maximumExperience as maximum_experience,
                   required_skills,
                   additional_skills,
                   j.jobDescription as job_description
            LIMIT 1
            """

            params = {"url": url}

            print(f"📝 Query: {query}")
            print(f"📊 Params: {params}")

            result = self.execute_query(query, params)

            if result and len(result) > 0:
                job_data = result[0]
                print(f"✅ Found job: {job_data.get('title', 'Unknown')}")
                required_skills = job_data.get("required_skills", []) or []
                additional_skills = job_data.get("additional_skills", []) or []
                all_skills = list({*required_skills, *additional_skills})

                # Transform data to match frontend format
                transformed_job = {
                    "job_url": job_data.get("job_url"),
                    "job_title": job_data.get("title"),
                    "company_name": job_data.get("company_name"),
                    "city": job_data.get("city"),
                    "province": job_data.get("province"),
                    "image_url": job_data.get("image_url"),
                    "minimum_salary": job_data.get("minimum_salary"),
                    "maximum_salary": job_data.get("maximum_salary"),
                    "salary_unit": job_data.get("salary_unit"),
                    "salary_type": job_data.get("salary_type"),
                    "employment_type": job_data.get("employment_type"),
                    "work_setup": job_data.get("work_setup"),
                    "minimum_education": job_data.get("minimum_education"),
                    "minimum_experience": job_data.get("minimum_experience"),
                    "maximum_experience": job_data.get("maximum_experience"),
                    "required_skills": all_skills,
                    "job_description": job_data.get("job_description"),
                }

                return transformed_job
            else:
                print(f"❌ No job found with URL suffix: {url}")
                return None

        except Exception as e:
            print(f"❌ Error getting job by URL suffix: {e}")
            import traceback

            traceback.print_exc()
            return None

    def delete_job_by_url(self, job_url: str) -> bool:
        """
        Hapus node Job (beserta semua relasinya) berdasarkan job_url
        """
        query = """
            MATCH (j:Job {jobUrl: $job_url})
            DETACH DELETE j
            RETURN COUNT(j) AS deleted_count
        """
        results = self.execute_write_query(query, {"job_url": job_url})
        return results and results[0].get("deleted_count", 0) > 0


# Global instance
job_service = JobService()
