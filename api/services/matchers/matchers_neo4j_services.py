from neo4j import GraphDatabase, Transaction
from neomodel import db

from api.models import Job, Skill, User, UserJobMatch
from api.services.matchers.helper import update_task_progress
from api.services.matchers.SafeNeo4jBackupRestore import SafeNeo4jBackupRestore


def get_users_from_neo4j():
    query = """
    MATCH (u:User {role: 'user'})
    RETURN u.uid AS uid,
            u.name AS name,
            u.email AS email,
            u.password AS password,
            u.profilePicture AS profilePicture,
            u.role AS role
    """

    result = db.cypher_query(query)
    users_list = []

    for record in result:
        user_data = {
            "uid": record["uid"],
            "name": record["name"],
            "email": record["email"],
            "password": record["password"],
            "profilePicture": record["profilePicture"],
            "role": record["role"],
            "skills": [],
        }

        user_data = {k: v for k, v in user_data.items() if v is not None}

        users_list.append(user_data)

    # Get skills for each user from User-Skill relationships
    for user_data in users_list:
        skills_query = """
        MATCH (u:User {email: $email})-[:HAS_SKILL]->(s:Skill)
        RETURN s.name AS skill_name
        ORDER BY s.name
        """

        skills_result = db.cypher_query(skills_query, email=user_data["email"])
        skills = [
            record["skill_name"] for record in skills_result if record["skill_name"]
        ]
        user_data["skills"] = skills

    return users_list


def get_jobs_from_neo4j():
    """Get jobs data from Neo4j database"""
    jobs = Job.all_with_skills()
    jobs_list = []
    for item in jobs:
        job = item["job"]
        skills = [skill.name for skill in item["skills"]]
        job_data = {
            "job_url": job.jobUrl,
            "job_title": job.jobTitle,
            "company_name": job.companyName,
            "subdistrict": job.subdistrict,
            "city": job.city,
            "province": job.province,
            "minimum_salary": job.minimumSalary,
            "maximum_salary": job.maximumSalary,
            "employment_type": job.employmentType,
            "work_setup": job.workSetup,
            "minimum_education": job.minimumEducation,
            "minimum_experience": job.minimumExperience,
            "maximum_experience": job.maximumExperience,
            "job_description": job.jobDescription,
            "scraped_at": job.scrapedAt,
            "required_skills": skills,
        }
        jobs_list.append(job_data)
    return jobs_list


def update_neo4j_for_specific_user(user_email, user_skills, categorized_matches):
    """Update Neo4j hanya untuk specific user tanpa mengganggu user lain"""
    uri = "bolt://host.docker.internal:7687"
    user = "neo4j"
    password = "12345678"

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session(database="neo4j") as session:
            with session.begin_transaction() as tx:
                # 0. Ensure user exists first
                tx.run(
                    """
                    MERGE (u:User {email: $email})
                    """,
                    {"email": user_email},
                )

                # 1. Delete existing matches untuk user ini SAJA
                tx.run(
                    """
                    MATCH (u:User {email: $email})
                    OPTIONAL MATCH (m:UserJobMatch)-[:USER_MATCH]->(u)
                    DETACH DELETE m
                    """,
                    {"email": user_email},
                )

                # 2. Update user skills (remove old, add new)
                tx.run(
                    """
                    MATCH (u:User {email: $email})
                    OPTIONAL MATCH (u)-[r:HAS_SKILL]->()
                    DELETE r
                    """,
                    {"email": user_email},
                )

                # Add new skills
                skills_added = 0
                for skill in user_skills:
                    if not skill or not skill.strip():  # Skip empty skills
                        continue

                    result = tx.run(
                        """
                        MATCH (u:User {email: $email})
                        MATCH (s:Skill) 
                        WHERE toLower(s.name) = toLower($skill_name)
                        MERGE (u)-[:HAS_SKILL]->(s)
                        RETURN count(*) as added
                        """,
                        {"email": user_email, "skill_name": skill},
                    )

                    if result.single()["added"] > 0:
                        skills_added += 1

                # 3. Add new categorized matches
                matches_added = 0

                for match in categorized_matches:
                    # Extract job URL from match graph
                    job_uri = match.get("job_uri", "")
                    similarity = match["similarity"]
                    category = match["category"]

                    job_identifier = job_uri.split("/")[-1] if job_uri else ""
                    job_identifier = job_identifier.split("_")[1]

                    if not job_identifier:
                        continue

                    # Create match node dan pastikan relasi dibuat dengan benar
                    result = tx.run(
                        """
                        MATCH (u:User {email: $email})
                        MATCH (j:Job) 
                        WHERE j.jobUrl CONTAINS $job_identifier
                        CREATE (m:UserJobMatch)
                        SET m.similarityScore = $similarity,
                            m.matchType = $category
                        CREATE (m)-[:USER_MATCH]->(u)
                        CREATE (m)-[:JOB_MATCH]->(j)
                        RETURN count(*) as created
                        """,
                        {
                            "email": user_email,
                            "job_identifier": job_identifier,
                            "similarity": similarity,
                            "category": category,
                        },
                    )

                    created_count = result.single()["created"]
                    if created_count > 0:
                        matches_added += 1

                tx.commit()
    except Exception as e:
        tx.rollback()
    finally:
        driver.close()


def create_calculated_user(new_user_data, categorized_matches):
    """Update Neo4j hanya untuk specific user tanpa mengganggu user lain"""
    db.begin()
    print("Creating user with data:", new_user_data)
    try:
        # 1. Create/Update user with all properties
        user = User(
            uid=new_user_data["uid"],
            name=new_user_data["name"],
            email=new_user_data["email"],
            password=new_user_data["password"],
            role=new_user_data["role"],
            profilePicture=new_user_data.get("profile_image", None),
        )
        user.save()

        print("User created:", user.uid)

        # 2. Add new skills
        skills_added = 0
        for skill_name in new_user_data["skills"]:
            if not skill_name or not skill_name.strip():  # Skip empty skills
                continue

            skill = Skill.nodes.filter(name__iexact=skill_name).first()
            if skill:
                user.has_skill.connect(skill)
                skills_added += 1

        print(f"Skills added: {skills_added}")

        # 3. Add new categorized matches
        matches_added = 0
        for match in categorized_matches:
            # Extract job URL from match graph
            job_uri = match.get("job_uri", "")
            similarity = match["similarity"]
            category = match["category"]

            job_identifier = job_uri.split("/")[-1] if job_uri else ""
            job_identifier = job_identifier.split("_")[1]

            if not job_identifier:
                continue

            # Find job by URL containing identifier
            job = Job.nodes.filter(jobUrl__contains=job_identifier).first()
            if job:
                # Create UserJobMatch
                user_job_match = UserJobMatch(
                    similarityScore=similarity, matchType=category
                )
                user_job_match.save()

                # Connect to user and job
                user_job_match.user_match.connect(user)
                user_job_match.job_match.connect(job)
                matches_added += 1

        db.commit()
    except Exception as e:
        db.rollback()
        return None

    # 4. Return the created user data with connected skills
    connected_skills = [skill.name for skill in user.has_skill.all()]

    return {
        "uid": user.uid,
        "name": user.name,
        "email": user.email,
        "password": user.password,
        "profile_image": user.profilePicture,
        "role": user.role,
        "skills": connected_skills,
    }


def import_to_neo4j_from_graph(tx: Transaction, graph):
    tx.run("MATCH (n) DETACH DELETE n")

    config = {
        "handleVocabUris": "IGNORE",
        "handleRDFTypes": "LABELS",
        "keepLangTag": False,
        "applyNeo4jNaming": False,
        "keepCustomDataTypes": True,
    }
    tx.run("CALL n10s.graphconfig.init($config)", config=config)

    turtle_data = graph.serialize(format="turtle")

    tx.run(
        "CALL n10s.rdf.import.inline($rdf_data, 'Turtle')",
        rdf_data=turtle_data,
    )


def clean_up_neo4j(tx: Transaction):
    labels_to_remove = [
        "Datatype",
        "ObjectProperty",
        "DatatypeProperty",
        "Restriction",
        "NamedIndividual",
        "Ontology",
        "Class",
    ]

    relationship_types_to_delete = [
        "domain",
        "range",
        "rest",
        "first",
        "withRestrictions",
        "onDatatype",
        "equivalentClass",
        "onProperty",
        "someValuesFrom",
        "intersectionOf",
        "subClassOf",
    ]

    for label in labels_to_remove:
        tx.run(f"MATCH (n:{label}) REMOVE n:{label} RETURN count(*) AS removed")

    for rel_type in relationship_types_to_delete:
        tx.run(f"MATCH ()-[r:{rel_type}]->() DELETE r RETURN count(*) AS deleted")


def fix_resource_nodes_to_skills(tx: Transaction):
    # URIs to exclude from Skill labeling
    excluded_uris = [
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Job",
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/User",
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Skills",
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/UserJobMatch",
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Mid_Match",
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Weak_Match",
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Strong_Match",
    ]

    # Step 1: Add Skill label to Class nodes except excluded URIs
    tx.run(
        """
        MATCH (n:Class) 
        WHERE NOT n.uri IN $excluded_uris
        SET n:Skill
        """,
        {"excluded_uris": excluded_uris},
    )

    # Step 2: Add name property based on URI
    base_uri = (
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/"
    )
    tx.run(
        """
        MATCH (n:Skill) 
        WHERE n.uri STARTS WITH $base_uri
        WITH n, replace(n.uri, $base_uri, '') as extracted_name
        SET n.name = replace(extracted_name, '_', ' ')
        """,
        {"base_uri": base_uri},
    )


def remove_all_resource_labels_and_uris(tx: Transaction):
    tx.run(
        """
        MATCH (n:Resource)
        REMOVE n:Resource
        RETURN count(n) AS removed
        """
    )

    tx.run(
        """
        MATCH (n)
        WHERE n.uri IS NOT NULL
        REMOVE n.uri
        RETURN count(n) AS removed
        """
    )


def convert_match_labels_to_property(tx: Transaction):
    """Convert UserJobMatch category labels to matchType property"""
    # Convert Strong_Match labels to property
    strong_result = tx.run(
        """
        MATCH (m:UserJobMatch:Strong_Match)
        REMOVE m:Strong_Match
        SET m.matchType = 'Strong'
        RETURN count(m) AS converted
    """
    )
    strong_count = strong_result.single()["converted"]

    # Convert Mid_Match labels to property
    mid_result = tx.run(
        """
        MATCH (m:UserJobMatch:Mid_Match)
        REMOVE m:Mid_Match
        SET m.matchType = 'Mid'
        RETURN count(m) AS converted
    """
    )
    mid_count = mid_result.single()["converted"]

    # Convert Weak_Match labels to property
    weak_result = tx.run(
        """
        MATCH (m:UserJobMatch:Weak_Match)
        REMOVE m:Weak_Match
        SET m.matchType = 'Weak'
        RETURN count(m) AS converted
    """
    )
    weak_count = weak_result.single()["converted"]

    total_converted = strong_count + mid_count + weak_count

    return {
        "strong": strong_count,
        "mid": mid_count,
        "weak": weak_count,
        "total": total_converted,
    }


def import_and_clean_neo4j_with_enrichment(
    graph,
    users_data=None,
    jobs_data=None,
    missing_skills_map=None,
    task_id=None,
    update_state_func=None,
):
    uri = "bolt://host.docker.internal:7687"
    user = "neo4j"
    password = "12345678"

    driver = GraphDatabase.driver(uri, auth=(user, password))
    backup_system = SafeNeo4jBackupRestore(driver)

    backup_config = {
        "node_labels": [
            "User",
            "ScrapingTask",
            "MatchingTask",
            "Maintenance",
        ],
        "relationship_types": ["TRIGGERED_BY", "HAS_PROCESS"],
        "nodes_with_relationships": [],
    }

    try:
        backup_data = backup_system.safe_full_dynamic_backup(backup_config)

        with driver.session() as session:
            session.run(
                "CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS FOR (r:Resource) REQUIRE r.uri IS UNIQUE"
            )

            with session.begin_transaction() as tx:
                try:
                    if update_state_func:
                        update_task_progress(
                            task_id,
                            "IMPORTING_DATA_WITH_NEOSEMANTICS",
                            {},
                            update_state_func,
                        )

                    import_to_neo4j_from_graph(tx, graph)

                    if update_state_func:
                        update_task_progress(
                            task_id,
                            "FINISHING_DATA",
                            {},
                            update_state_func,
                        )
                    fix_resource_nodes_to_skills(tx)
                    clean_up_neo4j(tx)
                    remove_all_resource_labels_and_uris(tx)
                    convert_match_labels_to_property(tx)

                    backup_system.safe_full_dynamic_restore_with_enrichment(
                        backup_data, tx, users_data, jobs_data
                    )

                    for job_url, missing_skills in missing_skills_map.items():
                        for skill in missing_skills:
                            tx.run(
                                """
                                MATCH (j:Job {jobUrl: $job_url})
                                CREATE (s:AdditionalSkill {name: $skill})
                                CREATE (j)-[:REQUIRED_SKILL]->(s)
                                """,
                                {"job_url": job_url, "skill": skill},
                            )

                    tx.commit()
                except Exception as e:
                    raise

            session.run("CREATE INDEX IF NOT EXISTS FOR (j:Job) ON (j.jobUrl)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.email)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (s:Skill) ON (s.name)")
            session.run(
                "CREATE INDEX IF NOT EXISTS FOR (s:AdditionalSkill) ON (s.name)"
            )
            session.run(
                "CREATE INDEX IF NOT EXISTS FOR (ujm:UserJobMatch) ON (ujm.matchType)"
            )
    except Exception as e:
        raise
    finally:
        driver.close()
