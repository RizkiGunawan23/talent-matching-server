import io
import json
import math
import uuid

from owlready2 import get_ontology, sync_reasoner_pellet
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import XSD

# Define namespaces
TALENT = Namespace(
    "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/"
)


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
        "c#": "cs",
        "ci/cd": "ci_cd",
    }

    print(f"Found {len(ontology_skills)} skills in the ontology")

    # Handle end_idx
    if end_idx is None or end_idx > len(jobs_data["result"]):
        end_idx = len(jobs_data["result"])

    # Use the slice of jobs specified by start_idx and end_idx
    jobs_slice = jobs_data["result"][start_idx:end_idx]
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
    for skill in user_data["skills"]:
        # Convert to lowercase for matching
        skill_lower = skill.lower()

        # Check if lowercase skill exists in our map
        if skill_lower in ontology_skills:
            original_name, original_uri = ontology_skills[skill_lower]
            graph.add((user_uri, TALENT["HAS_SKILL"], original_uri))
            print(f"Added skill: {original_name}")

    return graph


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


def calculate_user_job_similarity(graph):
    """
    Calculate the similarity between users and jobs in the ontology
    """
    # Get all users
    users_query = """
    SELECT ?user
    WHERE {
        ?user rdf:type <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/User> .
    }
    """

    # Get all jobs
    jobs_query = """
    SELECT ?job
    WHERE {
        ?job rdf:type <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Job> .
    }
    """

    users = [row[0] for row in graph.query(users_query)]
    jobs = [row[0] for row in graph.query(jobs_query)]

    match_results = []

    # For each user
    for user in users:
        # Get user skills
        user_skills_query = (
            """
        SELECT ?skill
        WHERE {
            <%s> <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/HAS_SKILL> ?skill .
        }
        """
            % user
        )

        user_skills = [row[0] for row in graph.query(user_skills_query)]

        if not user_skills:
            continue

        # For each job
        for job in jobs:
            # Get job skills
            job_skills_query = (
                """
            SELECT ?skill
            WHERE {
                <%s> <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/REQUIRED_SKILL> ?skill .
            }
            """
                % job
            )

            job_skills = [row[0] for row in graph.query(job_skills_query)]

            if not job_skills:
                continue

            # Calculate the max similarity for each user skill
            skill_similarities = []

            for user_skill in user_skills:
                # Get limited taxonomic features (self + up to 3 ancestors) for user_skill
                user_skill_features = get_limited_ancestors(graph, user_skill)

                max_skill_similarity = 0
                best_match = None

                for job_skill in job_skills:
                    # Get limited taxonomic features for job_skill
                    job_skill_features = get_limited_ancestors(graph, job_skill)

                    # Calculate Sánchez similarity between these two skills
                    skill_similarity = sanchez_similarity(
                        user_skill_features, job_skill_features
                    )

                    # Update max similarity if this is higher
                    if skill_similarity > max_skill_similarity:
                        max_skill_similarity = skill_similarity
                        best_match = job_skill

                # Print debugging info
                user_skill_name = str(user_skill).split("/")[-1]
                if best_match:
                    best_match_name = str(best_match).split("/")[-1]
                    print(
                        f"User skill: {user_skill_name} - Best match: {best_match_name} - Similarity: {max_skill_similarity:.4f}"
                    )
                else:
                    print(f"User skill: {user_skill_name} - No good match found")

                skill_similarities.append(max_skill_similarity)

            # Calculate overall similarity as average of individual skill similarities
            if skill_similarities:
                overall_similarity = sum(skill_similarities) / len(skill_similarities)

                # Only add if similarity is greater than 0
                if overall_similarity > 0:
                    match_results.append(
                        {"user": user, "job": job, "similarity": overall_similarity}
                    )

    return match_results


def add_user_job_matches_to_ontology(graph, match_results):
    """
    Add UserJobMatch individuals to the ontology based on match results
    """
    # Use existing URIs without redefining the class and properties
    userJobMatch_uri = TALENT["UserJobMatch"]
    userMatch_uri = TALENT["USER_MATCH"]
    jobMatch_uri = TALENT["JOB_MATCH"]
    similarityScore_uri = TALENT["similarityScore"]

    for match in match_results:
        # Create a unique identifier for the match
        match_id = str(uuid.uuid4())
        match_uri = TALENT[f"UserJobMatch_{match_id}"]

        # Add the UserJobMatch individual
        graph.add((match_uri, RDF.type, userJobMatch_uri))

        # Add USER_MATCH property
        graph.add((match_uri, userMatch_uri, URIRef(match["user"])))

        # Add JOB_MATCH property
        graph.add((match_uri, jobMatch_uri, URIRef(match["job"])))

        # Add similarityScore property
        graph.add(
            (
                match_uri,
                similarityScore_uri,
                Literal(match["similarity"], datatype=XSD.float),
            )
        )


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


def process_job_partition(
    base_graph, jobs_data, user_data, start_idx, end_idx, partition_num
):
    """Process a partition of 250 jobs with reasoning without creating files"""
    print(
        f"\n===== Processing Partition {partition_num}: Jobs {start_idx} to {end_idx-1} ====="
    )

    # Create a copy of the base graph for this partition
    # This includes the ontology structure but not the job/user data
    partition_graph = Graph()
    for s, p, o in base_graph:
        partition_graph.add((s, p, o))
    partition_graph.bind("talent", TALENT)

    # Create a partition of the jobs data
    partition_data = {"result": jobs_data["result"][start_idx:end_idx]}

    # Import jobs for this partition - FIX: Use jobs_slice instead of hardcoded range
    partition_graph = import_jobs_to_ontology(partition_graph, partition_data)

    # Add user data to this partition
    partition_graph = import_user_to_ontology(partition_graph, user_data)

    # Calculate similarity between user and jobs
    match_results = calculate_user_job_similarity(partition_graph)
    print(
        f"Partition {partition_num}: Found {len(match_results)} matches with similarity > 0"
    )

    # Add matches to ontology
    add_user_job_matches_to_ontology(partition_graph, match_results)

    # Convert and apply reasoning
    print(f"Applying reasoning to partition {partition_num}...")
    ontology = convert_ttl_to_owl(partition_graph)
    reasoned_ontology = apply_reasoning_to_graph(ontology)

    # Convert back to RDFlib format
    result_graph = convert_owl_to_ttl(reasoned_ontology)

    return result_graph, match_results


def merge_graphs(graphs):
    """Merge multiple graphs into one final graph without creating files"""
    print("\n===== Merging Partition Results =====")

    # Create a new graph for the merged result
    merged_graph = Graph()
    merged_graph.bind("talent", TALENT)

    # Add all triples from each graph to the merged graph
    for i, graph in enumerate(graphs):
        print(f"Adding triples from partition {i+1}...")
        for s, p, o in graph:
            merged_graph.add((s, p, o))

    return merged_graph


# Neo4j Integration
def import_to_neo4j_from_graph(uri, user, password, graph):
    """Import RDF data to Neo4j directly from an in-memory graph"""
    import os
    import tempfile
    import time

    from neo4j import GraphDatabase

    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        print("Clearing database...")
        run_query(driver, "MATCH (n) DETACH DELETE n")

        print("Creating constraints...")
        run_query(
            driver,
            "CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS FOR (r:Resource) REQUIRE r.uri IS UNIQUE",
        )

        print("Initializing n10s...")
        config = {
            "handleVocabUris": "IGNORE",
            "handleRDFTypes": "LABELS",
            "keepLangTag": False,
            "applyNeo4jNaming": False,
            "keepCustomDataTypes": True,
        }
        run_query(driver, "CALL n10s.graphconfig.init($config)", {"config": config})

        # Create a temporary file with auto-deletion disabled
        print("Preparing graph data for Neo4j...")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ttl")
        temp_path = temp_file.name
        temp_file.close()  # Close the file before writing to it

        # Serialize the graph to the file
        graph.serialize(destination=temp_path, format="turtle")

        print("Importing RDF data to Neo4j...")
        # Convert to file URI format with proper encoding
        file_uri = f"file:///{temp_path.replace('\\', '/').replace(' ', '%20')}"
        import_result = run_query(
            driver,
            "CALL n10s.rdf.import.fetch($file_uri, 'Turtle')",
            {"file_uri": file_uri},
        )
        print(f"Import completed: {import_result}")

        # Wait a moment for Neo4j to release the file
        time.sleep(3)

        # Attempt file deletion with retry
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                break
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"Deletion attempt {attempt+1} failed, retrying...")
                    time.sleep(2)  # Wait longer between retries
                else:
                    print(f"Warning: Could not delete temporary file {temp_path}: {e}")
                    print("The file will be cleaned up by the system later.")

        print("Creating indexes...")
        run_query(driver, "CREATE INDEX IF NOT EXISTS FOR (j:Job) ON (j.job_url)")
        run_query(driver, "CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.user_email)")

        # Show statistics
        label_counts = run_query(
            driver,
            "MATCH (n) RETURN DISTINCT labels(n) AS Labels, count(*) AS Count ORDER BY Count DESC",
        )
        print("\nNode counts by label:")
        for record in label_counts:
            print(f"  {record['Labels']}: {record['Count']}")

        rel_counts = run_query(
            driver,
            "MATCH (n)-[r]->(m) RETURN DISTINCT type(r) AS RelationshipType, count(*) AS Count ORDER BY Count DESC",
        )
        print("\nRelationship counts by type:")
        for record in rel_counts:
            print(f"  {record['RelationshipType']}: {record['Count']}")

    finally:
        driver.close()


def import_and_clean_neo4j_from_graph(graph):
    """Import the graph to Neo4j and clean up unnecessary labels/relationships"""
    print("\n===== IMPORTING TO NEO4J =====")

    # Neo4j connection settings
    uri = "bolt://localhost:7689"
    user = "neo4j"
    password = "12345678"  # Replace with your actual password

    try:
        # Import the graph directly to Neo4j
        import_to_neo4j_from_graph(uri, user, password, graph)

        # Clean up unnecessary labels and relationships
        clean_up_neo4j(uri, user, password)

        print("Neo4j import and cleanup completed successfully")
    except Exception as e:
        print(f"Error during Neo4j processing: {str(e)}")


def clean_up_neo4j(uri, user, password):
    """Clean up unnecessary labels and relationships in Neo4j"""
    from neo4j import GraphDatabase

    print("\n===== CLEANING UP NEO4J DATABASE =====")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    # Labels to remove
    labels_to_remove = [
        "Datatype",
        "ObjectProperty",
        "DatatypeProperty",
        "Restriction",
        "NamedIndividual",
        "Ontology",
    ]

    # Relationship types to delete
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
    ]

    try:
        # Show initial counts
        print("=== BEFORE CLEANUP ===")

        label_counts = run_query(
            driver,
            "MATCH (n) RETURN DISTINCT labels(n) AS Labels, count(*) AS Count ORDER BY Count DESC",
        )
        for record in label_counts:
            print(f"  {record['Labels']}: {record['Count']}")

        rel_counts = run_query(
            driver,
            "MATCH ()-[r]->() RETURN DISTINCT type(r) AS Type, count(*) AS Count ORDER BY Count DESC",
        )
        for record in rel_counts:
            print(f"  {record['Type']}: {record['Count']}")

        # Remove unwanted labels
        print("\n=== REMOVING LABELS ===")
        total_labels_removed = 0
        for label in labels_to_remove:
            print(f"Removing label: {label}")
            result = run_query(
                driver, f"MATCH (n:{label}) REMOVE n:{label} RETURN count(*) AS removed"
            )
            removed = result[0]["removed"] if result else 0
            total_labels_removed += removed
            print(f"  Removed {removed} nodes with label '{label}'")

        # Delete unwanted relationship types
        print("\n=== DELETING RELATIONSHIP TYPES ===")
        total_rels_deleted = 0
        for rel_type in relationship_types_to_delete:
            print(f"Deleting relationship type: {rel_type}")
            result = run_query(
                driver,
                f"MATCH ()-[r:{rel_type}]->() DELETE r RETURN count(*) AS deleted",
            )
            deleted = result[0]["deleted"] if result else 0
            total_rels_deleted += deleted
            print(f"  Deleted {deleted} relationships of type '{rel_type}'")

        print(f"\nTotal labels removed: {total_labels_removed}")
        print(f"Total relationships deleted: {total_rels_deleted}")

        # Show final counts
        print("\n=== AFTER CLEANUP ===")

        label_counts = run_query(
            driver,
            "MATCH (n) RETURN DISTINCT labels(n) AS Labels, count(*) AS Count ORDER BY Count DESC",
        )
        for record in label_counts:
            print(f"  {record['Labels']}: {record['Count']}")

        rel_counts = run_query(
            driver,
            "MATCH ()-[r]->() RETURN DISTINCT type(r) AS Type, count(*) AS Count ORDER BY Count DESC",
        )
        for record in rel_counts:
            print(f"  {record['Type']}: {record['Count']}")

    finally:
        driver.close()


def run_query(driver, query, parameters=None):
    """Run a Cypher query against Neo4j"""
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return list(result)


def main():
    # Define paths
    ONTOLOGY_PATH = "ontology_ver3.ttl"
    JSON_PATH = "cleaned_glints_jobs.json"
    USER_JSON_PATH = "user.json"

    # Set partition size
    PARTITION_SIZE = 250

    # Load the base ontology (structure only)
    base_graph = Graph()
    base_graph.parse(ONTOLOGY_PATH, format="turtle")
    base_graph.bind("talent", TALENT)

    # Load job data
    with open(JSON_PATH, "r", encoding="utf-8") as file:
        jobs_data = json.load(file)

    # Load user data
    with open(USER_JSON_PATH, "r", encoding="utf-8") as file:
        user_data = json.load(file)

    # Calculate number of partitions
    total_jobs = len(jobs_data["result"])
    num_partitions = (total_jobs + PARTITION_SIZE - 1) // PARTITION_SIZE

    # Process each partition
    processed_graphs = []
    all_matches = []

    for i in range(num_partitions):
        start_idx = i * PARTITION_SIZE
        end_idx = min(start_idx + PARTITION_SIZE, total_jobs)

        # Process this partition
        result_graph, matches = process_job_partition(
            base_graph, jobs_data, user_data, start_idx, end_idx, i + 1
        )

        # Store results in memory
        processed_graphs.append(result_graph)
        all_matches.extend(matches)

    # Merge all processed graphs in memory
    merged_graph = merge_graphs(processed_graphs)

    # Import directly from the merged graph
    import_and_clean_neo4j_from_graph(merged_graph)
