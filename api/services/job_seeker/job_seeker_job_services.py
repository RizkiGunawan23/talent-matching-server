from typing import Dict, List
from neomodel import db
from api.models import Job


def get_filter_options() -> Dict[str, List[Dict]]:
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
    employment_results = db.cypher_query(employment_types_query)[0]
    work_setup_results = db.cypher_query(work_setups_query)[0]
    education_results = db.cypher_query(education_levels_query)[0]
    provinces_results = db.cypher_query(provinces_query)[0]
    
    # Convert results to dictionaries
    employment_results = [{"value": row[0]} for row in employment_results]
    work_setup_results = [{"value": row[0]} for row in work_setup_results]
    education_results = [{"value": row[0]} for row in education_results]
    provinces_results = [{"value": row[0]} for row in provinces_results]

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


def get_job_provinces() -> List[Dict]:
    """Get all unique provinces from Job nodes with case-insensitive deduplication"""
    provinces_query = """
        MATCH (j:Job)
        WHERE j.province IS NOT NULL AND j.province <> ''
        RETURN DISTINCT j.province as province
        ORDER BY j.province
    """

    # Execute query
    provinces_results = db.cypher_query(provinces_query)[0]
    
    # Convert results to dictionaries
    provinces_results = [{"province": row[0]} for row in provinces_results]
    
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
            value = result["province"]
            # Use lowercase version as key to detect duplicates
            lowercase_value = value.lower()
            # Only add if this lowercase value hasn't been seen yet
            if lowercase_value not in unique_values:
                unique_values[lowercase_value] = value
        return unique_values.values()

    # Process provinces - deduplicate case-insensitive
    province_options = []
    for value in deduplicate_case_insensitive(provinces_results):
        province_options.append(
            {
                "id": create_id(value),
                "label": value,
                "value": value,
            }
        )

    return province_options

def search_jobs(filters: Dict) -> List[Dict]:
    """Get jobs with filters applied"""
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

    # Query with all fields from Job node
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

    # Execute query and get results
    results, _ = db.cypher_query(query, parameters)
    
    # Column names from the query
    columns = [
        'uid', 'job_url', 'job_title', 'company_name', 'city', 'province', 'subdistrict', 
        'minimum_salary', 'maximum_salary', 'salary_unit', 'salary_type', 'employment_type', 
        'work_setup', 'minimum_education', 'minimum_experience', 'maximum_experience', 
        'image_url', 'job_description', 'required_skills', 'additional_skills'
    ]
    
    # Convert results to dictionaries
    result_dicts = []
    for row in results:
        result_dict = {columns[i]: row[i] for i in range(len(columns))}
        
        # Merge skills and remove duplicates
        required_skills = result_dict.get("required_skills", []) or []
        additional_skills = result_dict.get("additional_skills", []) or []
        all_skills = list({*required_skills, *additional_skills})
        
        result_dict["required_skills"] = all_skills
        result_dict.pop("additional_skills", None)  # Remove additional_skills from final result
        result_dicts.append(result_dict)
        
    return result_dicts

def get_job_by_url(url: str) -> Dict:
    """Get job data from Neo4j database by URL"""
    try:
        # Use neomodel to get the job
        job = Job.nodes.filter(jobUrl=url).first()
        
        if not job:
            return None
            
        # Get related skills
        skills_query = """
            MATCH (j:Job {jobUrl: $job_url})
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(a:AdditionalSkill)
            RETURN collect(DISTINCT s.name) as required_skills, collect(DISTINCT a.name) as additional_skills
        """
        
        results, _ = db.cypher_query(skills_query, {"job_url": url})
        required_skills = results[0][0] if results and results[0][0] else []
        additional_skills = results[0][1] if results and results[0][1] else []
        all_skills = list({*required_skills, *additional_skills})
        
        # Transform to frontend format
        job_data = {
            "job_url": job.jobUrl,
            "job_title": job.jobTitle,
            "company_name": job.companyName,
            "city": job.city,
            "province": job.province,
            "image_url": job.imageUrl,
            "minimum_salary": job.minimumSalary,
            "maximum_salary": job.maximumSalary,
            "salary_unit": getattr(job, "salaryUnit", None),
            "salary_type": getattr(job, "salaryType", None),
            "employment_type": job.employmentType,
            "work_setup": job.workSetup,
            "minimum_education": job.minimumEducation,
            "minimum_experience": job.minimumExperience,
            "maximum_experience": job.maximumExperience,
            "required_skills": all_skills,
            "job_description": job.jobDescription,
        }
        return job_data
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None

def get_job_recommendations(user_email: str, filters: Dict = None) -> List[Dict]:
    """Get job matches for a user with filtering options"""
    # Default filters
    if filters is None:
        filters = {}
    
    # Note: job and location filters not used as requested
    job_types = filters.get('jobTypes', [])
    work_arrangements = filters.get('workArrangements', [])
    education_levels = filters.get('educationLevels', [])
    experiences = filters.get('experiences', [])
    salary_min = filters.get('salaryMin', '')
    salary_max = filters.get('salaryMax', '')
    sort_order = filters.get('sortOrder', 'similarity-desc')
    
    # Build ORDER BY clause based on sort_order
    if sort_order == 'similarity-asc':
        order_clause = "ORDER BY m.similarityScore ASC"
    else:  # default to similarity-desc
        order_clause = "ORDER BY m.similarityScore DESC"
    
    # Build Cypher query with optional filters
    filter_conditions = []
    params = {"email": user_email}
    
    query = """
        MATCH (m:UserJobMatch)-[:USER_MATCH]->(u:User {email: $email})
        MATCH (m)-[:JOB_MATCH]->(j:Job)
    """
    
    # Add job type filter
    if job_types and len(job_types) > 0:
        filter_conditions.append("j.employmentType IN $job_types")
        params["job_types"] = job_types
        
    # Add work arrangement filter
    if work_arrangements and len(work_arrangements) > 0:
        filter_conditions.append("j.workSetup IN $work_setups")
        params["work_setups"] = work_arrangements
        
    # Add education level filter
    if education_levels and len(education_levels) > 0:
        filter_conditions.append("j.minimumEducation IN $education_levels")
        params["education_levels"] = education_levels
        
    # Add experience filter
    if experiences and len(experiences) > 0:
        exp_conditions = []
        
        for exp in experiences:
            if exp == "no-experience":
                exp_conditions.append("(j.minimumExperience = 0 OR j.minimumExperience IS NULL)")
            elif exp == "fresh-graduate":
                exp_conditions.append("(j.minimumExperience <= 1 OR j.minimumExperience IS NULL)")
            elif exp == "less-than-year":
                exp_conditions.append("(j.minimumExperience < 1 OR j.minimumExperience IS NULL)")
            elif exp == "1-3-years":
                exp_conditions.append("(j.minimumExperience >= 1 AND j.minimumExperience <= 3)")
            elif exp == "3-5-years":
                exp_conditions.append("(j.minimumExperience >= 3 AND j.minimumExperience <= 5)")
            elif exp == "5-10-years":
                exp_conditions.append("(j.minimumExperience >= 5 AND j.minimumExperience <= 10)")
            elif exp == "more-than-10":
                exp_conditions.append("(j.minimumExperience > 10)")
                
        if exp_conditions:
            filter_conditions.append("(" + " OR ".join(exp_conditions) + ")")
    
    # Add salary filters
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
    query += order_clause
    
    # Execute query
    try:
        results, _ = db.cypher_query(query, params)
        
        # Column names from the query
        columns = [
            'job_url', 'job_title', 'company_name', 'city', 'province', 
            'image_url', 'minimum_salary', 'maximum_salary', 'salary_unit', 
            'salary_type', 'employment_type', 'work_setup', 'minimum_education',
            'minimum_experience', 'maximum_experience', 'required_skills', 
            'job_description', 'similarity_score', 'match_type'
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
        return []