import uuid

from django.contrib.auth.hashers import check_password, make_password
from neo4j import GraphDatabase, Transaction
from neomodel import db

from core.matchers.helper import update_task_progress
from core.matchers.SafeNeo4jBackupRestore import SafeNeo4jBackupRestore


def set_maintenance(is_maintenance: bool):
    """Set maintenance mode in Neo4j database"""
    uri = "bolt://host.docker.internal:7687"
    user = "neo4j"
    password = "12345678"
    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        result = session.run("MATCH (m:Maintenance) RETURN m LIMIT 1")
        record = result.single()

        if record is None:
            session.run(
                "CREATE (m:Maintenance {isMaintenance: $is_maintenance})",
                {"is_maintenance": is_maintenance},
            )
        else:
            session.run(
                "MATCH (m:Maintenance) SET m.isMaintenance = $is_maintenance",
                {"is_maintenance": is_maintenance},
            )


def get_users_from_neo4j():
    """Get users data from Neo4j database (real implementation)"""
    uri = "bolt://host.docker.internal:7687"
    user = "neo4j"
    password = "12345678"

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session() as session:
            query = """
            MATCH (u:User {role: 'user'})
            RETURN u.uid AS uid,
                    u.name AS name,
                    u.email AS email,
                    u.password AS password,
                    u.profilePicture AS profilePicture,
                    u.role AS role
            """

            result = session.run(query)
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

                skills_result = session.run(skills_query, email=user_data["email"])
                skills = [
                    record["skill_name"]
                    for record in skills_result
                    if record["skill_name"]
                ]
                user_data["skills"] = skills

            return users_list

    except Exception as e:
        print(f"❌ Error getting users from Neo4j: {e}")
        return []
    finally:
        driver.close()


def get_jobs_from_neo4j():
    """Get jobs data from Neo4j database"""

    uri = "bolt://host.docker.internal:7687"
    user = "neo4j"
    password = "12345678"

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session() as session:
            # Query untuk get semua jobs dengan skills yang required
            jobs_query = """
            MATCH (j:Job)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            RETURN j.jobUrl AS job_url,
                   j.jobTitle AS job_title,
                   j.companyName AS company_name,
                   j.subdistrict AS subdistrict,
                   j.city AS city,
                   j.province AS province,
                   j.minimumSalary AS minimum_salary,
                   j.maximumSalary AS maximum_salary,
                   j.employmentType AS employment_type,
                   j.workSetup AS work_setup,
                   j.minimumEducation AS minimum_education,
                   j.minimumExperience AS minimum_experience,
                   j.maximumExperience AS maximum_experience,
                   j.jobDescription AS job_description,
                   j.scrapedAt AS scraped_at,
                   collect(DISTINCT s.name) AS required_skills
            ORDER BY j.scrapedAt DESC
            """

            result = session.run(jobs_query)
            jobs_list = []

            for record in result:
                job_data = {
                    "job_url": record["job_url"],
                    "job_title": record["job_title"],
                    "company_name": record["company_name"],
                    "subdistrict": record["subdistrict"],
                    "city": record["city"],
                    "province": record["province"],
                    "minimum_salary": record["minimum_salary"],
                    "maximum_salary": record["maximum_salary"],
                    "employment_type": record["employment_type"],
                    "work_setup": record["work_setup"],
                    "minimum_education": record["minimum_education"],
                    "minimum_experience": record["minimum_experience"],
                    "maximum_experience": record["maximum_experience"],
                    "job_description": record["job_description"],
                    "scraped_at": record["scraped_at"],
                    "required_skills": [
                        skill for skill in record["required_skills"] if skill
                    ],  # Filter None values
                }

                # Keep all keys, only ensure required_skills is present (even if empty)
                if "required_skills" not in job_data:
                    job_data["required_skills"] = []

                jobs_list.append(job_data)

            print(jobs_list)
            return jobs_list

    except Exception as e:
        print(f"❌ Error getting jobs from Neo4j: {e}")
        print("   🔄 Falling back to empty jobs data...")
        return []
    finally:
        driver.close()


def update_neo4j_for_specific_user(user_email, user_skills, categorized_matches):
    """Update Neo4j hanya untuk specific user tanpa mengganggu user lain"""
    print(f"   💾 Updating Neo4j for {user_email}...")

    uri = "bolt://host.docker.internal:7687"
    user = "neo4j"
    password = "12345678"

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session(database="neo4j") as session:
            with session.begin_transaction() as tx:
                # 0. Ensure user exists first
                print("   👤 Ensuring user exists...")
                tx.run(
                    """
                    MERGE (u:User {email: $email})
                    """,
                    {"email": user_email},
                )

                # 1. Delete existing matches untuk user ini SAJA
                print("   🗑️ Removing existing matches for this user...")
                tx.run(
                    """
                    MATCH (u:User {email: $email})
                    OPTIONAL MATCH (m:UserJobMatch)-[:USER_MATCH]->(u)
                    DETACH DELETE m
                    """,
                    {"email": user_email},
                )

                # 2. Update user skills (remove old, add new)
                print("   🔧 Updating user skills...")
                # Remove existing skills
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

                print(f"   ✅ Added {skills_added} skills")

                # 3. Add new categorized matches
                print(f"   ➕ Adding {len(categorized_matches)} new matches...")
                matches_added = 0

                for match in categorized_matches:
                    # Extract job URL from match graph
                    job_uri = match.get("job_uri", "")
                    similarity = match["similarity"]
                    category = match["category"]

                    job_identifier = job_uri.split("/")[-1] if job_uri else ""
                    job_identifier = job_identifier.split("_")[1]

                    if not job_identifier:
                        print(f"   ⚠️ Skipping match with empty job identifier")
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
                    else:
                        print(f"   ⚠️ Failed to create match for job: {job_identifier}")

                print(f"   ✅ Successfully added {matches_added} matches")

                # 4. Verification - show final stats dengan detail relasi
                verification_result = tx.run(
                    """
                    MATCH (u:User {email: $email})
                    OPTIONAL MATCH (u)-[:HAS_SKILL]->(s:Skill)
                    OPTIONAL MATCH (m:UserJobMatch)-[:USER_MATCH]->(u)
                    OPTIONAL MATCH (m)-[:JOB_MATCH]->(j:Job)
                    RETURN count(DISTINCT s) AS skills_count, 
                           count(DISTINCT m) AS matches_count,
                           count(DISTINCT j) AS jobs_matched_count
                    """,
                    {"email": user_email},
                )
                stats = verification_result.single()

                print(f"   📊 Final verification:")
                print(f"     User: {user_email}")
                print(f"     Skills: {stats['skills_count']}")
                print(f"     Matches: {stats['matches_count']}")
                print(f"     Jobs matched: {stats['jobs_matched_count']}")

                # Additional check - verify relasi USER_MATCH exists
                relation_check = tx.run(
                    """
                    MATCH (u:User {email: $email})
                    MATCH (m:UserJobMatch)-[:USER_MATCH]->(u)
                    RETURN count(m) as user_match_relations
                    """,
                    {"email": user_email},
                )

                relation_count = relation_check.single()["user_match_relations"]
                print(f"     USER_MATCH relations: {relation_count}")

                if relation_count == 0:
                    print("   ❌ WARNING: No USER_MATCH relations found!")
                else:
                    print("   ✅ USER_MATCH relations verified")

                tx.commit()

    except Exception as e:
        print(f"   ❌ Error updating Neo4j: {e}")
        import traceback

        print(f"   Stack trace: {traceback.format_exc()}")
        tx.rollback()
    finally:
        driver.close()


def create_calculated_user(new_user_data, categorized_matches):
    """Update Neo4j hanya untuk specific user tanpa mengganggu user lain"""
    print(f"   💾 Updating Neo4j for {new_user_data["email"]}...")

    uri = "bolt://host.docker.internal:7687"
    user = "neo4j"
    password = "12345678"

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session(database="neo4j") as session:
            with session.begin_transaction() as tx:
                # 1. Create/Update user with all properties
                print("   👤 Creating/updating user...")
                tx.run(
                    """
                    MERGE (u:User {email: $email})
                    SET u.uid = $uid,
                        u.name = $name,
                        u.password = $password,
                        u.role = $role
                    """,
                    {
                        "uid": new_user_data["uid"],
                        "name": new_user_data["name"],
                        "email": new_user_data["email"],
                        "password": new_user_data["password"],
                        "role": new_user_data["role"],
                    },
                )

                # 2. Add new skills
                print(f"   🔧 Adding {len(new_user_data['skills'])} skills...")
                skills_added = 0
                for skill in new_user_data["skills"]:
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
                        {"email": new_user_data["email"], "skill_name": skill},
                    )

                    if result.single()["added"] > 0:
                        skills_added += 1

                print(f"   ✅ Added {skills_added} skills")

                # 3. Add new categorized matches
                print(f"   ➕ Adding {len(categorized_matches)} new matches...")
                matches_added = 0

                for match in categorized_matches:
                    # Extract job URL from match graph
                    job_uri = match.get("job_uri", "")
                    similarity = match["similarity"]
                    category = match["category"]

                    job_identifier = job_uri.split("/")[-1] if job_uri else ""
                    job_identifier = job_identifier.split("_")[1]

                    if not job_identifier:
                        print(f"   ⚠️ Skipping match with empty job identifier")
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
                            "email": new_user_data["email"],
                            "job_identifier": job_identifier,
                            "similarity": similarity,
                            "category": category,
                        },
                    )

                    created_count = result.single()["created"]
                    if created_count > 0:
                        matches_added += 1
                    else:
                        print(f"   ⚠️ Failed to create match for job: {job_identifier}")

                print(f"   ✅ Successfully added {matches_added} matches")

                # 3.5. Create UploadFile node for profile image
                print("   📁 Creating UploadFile node for profile image...")
                if new_user_data.get("profile_image"):
                    tx.run(
                        """
                        MATCH (u:User {email: $email})
                        SET u.profilePicture = $profile_image
                        """,
                        {
                            "email": new_user_data["email"],
                            "profile_image": new_user_data["profile_image"],
                        },
                    )
                else:
                    print(
                        "   ⚠️ No profile image provided, skipping UploadFile creation"
                    )

                tx.commit()

                skills = []

                with driver.session(database="neo4j") as session:
                    result = session.run(
                        """
                            MATCH (u:User {email: $email})-[:HAS_SKILL]->(s:Skill)
                            RETURN collect(s.name) AS skills
                        """,
                        {"email": new_user_data["email"]},
                    )
                    record = result.single()
                    if record and record.get("skills"):
                        skills = record["skills"]

                return {
                    "uid": new_user_data["uid"],
                    "name": new_user_data["name"],
                    "email": new_user_data["email"],
                    "password": new_user_data["password"],
                    "profile_image": new_user_data.get("profile_image"),
                    "role": new_user_data["role"],
                    "skills": skills,
                }

    except Exception as e:
        print(f"   ❌ Error updating Neo4j: {e}")
        import traceback

        print(f"   Stack trace: {traceback.format_exc()}")
        tx.rollback()
        return None
    finally:
        driver.close()


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
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Strong_Match"
    ]
    
    # Step 1: Add Skill label to Class nodes except excluded URIs
    tx.run(
        """
        MATCH (n:Class) 
        WHERE NOT n.uri IN $excluded_uris
        SET n:Skill
        """,
        {"excluded_uris": excluded_uris}
    )
    
    # Step 2: Add name property based on URI
    base_uri = "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/"
    tx.run(
        """
        MATCH (n:Skill) 
        WHERE n.uri STARTS WITH $base_uri
        WITH n, replace(n.uri, $base_uri, '') as extracted_name
        SET n.name = replace(extracted_name, '_', ' ')
        """,
        {"base_uri": base_uri}
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
    print("🔄 Converting match category labels to matchType property...")

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
    print(f"   ✅ Converted match labels to properties:")
    print(f"     Strong → strong: {strong_count}")
    print(f"     Mid → mid: {mid_count}")
    print(f"     Weak → weak: {weak_count}")
    print(f"     Total converted: {total_converted}")

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

                    print("🔄 Safely restoring backed up data...")
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
                    print(f"❌ Error during Neo4j import and cleanup: {e}")
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

            print(f"✅ Neo4j import and cleanup completed successfully!")
    except Exception as e:
        print(f"❌ Error during Neo4j processing: {e}")
        raise
    finally:
        driver.close()
