from neo4j import GraphDatabase, Transaction
from neomodel import db

from api.models import Job, Skill, User, UserJobMatch
from api.services.matchers.helper import update_task_progress


def get_users_from_neo4j():
    """Get users data using neomodel ORM"""
    # Get all users with role 'user'
    users = User.nodes.filter(role="user")
    users_list = []

    for user in users:
        user_data = {
            "uid": user.uid,
            "name": user.name,
            "email": user.email,
            "password": user.password,
            "profilePicture": user.profilePicture,
            "role": user.role,
            "skills": [],
        }

        # Remove None values
        user_data = {k: v for k, v in user_data.items() if v is not None}

        # Get skills for this user using ORM relationship
        try:
            skills = user.has_skill.all()
            user_data["skills"] = [skill.name for skill in skills if skill.name]
        except Exception as e:
            print(
                f"[GET_USERS_ERROR] Failed to get skills for user {user.email}: {str(e)}"
            )
            user_data["skills"] = []

        users_list.append(user_data)

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
    db.begin()
    try:
        # 1. Ensure user exists first
        user: User | None = User.nodes.get_or_none(email=user_email)
        if not user:
            print(f"[UPDATE_USER_ERROR] User with email {user_email} not found")
            db.rollback()
            return

        deleted_matches = 0
        user_job_matches = UserJobMatch.nodes.all()
        for match in user_job_matches:
            # Check if this match is connected to our user
            connected_users = match.user_match.all()
            for connected_user in connected_users:
                if connected_user.email == user_email:
                    # Disconnect relationships first
                    match.user_match.disconnect_all()
                    match.job_match.disconnect_all()
                    # Delete the match node
                    match.delete()
                    deleted_matches += 1
                    break

        # 3. Remove existing skills relationships
        user.has_skill.disconnect_all()
        print(f"[UPDATE_USER_INFO] Disconnected all existing skills for {user_email}")

        # 4. Add new skills using ORM
        skills_added = 0
        for skill_name in user_skills:
            if not skill_name or not skill_name.strip():  # Skip empty skills
                continue

            try:
                # Find skill using case-insensitive search
                skill = Skill.nodes.filter(name__iexact=skill_name.strip()).first()
                if skill:
                    user.has_skill.connect(skill)
                    skills_added += 1
                else:
                    print(
                        f"[UPDATE_USER_WARNING] Skill '{skill_name}' not found in database"
                    )
            except Exception as e:
                print(
                    f"[UPDATE_USER_ERROR] Error connecting skill '{skill_name}': {str(e)}"
                )

        print(f"[UPDATE_USER_INFO] Added {skills_added} skills for {user_email}")

        # 5. Add new categorized matches
        matches_added = 0
        for match in categorized_matches:
            try:
                # Extract job URL from match graph
                job_uri = match.get("job_uri", "")
                similarity = match["similarity"]
                category = match["category"]

                if not job_uri:
                    print(f"[UPDATE_USER_WARNING] No job_uri found in match: {match}")
                    continue

                job_identifier = job_uri.split("/")[-1] if job_uri else ""
                if "_" in job_identifier:
                    job_identifier = job_identifier.split("_")[1]

                if not job_identifier:
                    print(
                        f"[UPDATE_USER_WARNING] Could not extract job identifier from {job_uri}"
                    )
                    continue

                # Find job using ORM with URL containing identifier
                job = None
                try:
                    # Try exact match first
                    jobs = Job.nodes.filter(jobUrl__contains=job_identifier)
                    job = jobs.first()
                except Exception as e:
                    print(
                        f"[UPDATE_USER_ERROR] Error finding job with identifier '{job_identifier}': {str(e)}"
                    )

                if not job:
                    print(
                        f"[UPDATE_USER_WARNING] Job not found for identifier '{job_identifier}'"
                    )
                    continue

                # Create UserJobMatch using ORM
                user_job_match = UserJobMatch(
                    similarityScore=similarity, matchType=category
                )
                user_job_match.save()

                # Connect to user and job using ORM relationships
                user_job_match.user_match.connect(user)
                user_job_match.job_match.connect(job)
                matches_added += 1
            except Exception as e:
                print(f"[UPDATE_USER_ERROR] Error processing match {match}: {str(e)}")
                continue

        print(f"[UPDATE_USER_INFO] Added {matches_added} matches for {user_email}")

        # Commit the transaction
        db.commit()
        print(
            f"[UPDATE_USER_SUCCESS] Successfully updated user {user_email}: {skills_added} skills, {matches_added} matches"
        )
    except Exception as e:
        print(f"[UPDATE_USER_ERROR] Fatal error updating user {user_email}: {str(e)}")
        db.rollback()
        raise


def create_calculated_user(new_user_data, categorized_matches):
    """Update Neo4j hanya untuk specific user tanpa mengganggu user lain"""
    db.begin()
    print(f"[CREATE_USER_INFO] Creating user with data: {new_user_data}")

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


def import_to_neo4j_from_graph(graph):
    """Import RDF graph to Neo4j using neosemantics - NO TRANSACTION WRAPPER"""
    try:
        print("[IMPORT_INFO] Starting graph import to Neo4j")

        # Clear existing data
        db.cypher_query("MATCH (n) DETACH DELETE n")
        print("[IMPORT_INFO] Cleared existing data")

        # Configure neosemantics
        config = {
            "handleVocabUris": "IGNORE",
            "handleRDFTypes": "LABELS",
            "keepLangTag": False,
            "applyNeo4jNaming": False,
            "keepCustomDataTypes": True,
        }
        db.cypher_query("CALL n10s.graphconfig.init($config)", {"config": config})
        print("[IMPORT_INFO] Configured neosemantics")

        # Serialize graph and import
        turtle_data = graph.serialize(format="turtle")
        db.cypher_query(
            "CALL n10s.rdf.import.inline($rdf_data, 'Turtle')",
            {"rdf_data": turtle_data},
        )
        print("[IMPORT_SUCCESS] Graph imported successfully")

    except Exception as e:
        print(f"[IMPORT_ERROR] Failed to import graph: {str(e)}")
        raise


def clean_up_neo4j():
    """Clean up Neo4j nodes and relationships - NO TRANSACTION WRAPPER"""
    try:
        print("[CLEANUP_INFO] Starting Neo4j cleanup")

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

        # Remove labels
        for label in labels_to_remove:
            result, _ = db.cypher_query(
                f"MATCH (n:{label}) REMOVE n:{label} RETURN count(n) AS removed"
            )
            removed_count = result[0][0] if result else 0
            print(f"[CLEANUP_INFO] Removed {removed_count} {label} labels")

        # Delete relationship types
        for rel_type in relationship_types_to_delete:
            result, _ = db.cypher_query(
                f"MATCH ()-[r:{rel_type}]->() DELETE r RETURN count(r) AS deleted"
            )
            deleted_count = result[0][0] if result else 0
            print(f"[CLEANUP_INFO] Deleted {deleted_count} {rel_type} relationships")

        print("[CLEANUP_SUCCESS] Neo4j cleanup completed")

    except Exception as e:
        print(f"[CLEANUP_ERROR] Failed to clean up Neo4j: {str(e)}")
        raise


def fix_resource_nodes_to_skills():
    """Fix resource nodes to skills - NO TRANSACTION WRAPPER"""
    try:
        print("[FIX_SKILLS_INFO] Starting resource nodes to skills conversion")

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
        result, _ = db.cypher_query(
            """
            MATCH (n:Class) 
            WHERE NOT n.uri IN $excluded_uris
            SET n:Skill
            RETURN count(n) AS converted
            """,
            {"excluded_uris": excluded_uris},
        )
        converted_count = result[0][0] if result else 0
        print(f"[FIX_SKILLS_INFO] Converted {converted_count} Class nodes to Skill")

        # Step 2: Add name property based on URI
        base_uri = "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/"
        result, _ = db.cypher_query(
            """
            MATCH (n:Skill) 
            WHERE n.uri STARTS WITH $base_uri
            WITH n, replace(n.uri, $base_uri, '') as extracted_name
            SET n.name = replace(extracted_name, '_', ' ')
            RETURN count(n) AS updated
            """,
            {"base_uri": base_uri},
        )
        updated_count = result[0][0] if result else 0
        print(f"[FIX_SKILLS_INFO] Updated {updated_count} Skill nodes with names")

        print("[FIX_SKILLS_SUCCESS] Resource nodes to skills conversion completed")

    except Exception as e:
        print(f"[FIX_SKILLS_ERROR] Failed to fix resource nodes to skills: {str(e)}")
        raise


def remove_all_resource_labels_and_uris():
    """Remove resource labels and URIs - NO TRANSACTION WRAPPER"""
    try:
        print("[REMOVE_RESOURCE_INFO] Starting resource labels and URIs removal")

        # Remove Resource labels
        result, _ = db.cypher_query(
            """
            MATCH (n:Resource)
            REMOVE n:Resource
            RETURN count(n) AS removed
            """
        )
        removed_labels = result[0][0] if result else 0
        print(f"[REMOVE_RESOURCE_INFO] Removed {removed_labels} Resource labels")

        # Remove URI properties
        result, _ = db.cypher_query(
            """
            MATCH (n)
            WHERE n.uri IS NOT NULL
            REMOVE n.uri
            RETURN count(n) AS removed
            """
        )
        removed_uris = result[0][0] if result else 0
        print(f"[REMOVE_RESOURCE_INFO] Removed {removed_uris} URI properties")

        print("[REMOVE_RESOURCE_SUCCESS] Resource labels and URIs removal completed")

    except Exception as e:
        print(
            f"[REMOVE_RESOURCE_ERROR] Failed to remove resource labels and URIs: {str(e)}"
        )
        raise


def convert_match_labels_to_property():
    """Convert UserJobMatch category labels to matchType property - NO TRANSACTION WRAPPER"""
    try:
        print("[CONVERT_MATCH_INFO] Starting match labels to property conversion")

        # Convert Strong_Match labels to property
        strong_result, _ = db.cypher_query(
            """
            MATCH (m:UserJobMatch:Strong_Match)
            REMOVE m:Strong_Match
            SET m.matchType = 'Strong'
            RETURN count(m) AS converted
            """
        )
        strong_count = strong_result[0][0] if strong_result else 0

        # Convert Mid_Match labels to property
        mid_result, _ = db.cypher_query(
            """
            MATCH (m:UserJobMatch:Mid_Match)
            REMOVE m:Mid_Match
            SET m.matchType = 'Mid'
            RETURN count(m) AS converted
            """
        )
        mid_count = mid_result[0][0] if mid_result else 0

        # Convert Weak_Match labels to property
        weak_result, _ = db.cypher_query(
            """
            MATCH (m:UserJobMatch:Weak_Match)
            REMOVE m:Weak_Match
            SET m.matchType = 'Weak'
            RETURN count(m) AS converted
            """
        )
        weak_count = weak_result[0][0] if weak_result else 0

        total_converted = strong_count + mid_count + weak_count

        print(
            f"[CONVERT_MATCH_INFO] Converted Strong: {strong_count}, Mid: {mid_count}, Weak: {weak_count}"
        )
        print(f"[CONVERT_MATCH_SUCCESS] Total converted: {total_converted}")

        return {
            "strong": strong_count,
            "mid": mid_count,
            "weak": weak_count,
            "total": total_converted,
        }

    except Exception as e:
        print(f"[CONVERT_MATCH_ERROR] Failed to convert match labels: {str(e)}")
        raise


def add_missing_skills_to_jobs(missing_skills_map):
    """Add missing skills to jobs - NO TRANSACTION WRAPPER"""
    try:
        print("[ADD_MISSING_SKILLS_INFO] Starting to add missing skills to jobs")
        added_skills_count = 0

        for job_url, missing_skills in missing_skills_map.items():
            try:
                for skill_name in missing_skills:
                    if not skill_name or not skill_name.strip():
                        continue

                    try:
                        # Use raw cypher since AdditionalSkill relationship might not be defined in model
                        db.cypher_query(
                            """
                            MATCH (j:Job {jobUrl: $job_url})
                            MERGE (s:AdditionalSkill {name: $skill_name})
                            MERGE (j)-[:REQUIRED_SKILL]->(s)
                            """,
                            {"job_url": job_url, "skill_name": skill_name.strip()},
                        )
                        added_skills_count += 1

                        print(
                            f"[ADD_MISSING_SKILLS_DEBUG] Added skill '{skill_name}' to job {job_url}"
                        )

                    except Exception as skill_error:
                        print(
                            f"[ADD_MISSING_SKILLS_ERROR] Failed to add skill '{skill_name}': {str(skill_error)}"
                        )
                        continue

            except Exception as job_error:
                print(
                    f"[ADD_MISSING_SKILLS_ERROR] Error processing job {job_url}: {str(job_error)}"
                )
                continue

        print(
            f"[ADD_MISSING_SKILLS_SUCCESS] Added {added_skills_count} missing skills to jobs"
        )

    except Exception as e:
        print(f"[ADD_MISSING_SKILLS_ERROR] Fatal error adding missing skills: {str(e)}")
        raise


def create_indexes():
    """Create database indexes - NO TRANSACTION WRAPPER"""
    try:
        print("[CREATE_INDEXES_INFO] Starting to create database indexes")

        indexes = [
            ("Job", "jobUrl"),
            ("User", "email"),
            ("Skill", "name"),
            ("AdditionalSkill", "name"),
            ("UserJobMatch", "matchType"),
        ]

        for node_type, property_name in indexes:
            try:
                db.cypher_query(
                    f"CREATE INDEX IF NOT EXISTS FOR (n:{node_type}) ON (n.{property_name})"
                )
                print(
                    f"[CREATE_INDEXES_INFO] Created index for {node_type}.{property_name}"
                )
            except Exception as e:
                print(
                    f"[CREATE_INDEXES_ERROR] Failed to create index for {node_type}.{property_name}: {str(e)}"
                )

        print("[CREATE_INDEXES_SUCCESS] Database indexes creation completed")

    except Exception as e:
        print(f"[CREATE_INDEXES_ERROR] Fatal error creating indexes: {str(e)}")
        raise


def import_and_clean_neo4j_with_enrichment(
    graph,
    users_data=None,
    jobs_data=None,
    missing_skills_map=None,
    task_id=None,
    update_state_func=None,
):
    """Import and clean Neo4j with enrichment using proper transaction management"""
    try:
        print("[MAIN_IMPORT_INFO] Starting import and clean process")

        # Step 1: Backup existing data (no transaction needed)
        from api.services.matchers.matchers_neo4j_backup_restore_services import (
            perform_full_dynamic_backup,
        )

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

        backup_data = perform_full_dynamic_backup(backup_config)
        print("[MAIN_IMPORT_INFO] Backup completed")

        # Step 2: Create constraint for neosemantics (outside transaction)
        try:
            db.cypher_query(
                "CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS FOR (r:Resource) REQUIRE r.uri IS UNIQUE"
            )
            print("[MAIN_IMPORT_INFO] Neosemantics constraint created")
        except Exception as e:
            print(f"[MAIN_IMPORT_WARNING] Constraint might already exist: {str(e)}")

        # Step 3: Main import transaction (single transaction for all RDF operations)
        db.begin()
        try:
            if update_state_func:
                update_task_progress(
                    task_id,
                    "IMPORTING_DATA_WITH_NEOSEMANTICS",
                    {},
                    update_state_func,
                )

            # Import RDF graph (no internal transaction)
            import_to_neo4j_from_graph(graph)
            print("[MAIN_IMPORT_INFO] RDF graph imported")

            if update_state_func:
                update_task_progress(
                    task_id,
                    "FINISHING_DATA",
                    {},
                    update_state_func,
                )

            # Process imported data (no internal transactions)
            fix_resource_nodes_to_skills()
            clean_up_neo4j()
            remove_all_resource_labels_and_uris()
            convert_match_labels_to_property()
            print("[MAIN_IMPORT_INFO] Data processing completed")

            # Commit main transaction
            db.commit()
            print("[MAIN_IMPORT_SUCCESS] Main import transaction committed")

        except Exception as e:
            db.rollback()
            print(f"[MAIN_IMPORT_ERROR] Main transaction rolled back: {str(e)}")
            raise

        # Step 4: Restore backup data with enrichment (has internal transaction)
        try:
            print("[MAIN_IMPORT_INFO] Starting backup restore with enrichment")
            from api.services.matchers.matchers_neo4j_backup_restore_services import (
                perform_full_dynamic_restore_with_enrichment,
            )

            restore_success = perform_full_dynamic_restore_with_enrichment(
                backup_data, users_data, jobs_data
            )

            if restore_success:
                print("[MAIN_IMPORT_SUCCESS] Backup restore with enrichment completed")
            else:
                print("[MAIN_IMPORT_WARNING] Backup restore completed with warnings")

        except Exception as e:
            print(f"[MAIN_IMPORT_ERROR] Error during backup restore: {str(e)}")
            # Don't re-raise, continue with missing skills

        # Step 5: Add missing skills (separate transaction)
        if missing_skills_map:
            db.begin()
            try:
                print("[MAIN_IMPORT_INFO] Adding missing skills to jobs")
                add_missing_skills_to_jobs(missing_skills_map)
                db.commit()
                print("[MAIN_IMPORT_SUCCESS] Missing skills added")
            except Exception as e:
                db.rollback()
                print(f"[MAIN_IMPORT_ERROR] Failed to add missing skills: {str(e)}")
                # Don't re-raise, continue with indexes

        # Step 6: Create indexes (separate transaction)
        db.begin()
        try:
            create_indexes()
            db.commit()
            print("[MAIN_IMPORT_SUCCESS] Indexes created")
        except Exception as e:
            db.rollback()
            print(f"[MAIN_IMPORT_ERROR] Failed to create indexes: {str(e)}")
            # Don't re-raise for indexes, just log the error

        print("[MAIN_IMPORT_SUCCESS] Import and clean process completed successfully")

    except Exception as e:
        print(f"[MAIN_IMPORT_ERROR] Fatal error in import process: {str(e)}")
        raise
