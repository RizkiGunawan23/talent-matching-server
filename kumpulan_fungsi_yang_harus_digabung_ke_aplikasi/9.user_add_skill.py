import json
import math
import uuid

from neo4j import GraphDatabase
from owlready2 import sync_reasoner_pellet
from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

TALENT = Namespace(
    "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/"
)


def sanchez_similarity(set_a, set_b):
    """
    Calculate the Sánchez similarity between two sets.
    Based on the formula: sim_sanchez(a,b) = 1 - log2(1 + (|Φ(a)∖Φ(b)| + |Φ(b)∖Φ(a)|)/(|Φ(a)∖Φ(b)| + |Φ(b)∖Φ(a)| + |Φ(a)∩Φ(b)|))
    """
    # If the sets are exactly the same, similarity is 1
    if set_a == set_b:
        return 1.0

    # Calculate the set differences and intersection
    a_minus_b = len(set_a - set_b)
    b_minus_a = len(set_b - set_a)
    intersection = len(set_a.intersection(set_b))

    # If there's no intersection, similarity is 0
    if intersection == 0:
        return 0.0

    # Calculate the Sánchez similarity
    numerator = a_minus_b + b_minus_a
    denominator = a_minus_b + b_minus_a + intersection

    similarity = 1 - math.log2(1 + numerator / denominator)
    return similarity


def get_limited_ancestors(graph, skill_uri, max_levels=3):
    """
    Get the skill itself and up to 3 levels of ancestor classes
    """
    ancestors = set()
    ancestors.add(str(skill_uri))  # Add the skill itself

    current_level = [skill_uri]
    level = 0

    while current_level and level < max_levels:
        next_level = []
        for node in current_level:
            # Get immediate parents
            query = f"""
            SELECT ?parent
            WHERE {{
                <{node}> rdfs:subClassOf ?parent .
                FILTER(?parent != <{node}>)
            }}
            """

            for row in graph.query(query):
                parent = row[0]
                parent_str = str(parent)
                if parent_str not in ancestors:
                    ancestors.add(parent_str)
                    next_level.append(parent)

        current_level = next_level
        level += 1

    return ancestors


def convert_ttl_to_owl(graph):
    """Convert RDFlib Graph to an OWLReady2 ontology using a temporary file"""
    try:
        print("Converting RDFlib Graph to OWLReady2 ontology...")
        import os
        import tempfile

        # Create a temporary file in system's temp directory (not visible in your project folder)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".owl") as temp:
            temp_path = temp.name
            # Serialize the graph to the temporary file
            graph.serialize(destination=temp_path, format="xml")

        try:
            # Load the ontology using the temporary file
            from owlready2 import get_ontology

            ontology = get_ontology("file://" + temp_path).load()
            return ontology
        finally:
            # Clean up - delete the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return None


def apply_reasoning_to_graph(ontology):
    """Apply reasoning to an OWLReady2 ontology with progress indicators"""
    try:
        print("Applying reasoning with Pellet...")
        print("Step 1: Preparing ontology for reasoning...")

        # Count entities before reasoning
        num_classes_before = len(list(ontology.classes()))
        num_properties_before = len(list(ontology.properties()))
        num_individuals_before = len(list(ontology.individuals()))

        print(f"Ontology statistics before reasoning:")
        print(f"  - Classes: {num_classes_before}")
        print(f"  - Properties: {num_properties_before}")
        print(f"  - Individuals: {num_individuals_before}")

        print("Step 2: Starting reasoning process (this may take some time)...")
        import time

        start_time = time.time()

        # Perform reasoning
        with ontology:
            print("  - Initializing reasoner...")
            print("  - Classifying taxonomy...")
            print("  - Computing inferences...")
            sync_reasoner_pellet()  # Using Pellet reasoner

        end_time = time.time()
        reasoning_time = end_time - start_time

        # Count entities after reasoning
        num_classes_after = len(list(ontology.classes()))
        num_properties_after = len(list(ontology.properties()))
        num_individuals_after = len(list(ontology.individuals()))

        print(f"Step 3: Reasoning completed in {reasoning_time:.2f} seconds")
        print(f"Ontology statistics after reasoning:")
        print(f"  - Classes: {num_classes_after}")
        print(f"  - Properties: {num_properties_after}")
        print(f"  - Individuals: {num_individuals_after}")

        if num_classes_after > num_classes_before:
            print(f"  - Inferred {num_classes_after - num_classes_before} new classes")
        if num_properties_after > num_properties_before:
            print(
                f"  - Inferred {num_properties_after - num_properties_before} new properties"
            )
        if num_individuals_after > num_individuals_before:
            print(
                f"  - Inferred {num_individuals_after - num_individuals_before} new individuals"
            )

        return ontology
    except Exception as e:
        print(f"Error during reasoning: {str(e)}")
        return None


def convert_owl_to_ttl(ontology):
    """Convert OWLReady2 ontology back to RDFlib Graph using in-memory buffer"""
    try:
        print("Converting OWLReady2 ontology to RDFlib Graph...")
        # Use BytesIO to avoid creating a file
        from io import BytesIO

        # Create an in-memory buffer
        buffer = BytesIO()

        # Save the ontology to the buffer
        ontology.save(file=buffer, format="rdfxml")

        # Reset buffer position to start
        buffer.seek(0)

        # Load it into an RDFlib Graph
        new_graph = Graph()
        new_graph.parse(buffer, format="xml")

        # Bind the TALENT namespace
        new_graph.bind("talent", TALENT)

        return new_graph
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return None


def update_user_skills_and_recalculate_matches(user_email, new_skills):
    """
    Update a user's skills and recalculate job matches only for that user,
    without affecting other users or creating intermediate files.
    """
    # 1. Load base ontology
    print(f"Loading base ontology...")
    base_graph = Graph()
    base_graph.parse("ontology_ver3.ttl", format="turtle")
    base_graph.bind("talent", TALENT)

    # 2. Get job data from Neo4j
    print(f"Retrieving jobs from Neo4j...")
    jobs_data = get_jobs_from_neo4j()

    # 3. Get existing user skills from Neo4j
    print(f"Retrieving user data from Neo4j...")
    existing_user_data = get_user_data_from_neo4j(user_email)
    user_email = existing_user_data["email"]
    existing_skills = existing_user_data["has_skills"]

    # 4. Combine existing and new skills
    all_skills = list(set(existing_skills + new_skills))
    user_data = {"email": user_email, "has_skills": all_skills}

    # 5. Build in-memory graph with jobs and user
    graph = import_jobs_to_ontology(base_graph, jobs_data)
    graph = import_user_to_ontology(graph, user_data)

    # # 6. Calculate similarities
    print("Calculating similarities...")
    matches = calculate_user_job_similarity_for_specific_user(graph, user_email)

    # 6.5 Add match nodes to the ontology
    graph = add_user_job_matches_to_ontology(graph, matches)

    # 7. Apply reasoning (in memory)
    print("Applying reasoning...")
    ontology = convert_ttl_to_owl(graph)
    reasoned_ontology = apply_reasoning_to_graph(ontology)
    result_graph = convert_owl_to_ttl(reasoned_ontology)

    # 8. Extract match information from reasoned graph
    print("Extracting match classifications...")
    classified_matches = extract_match_classifications(result_graph, user_email)

    # 9. Update Neo4j directly
    print("Updating Neo4j directly...")
    update_neo4j_for_user_direct(user_email, all_skills, classified_matches)

    return {
        "user_email": user_email,
        "skills_added": new_skills,
        "total_skills": all_skills,
        "matches_found": len(classified_matches),
    }


def import_jobs_to_ontology(graph, jobs_data, start_idx=0, end_idx=None):
    # Get all skills in the ontology
    all_skills_query = """
    SELECT ?skill
    WHERE {
        ?skill rdfs:subClassOf+ <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Skills> .
    }
    """
    # Dictionary mapping lowercase skill names to their original URIs and names
    ontology_skills = {}
    for row in graph.query(all_skills_query):
        skill_uri = row[0]
        # Extract skill name from URI
        skill_name = str(skill_uri).split("/")[-1].replace("_", " ")
        # Store lowercase version as key for case-insensitive matching
        ontology_skills[skill_name.lower()] = (skill_name, skill_uri)

    # Tambahkan pemetaan khusus untuk kasus-kasus tertentu
    special_cases = {
        "c#": "cs",  # C# dipetakan ke CS
    }

    print(f"Found {len(ontology_skills)} skills in the ontology")

    # Handle end_idx
    if end_idx is None or end_idx > len(jobs_data):
        end_idx = len(jobs_data)

    # Use the slice of jobs specified by start_idx and end_idx
    jobs_slice = jobs_data[start_idx:end_idx]
    print(f"Processing jobs {start_idx} to {end_idx-1} (total: {len(jobs_slice)})")

    for job in jobs_slice:
        if "job_url" not in job:
            continue

        # Create a unique identifier for the job (using URL as base)
        job_id = job["job_url"].split("/")[-1]
        if "?" in job_id:
            job_id = job_id.split("?")[0]

        # Create job individual
        job_uri = TALENT[f"Job_{job_id}"]
        graph.add((job_uri, RDF.type, TALENT["Job"]))
        graph.add(
            (job_uri, TALENT["job_url"], Literal(job["job_url"], datatype=XSD.string))
        )

        # Add required skills
        if "required_skills" in job and job["required_skills"]:
            for skill in job["required_skills"]:
                # Convert to lowercase for matching
                skill_lower = skill.lower()

                # Check for special cases first
                if skill_lower in special_cases:
                    mapped_skill = special_cases[skill_lower]
                    if mapped_skill in ontology_skills:
                        original_name, original_uri = ontology_skills[mapped_skill]
                        graph.add((job_uri, TALENT["REQUIRED_SKILL"], original_uri))
                        print(f"Special case matched: {skill} -> {original_name}")
                        continue

                # Regular matching
                if skill_lower in ontology_skills:
                    original_name, original_uri = ontology_skills[skill_lower]
                    graph.add((job_uri, TALENT["REQUIRED_SKILL"], original_uri))

    return graph


def import_user_to_ontology(graph, user_data):
    # Get all skills in the ontology
    all_skills_query = """
    SELECT ?skill
    WHERE {
        ?skill rdfs:subClassOf+ <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Skills> .
    }
    """
    # Dictionary mapping lowercase skill names to their original URIs
    ontology_skills = {}
    for row in graph.query(all_skills_query):
        skill_uri = row[0]
        # Extract skill name from URI
        skill_name = str(skill_uri).split("/")[-1].replace("_", " ")
        # Store lowercase version as key for case-insensitive matching
        ontology_skills[skill_name.lower()] = (skill_name, skill_uri)

    print(f"Found {len(ontology_skills)} skills in the ontology")

    # Special cases mapping
    special_cases = {
        "c#": "cs",  # C# mapped to CS
    }

    # Create a unique identifier for the user (using email as base)
    user_id = user_data["email"].split("@")[0]  # Use part before @ for the ID

    # Create user individual
    user_uri = TALENT[f"User_{user_id}"]
    graph.add((user_uri, RDF.type, TALENT["User"]))
    graph.add(
        (
            user_uri,
            TALENT["user_email"],
            Literal(user_data["email"], datatype=XSD.string),
        )
    )

    # Add the user's skills
    for skill in user_data["has_skills"]:
        # Convert to lowercase for matching
        skill_lower = skill.lower()

        # Check for special cases first
        if skill_lower in special_cases:
            mapped_skill = special_cases[skill_lower]
            if mapped_skill in ontology_skills:
                original_name, original_uri = ontology_skills[mapped_skill]
                graph.add((user_uri, TALENT["HAS_SKILL"], original_uri))
                print(f"Special case matched: {skill} -> {original_name}")
                continue

        # Regular matching
        if skill_lower in ontology_skills:
            original_name, original_uri = ontology_skills[skill_lower]
            graph.add((user_uri, TALENT["HAS_SKILL"], original_uri))
            print(f"Added skill: {original_name}")

    return graph


def add_user_job_matches_to_ontology(graph, match_results):
    """Add match nodes to the ontology with similarity scores"""
    print(f"Adding {len(match_results)} match nodes to ontology...")

    userJobMatch_uri = TALENT["UserJobMatch"]
    userMatch_uri = TALENT["USER_MATCH"]
    jobMatch_uri = TALENT["JOB_MATCH"]
    similarityScore_uri = TALENT["similarityScore"]

    for match in match_results:
        match_id = str(uuid.uuid4())
        match_uri = TALENT[f"UserJobMatch_{match_id}"]

        # Extract URIs from string representations
        user_uri = URIRef(match["user"])
        job_uri = URIRef(match["job"])
        similarity = match["similarity"]

        # Add match node and its relationships
        graph.add((match_uri, RDF.type, userJobMatch_uri))
        graph.add((match_uri, userMatch_uri, user_uri))
        graph.add((match_uri, jobMatch_uri, job_uri))
        graph.add(
            (match_uri, similarityScore_uri, Literal(similarity, datatype=XSD.float))
        )

    return graph


def extract_match_classifications(result_graph, user_email):
    """Extract match classification information from the reasoned graph"""
    user_id = user_email.split("@")[0]
    user_uri = str(TALENT[f"User_{user_id}"])

    # Get all match nodes for this user with their types and scores
    query = f"""
    SELECT ?match ?job ?score ?type
    WHERE {{
        ?match a <{TALENT["UserJobMatch"]}> .
        ?match <{TALENT["USER_MATCH"]}> <{user_uri}> .
        ?match <{TALENT["JOB_MATCH"]}> ?job .
        ?match <{TALENT["similarityScore"]}> ?score .
        
        # Get the most specific match type (Strong, Mid, or Weak)
        {{
            ?match a <{TALENT["Strong_Match"]}> .
            BIND("Strong_Match" AS ?type)
        }} UNION {{
            ?match a <{TALENT["Mid_Match"]}> .
            BIND("Mid_Match" AS ?type)
        }} UNION {{
            ?match a <{TALENT["Weak_Match"]}> .
            BIND("Weak_Match" AS ?type)
        }}
    }}
    """

    classified_matches = []
    for row in result_graph.query(query):
        match_uri = str(row[0])
        job_uri = str(row[1])
        score = float(row[2])
        match_type = str(row[3])

        # Get job URL from URI
        job_url = job_uri.split("/")[-1]
        if job_url.startswith("Job_"):
            job_url = job_url[4:]  # Remove "Job_" prefix

        classified_matches.append(
            {
                "match_uri": match_uri,
                "job_uri": job_uri,
                "job_url": job_url,
                "similarity": score,
                "match_type": match_type,
            }
        )

    return classified_matches


def update_neo4j_for_user_direct(user_email, skills, classified_matches):
    """Update user skills and matches using direct Cypher without temp files"""
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "12345678"

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session() as session:
            print("Updating Neo4j database...")

            # 1. Clear existing matches for this user
            print("Removing existing matches...")
            match_removal = session.run(
                """
                MATCH (m:UserJobMatch)-[:USER_MATCH]->(u:User {user_email: $email})
                DETACH DELETE m
                RETURN count(m) as removed
                """,
                {"email": user_email},
            )
            removed = match_removal.single()["removed"] if match_removal.peek() else 0
            print(f"Removed {removed} existing match nodes")

            # 2. Clear existing user skills
            print("Removing existing skills...")
            skill_removal = session.run(
                """
                MATCH (u:User {user_email: $email})-[r:HAS_SKILL]->()
                DELETE r
                RETURN count(r) as removed
                """,
                {"email": user_email},
            )
            removed_skills = (
                skill_removal.single()["removed"] if skill_removal.peek() else 0
            )
            print(f"Removed {removed_skills} existing skill relationships")

            # 3. Add user skills in a single transaction
            print(f"Adding {len(skills)} skills...")
            skill_query = """
            MATCH (u:User {user_email: $email})
            UNWIND $skills as skill_name
            MATCH (s:Skill)
            WHERE toLower(s.name) = toLower(skill_name)
            MERGE (u)-[:HAS_SKILL]->(s)
            RETURN count(*) as added
            """
            skill_result = session.run(
                skill_query, {"email": user_email, "skills": skills}
            )
            added_skills = skill_result.single()["added"] if skill_result.peek() else 0
            print(f"Added {added_skills} skill relationships")

            # 4. Add matches in a single transaction
            if classified_matches:
                print(f"Adding {len(classified_matches)} matches...")

                # Group matches by type
                strong_matches = [
                    m for m in classified_matches if m["match_type"] == "Strong_Match"
                ]
                mid_matches = [
                    m for m in classified_matches if m["match_type"] == "Mid_Match"
                ]
                weak_matches = [
                    m for m in classified_matches if m["match_type"] == "Weak_Match"
                ]

                # Create Strong matches
                if strong_matches:
                    match_batch = [
                        {"job_url": m["job_url"], "score": m["similarity"]}
                        for m in strong_matches
                    ]
                    session.run(
                        """
                        MATCH (u:User {user_email: $email})
                        UNWIND $matches as match_data
                        MATCH (j:Job) 
                        WHERE j.job_url CONTAINS match_data.job_url OR j.job_url ENDS WITH match_data.job_url
                        CREATE (m:UserJobMatch:Strong_Match:Resource)
                        SET m += {uri: 'http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/UserJobMatch_' + randomUUID()}
                        SET m += {similarityScore: match_data.score}
                        CREATE (m)-[:USER_MATCH]->(u)
                        CREATE (m)-[:JOB_MATCH]->(j)
                        """,
                        {"email": user_email, "matches": match_batch},
                    )

                # Create Mid matches
                if mid_matches:
                    match_batch = [
                        {"job_url": m["job_url"], "score": m["similarity"]}
                        for m in mid_matches
                    ]
                    session.run(
                        """
                        MATCH (u:User {user_email: $email})
                        UNWIND $matches as match_data
                        MATCH (j:Job) 
                        WHERE j.job_url CONTAINS match_data.job_url OR j.job_url ENDS WITH match_data.job_url
                        CREATE (m:UserJobMatch:Mid_Match:Resource)
                        SET m += {uri: 'http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/UserJobMatch_' + randomUUID()}
                        SET m += {similarityScore: match_data.score}
                        CREATE (m)-[:USER_MATCH]->(u)
                        CREATE (m)-[:JOB_MATCH]->(j)
                        """,
                        {"email": user_email, "matches": match_batch},
                    )

                # Create Weak matches
                if weak_matches:
                    match_batch = [
                        {"job_url": m["job_url"], "score": m["similarity"]}
                        for m in weak_matches
                    ]
                    session.run(
                        """
                        MATCH (u:User {user_email: $email})
                        UNWIND $matches as match_data
                        MATCH (j:Job) 
                        WHERE j.job_url CONTAINS match_data.job_url OR j.job_url ENDS WITH match_data.job_url
                        CREATE (m:UserJobMatch:Weak_Match:Resource)
                        SET m += {uri: 'http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/UserJobMatch_' + randomUUID()}
                        SET m += {similarityScore: match_data.score}
                        CREATE (m)-[:USER_MATCH]->(u)
                        CREATE (m)-[:JOB_MATCH]->(j)
                        """,
                        {"email": user_email, "matches": match_batch},
                    )

                print(
                    f"Created match nodes: {len(strong_matches)} Strong, {len(mid_matches)} Mid, {len(weak_matches)} Weak"
                )

    except Exception as e:
        print(f"Error updating Neo4j: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        driver.close()


def calculate_user_job_similarity_for_specific_user(graph, user_email):
    """Calculate job similarities only for a specific user"""
    # Convert email to user URI format
    user_id = user_email.split("@")[0]
    user_uri = TALENT[f"User_{user_id}"]

    # Find this specific user in the graph
    user_exists_query = f"""
    ASK {{ <{user_uri}> a <{TALENT["User"]}> }}
    """
    if not graph.query(user_exists_query).askAnswer:
        print(f"User {user_email} not found in graph")
        return []

    # Get all jobs
    jobs_query = """
    SELECT ?job
    WHERE {
        ?job rdf:type <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Job> .
    }
    """
    jobs = [row[0] for row in graph.query(jobs_query)]

    # Get user skills
    user_skills_query = f"""
    SELECT ?skill
    WHERE {{
        <{user_uri}> <{TALENT["HAS_SKILL"]}> ?skill .
    }}
    """
    user_skills = [row[0] for row in graph.query(user_skills_query)]

    if not user_skills:
        print(f"User {user_email} has no skills in the graph")
        return []

    match_results = []

    # For each job, calculate similarity with this user
    for job in jobs:
        # Get job skills
        job_skills_query = f"""
        SELECT ?skill
        WHERE {{
            <{job}> <{TALENT["REQUIRED_SKILL"]}> ?skill .
        }}
        """
        job_skills = [row[0] for row in graph.query(job_skills_query)]

        if not job_skills:
            continue

        # Calculate max similarity for each user skill
        skill_similarities = []

        for user_skill in user_skills:
            # Get limited ancestors for user skill
            user_skill_features = get_limited_ancestors(graph, user_skill)

            max_skill_similarity = 0
            best_match = None

            for job_skill in job_skills:
                # Get limited ancestors for job skill
                job_skill_features = get_limited_ancestors(graph, job_skill)

                # Calculate similarity
                skill_similarity = sanchez_similarity(
                    user_skill_features, job_skill_features
                )

                # Update max similarity if this is higher
                if skill_similarity > max_skill_similarity:
                    max_skill_similarity = skill_similarity
                    best_match = job_skill

            skill_similarities.append(max_skill_similarity)

        # Calculate overall similarity
        if skill_similarities:
            overall_similarity = sum(skill_similarities) / len(skill_similarities)

            if overall_similarity > 0:
                match_results.append(
                    {
                        "user": str(user_uri),
                        "job": str(job),
                        "similarity": overall_similarity,
                    }
                )

    return match_results


def get_jobs_from_neo4j():
    """Retrieve all jobs with their required skills from Neo4j"""
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "12345678"  # Update with your password

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session() as session:
            # Query to get all jobs with their required skills
            result = session.run(
                """
            MATCH (j:Job)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            WITH j, collect(DISTINCT s.name) as required_skills
            RETURN j.job_url as job_id, j.job_url as job_url, required_skills
            """
            )

            # Format the data to match the expected JSON structure
            jobs_data = []
            for record in result:
                job = {
                    "job_id": record["job_id"],
                    "job_url": record["job_url"],
                    "required_skills": record["required_skills"],
                }
                jobs_data.append(job)

            print(f"Retrieved {len(jobs_data)} jobs from Neo4j")
            return jobs_data

    except Exception as e:
        print(f"Error retrieving jobs from Neo4j: {e}")
        # Fallback to file if database access fails
        print("Falling back to JSON file for jobs")
        with open("cleaned_glints_jobs.json", "r", encoding="utf-8") as file:
            return json.load(file)
    finally:
        driver.close()


def get_user_data_from_neo4j(user_email):
    """Retrieve a specific user with their skills from Neo4j"""
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "12345678"  # Update with your password

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session() as session:
            # Query to get user data and skills
            result = session.run(
                """
            MATCH (u:User {user_email: $email})
            OPTIONAL MATCH (u)-[:HAS_SKILL]->(s:Skill)
            RETURN u.user_email as email, collect(DISTINCT s.name) as has_skills
            """,
                {"email": user_email},
            )

            record = result.single()
            if not record:
                print(f"User {user_email} not found in database")
                return {"email": user_email, "has_skills": []}

            return {"email": record["email"], "has_skills": record["has_skills"]}

    except Exception as e:
        print(f"Error retrieving user data from Neo4j: {e}")
        return {"email": user_email, "has_skills": []}
    finally:
        driver.close()


def main():
    # Example usage
    user_email = "rizki@gmail.com"
    new_skills = ["JavaScript", "Java", "React.js", "Python"]
    result = update_user_skills_and_recalculate_matches(user_email, new_skills)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
