import math
import os
import uuid

from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import XSD

from api.constants import TALENT_NAMESPACE


def load_base_ontology():
    """Load the base ontology structure"""
    ontology_path = os.path.join(os.path.dirname(__file__), "ontology.ttl")
    base_graph = Graph()
    base_graph.parse(ontology_path, format="turtle")
    base_graph.bind("talent", TALENT_NAMESPACE)

    return base_graph


def import_all_jobs_to_ontology(graph, jobs_data):
    """
    Import all jobs into the ontology graph and map missing skills.
    """
    all_skills_query = """
    SELECT ?skill
    WHERE {
        ?skill rdfs:subClassOf+ <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Skills> .
    }
    """

    # Load all skills from ontology
    ontology_skills = {}
    for row in graph.query(all_skills_query):
        skill_uri = row[0]
        skill_name = str(skill_uri).split("/")[-1].replace("_", " ")
        ontology_skills[skill_name.lower()] = (skill_name, skill_uri)

    special_cases = {
        "c#": "cs",
        "ci/cd": "ci_cd",
        "pl/sql": "pl_sql",
    }

    jobs_processed = 0
    jobs_with_skills = 0
    missing_skills_map = {}  # Dictionary to store missing skills by job_url

    for job in jobs_data:
        if "job_url" not in job:
            continue

        # Create job identifier
        job_id = job["job_url"].split("/")[-1]
        if "?" in job_id:
            job_id = job_id.split("?")[0]

        # Create job individual
        job_uri = TALENT_NAMESPACE[f"Job_{job_id}"]
        graph.add((job_uri, RDF.type, TALENT_NAMESPACE["Job"]))
        graph.add(
            (
                job_uri,
                TALENT_NAMESPACE["jobUrl"],
                Literal(job["job_url"], datatype=XSD.string),
            )
        )

        # Add required skills
        skills_added = 0
        missing_skills = []  # List to store missing skills for this job
        if "required_skills" in job and job["required_skills"]:
            for skill in job["required_skills"]:
                skill_lower = skill.lower()

                # Check special cases first
                if skill_lower in special_cases:
                    mapped_skill = special_cases[skill_lower]
                    if mapped_skill in ontology_skills:
                        original_name, original_uri = ontology_skills[mapped_skill]
                        graph.add(
                            (job_uri, TALENT_NAMESPACE["REQUIRED_SKILL"], original_uri)
                        )
                        skills_added += 1
                        continue

                # Regular matching
                if skill_lower in ontology_skills:
                    original_name, original_uri = ontology_skills[skill_lower]
                    graph.add(
                        (job_uri, TALENT_NAMESPACE["REQUIRED_SKILL"], original_uri)
                    )
                    skills_added += 1
                else:
                    # Skill not found in ontology
                    missing_skills.append(skill)

        if skills_added > 0:
            jobs_with_skills += 1

        # Store missing skills for this job
        if missing_skills:
            missing_skills_map[job["job_url"]] = missing_skills

        jobs_processed += 1

    return graph, missing_skills_map


def import_all_users_to_ontology(graph, users_data):
    """Import ALL users to ontology"""
    # Handle empty or None users_data
    if not users_data:
        return graph

    # Get all skills for matching
    all_skills_query = """
    SELECT ?skill
    WHERE {
        ?skill rdfs:subClassOf+ <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Skills> .
    }
    """

    ontology_skills = {}
    for row in graph.query(all_skills_query):
        skill_uri = row[0]
        skill_name = str(skill_uri).split("/")[-1].replace("_", " ")
        ontology_skills[skill_name.lower()] = (skill_name, skill_uri)

    # Special cases
    special_cases = {
        "c#": "cs",
        "ci/cd": "ci_cd",
        "pl/sql": "pl_sql",
    }

    total_skills_added = 0

    for user in users_data:
        # Generate UUID if not exists, or use existing UUID
        if "uuid" in user and user["uuid"]:
            user_uuid = user["uuid"]
        else:
            # Generate new UUID if not provided
            user_uuid = str(uuid.uuid4())

        # Create user individual
        user_uri = TALENT_NAMESPACE[f"User_{user_uuid}"]
        graph.add((user_uri, RDF.type, TALENT_NAMESPACE["User"]))
        graph.add(
            (
                user_uri,
                TALENT_NAMESPACE["email"],
                Literal(user["email"], datatype=XSD.string),
            )
        )

        # Add user skills
        user_skills_added = 0
        for skill in user["skills"]:
            skill_lower = skill.lower()

            # Check special cases first
            if skill_lower in special_cases:
                mapped_skill = special_cases[skill_lower]
                if mapped_skill in ontology_skills:
                    original_name, original_uri = ontology_skills[mapped_skill]
                    graph.add((user_uri, TALENT_NAMESPACE["HAS_SKILL"], original_uri))
                    user_skills_added += 1
                    continue

            # Regular matching
            if skill_lower in ontology_skills:
                original_name, original_uri = ontology_skills[skill_lower]
                graph.add((user_uri, TALENT_NAMESPACE["HAS_SKILL"], original_uri))
                user_skills_added += 1

        total_skills_added += user_skills_added

    return graph


def build_temp_graph_for_user(base_graph, jobs_data, user_email, user_skills):
    """Build temporary graph dengan ALL jobs + specific user only"""
    # Start dengan base ontology
    temp_graph = Graph()
    for s, p, o in base_graph:
        temp_graph.add((s, p, o))
    temp_graph.bind("talent", TALENT_NAMESPACE)

    # Add ALL jobs
    temp_graph = import_all_jobs_to_temp_graph(temp_graph, jobs_data)

    # Add ONLY this specific user
    temp_graph, user_uri = import_specific_user_to_temp_graph(
        temp_graph, user_email, user_skills
    )

    return temp_graph, user_uri


def import_all_jobs_to_temp_graph(graph, jobs_data):
    all_skills_query = """
    SELECT ?skill
    WHERE {
        ?skill rdfs:subClassOf+ <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Skills> .
    }
    """

    ontology_skills = {}
    for row in graph.query(all_skills_query):
        skill_uri = row[0]
        skill_name = str(skill_uri).split("/")[-1].replace("_", " ")
        ontology_skills[skill_name.lower()] = (skill_name, skill_uri)

    special_cases = {
        "c#": "cs",
        "ci/cd": "ci_cd",
        "pl/sql": "pl_sql",
    }

    jobs_added = 0
    for job in jobs_data:
        if "job_url" not in job:
            continue

        # Create job
        job_id = job["job_url"].split("/")[-1]
        if "?" in job_id:
            job_id = job_id.split("?")[0]

        job_uri = TALENT_NAMESPACE[f"Job_{job_id}"]
        graph.add((job_uri, RDF.type, TALENT_NAMESPACE["Job"]))
        graph.add(
            (
                job_uri,
                TALENT_NAMESPACE["jobUrl"],
                Literal(job["job_url"], datatype=XSD.string),
            )
        )

        # Add job skills
        if "required_skills" in job and job["required_skills"]:
            for skill in job["required_skills"]:
                skill_lower = skill.lower()

                if skill_lower in special_cases:
                    mapped_skill = special_cases[skill_lower]
                    if mapped_skill in ontology_skills:
                        original_name, original_uri = ontology_skills[mapped_skill]
                        graph.add(
                            (job_uri, TALENT_NAMESPACE["REQUIRED_SKILL"], original_uri)
                        )
                        continue

                if skill_lower in ontology_skills:
                    original_name, original_uri = ontology_skills[skill_lower]
                    graph.add(
                        (job_uri, TALENT_NAMESPACE["REQUIRED_SKILL"], original_uri)
                    )

        jobs_added += 1

    return graph


def import_specific_user_to_temp_graph(graph, user_email, user_skills):
    """Import specific user ke temporary graph"""
    # Get skill mappings
    all_skills_query = """
    SELECT ?skill
    WHERE {
        ?skill rdfs:subClassOf+ <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Skills> .
    }
    """

    ontology_skills = {}
    for row in graph.query(all_skills_query):
        skill_uri = row[0]
        skill_name = str(skill_uri).split("/")[-1].replace("_", " ")
        ontology_skills[skill_name.lower()] = (skill_name, skill_uri)

    special_cases = {
        "c#": "cs",
        "ci/cd": "ci_cd",
        "pl/sql": "pl_sql",
    }

    user_uuid = str(uuid.uuid4())
    user_uri = TALENT_NAMESPACE[f"User_{user_uuid}"]
    graph.add((user_uri, RDF.type, TALENT_NAMESPACE["User"]))
    graph.add(
        (user_uri, TALENT_NAMESPACE["email"], Literal(user_email, datatype=XSD.string))
    )

    # Add user skills
    skills_added = 0
    for skill in user_skills:
        skill_lower = skill.lower()

        if skill_lower in special_cases:
            mapped_skill = special_cases[skill_lower]
            if mapped_skill in ontology_skills:
                original_name, original_uri = ontology_skills[mapped_skill]
                graph.add((user_uri, TALENT_NAMESPACE["HAS_SKILL"], original_uri))
                skills_added += 1
                continue

        if skill_lower in ontology_skills:
            original_name, original_uri = ontology_skills[skill_lower]
            graph.add((user_uri, TALENT_NAMESPACE["HAS_SKILL"], original_uri))
            skills_added += 1

    return graph, user_uri


def calculate_user_job_similarity_for_specific_user(graph, user_uri):
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
        <{user_uri}> <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/HAS_SKILL> ?skill .
    }}
    """
    user_skills = [row[0] for row in graph.query(user_skills_query)]

    if not user_skills:
        return []

    match_results = []
    for job_uri in jobs:
        # Get job skills
        job_skills_query = f"""
        SELECT ?skill
        WHERE {{
            <{job_uri}> <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/REQUIRED_SKILL> ?skill .
        }}
        """
        job_skills = [row[0] for row in graph.query(job_skills_query)]

        if not job_skills:
            continue

        # Calculate similarity using your existing algorithm
        skill_similarities = []
        for user_skill in user_skills:
            user_skill_features = get_limited_ancestors(graph, user_skill)
            max_skill_similarity = 0

            for job_skill in job_skills:
                job_skill_features = get_limited_ancestors(graph, job_skill)
                skill_similarity = sanchez_similarity(
                    user_skill_features, job_skill_features
                )
                if skill_similarity > max_skill_similarity:
                    max_skill_similarity = skill_similarity

            skill_similarities.append(max_skill_similarity)

        # Calculate overall similarity
        skill_similarities = sorted(skill_similarities, reverse=True)
        if skill_similarities:
            overall_similarity = sum(skill_similarities[0 : len(job_skills)]) / len(
                job_skills
            )
            if overall_similarity > 0:
                match_results.append(
                    {
                        "user": str(user_uri),
                        "job": str(job_uri),
                        "similarity": overall_similarity,
                    }
                )

    return match_results


def extract_categorized_matches_for_user(graph, user_uri):
    """
    Extract categorized matches untuk specific user setelah dynamic categorization
    """
    categorized_matches = []

    # Query untuk mendapatkan semua matches yang sudah dikategorisasi untuk user ini
    categorized_query = f"""
    SELECT ?match ?similarity ?matchType ?job
    WHERE {{
        ?match rdf:type <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/UserJobMatch> .
        ?match <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/USER_MATCH> <{user_uri}> .
        ?match <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/similarityScore> ?similarity .
        ?match <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/JOB_MATCH> ?job .
        ?match <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/matchType> ?matchType .
    }}
    """

    matches = list(graph.query(categorized_query))

    for match, similarity, match_type, job in matches:
        categorized_matches.append(
            {
                "match_uri": str(match),
                "job_uri": str(job),
                "similarity": float(similarity),
                "category": str(match_type),
            }
        )

    return categorized_matches


def add_user_job_matches_to_ontology(graph, match_results):
    """Add UserJobMatch instances ke graph"""
    for match in match_results:
        match_id = str(uuid.uuid4())
        match_uri = TALENT_NAMESPACE[f"UserJobMatch_{match_id}"]

        graph.add((match_uri, RDF.type, TALENT_NAMESPACE["UserJobMatch"]))
        graph.add((match_uri, TALENT_NAMESPACE["USER_MATCH"], URIRef(match["user"])))
        graph.add((match_uri, TALENT_NAMESPACE["JOB_MATCH"], URIRef(match["job"])))
        graph.add(
            (
                match_uri,
                TALENT_NAMESPACE["similarityScore"],
                Literal(match["similarity"], datatype=XSD.float),
            )
        )

    return graph


def sanchez_similarity(set_a, set_b):
    """Calculate Sánchez similarity between two sets"""
    if set_a == set_b:
        return 1.0

    a_minus_b = len(set_a - set_b)
    b_minus_a = len(set_b - set_a)
    intersection = len(set_a.intersection(set_b))

    if intersection == 0:
        return 0.0

    numerator = a_minus_b + b_minus_a
    denominator = a_minus_b + b_minus_a + intersection

    similarity = 1 - math.log2(1 + numerator / denominator)
    return similarity


def get_limited_ancestors(graph, skill_uri, max_levels=5):
    """Get skill and its ancestors (up to 3 levels), stopping at Skills node"""
    ancestors = set()
    ancestors.add(str(skill_uri))

    # Define Skills top-level node
    SKILLS_NODE = "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Skills"

    current_level = [skill_uri]
    level = 0

    while current_level and level < max_levels:
        next_level = []
        for node in current_level:
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

                if parent_str == SKILLS_NODE:
                    current_level = max_levels
                    level = max_levels
                    continue

                if parent_str not in ancestors:
                    ancestors.add(parent_str)
                    next_level.append(parent)

        current_level = next_level
        level += 1

    return ancestors


def calculate_all_user_job_similarities(graph):
    """Calculate similarities between ALL users and ALL jobs at once"""
    users_query = """
    SELECT ?user ?email
    WHERE {
        ?user rdf:type <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/User> .
        ?user <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/email> ?email .
    }
    """

    jobs_query = """
    SELECT ?job
    WHERE {
        ?job rdf:type <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/Job> .
    }
    """

    users = [(row[0], str(row[1])) for row in graph.query(users_query)]
    jobs = [row[0] for row in graph.query(jobs_query)]

    match_results = []
    processed_combinations = 0

    for user_uri, email in users:
        user_skills_query = f"""
        SELECT ?skill
        WHERE {{
            <{user_uri}> <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/HAS_SKILL> ?skill .
        }}
        """

        user_skills = [row[0] for row in graph.query(user_skills_query)]

        if not user_skills:
            continue

        user_matches = 0

        for job_uri in jobs:
            job_skills_query = f"""
            SELECT ?skill
            WHERE {{
                <{job_uri}> <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/REQUIRED_SKILL> ?skill .
            }}
            """

            job_skills = [row[0] for row in graph.query(job_skills_query)]

            if not job_skills:
                continue

            skill_similarities = []

            for user_skill in user_skills:
                user_skill_features = get_limited_ancestors(graph, user_skill)
                max_skill_similarity = 0

                for job_skill in job_skills:
                    job_skill_features = get_limited_ancestors(graph, job_skill)
                    skill_similarity = sanchez_similarity(
                        user_skill_features, job_skill_features
                    )

                    if skill_similarity > max_skill_similarity:
                        max_skill_similarity = skill_similarity

                skill_similarities.append(max_skill_similarity)

            # Calculate overall similarity
            if skill_similarities:
                overall_similarity = sum(skill_similarities) / len(skill_similarities)

                if overall_similarity > 0:
                    match_results.append(
                        {
                            "user": user_uri,
                            "job": job_uri,
                            "similarity": overall_similarity,
                        }
                    )
                    user_matches += 1

            processed_combinations += 1

    return match_results


def extract_equivalent_class_rules_from_ontology(graph):
    """Extract equivalent class rules for UserJobMatch subclasses from ontology"""
    rules = {}

    # Query untuk mengambil equivalent class definitions yang lebih kompleks
    equivalent_rules_query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX : <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/>
    
    SELECT ?class ?restriction ?property ?datatype ?minValue ?maxValue ?minInclusive ?maxInclusive ?minExclusive ?maxExclusive
    WHERE {
        ?class owl:equivalentClass ?equivalentClass .
        ?equivalentClass owl:intersectionOf ?intersection .
        
        # Navigate through the intersection list
        ?intersection rdf:rest*/rdf:first ?restriction .
        
        # Filter for restriction nodes
        FILTER(isBlank(?restriction))
        
        ?restriction owl:onProperty ?property .
        ?restriction owl:someValuesFrom ?valueRestriction .
        
        # Get datatype restriction details
        ?valueRestriction owl:onDatatype ?datatype .
        ?valueRestriction owl:withRestrictions ?restrictionList .
        
        # Navigate through restriction list
        ?restrictionList rdf:rest*/rdf:first ?individualRestriction .
        
        OPTIONAL { ?individualRestriction xsd:minInclusive ?minInclusive }
        OPTIONAL { ?individualRestriction xsd:maxInclusive ?maxInclusive }
        OPTIONAL { ?individualRestriction xsd:minExclusive ?minExclusive }
        OPTIONAL { ?individualRestriction xsd:maxExclusive ?maxExclusive }
        
        FILTER(
            ?class = :Strong_Match ||
            ?class = :Mid_Match ||
            ?class = :Weak_Match
        )
        
        FILTER(?property = :similarityScore)
    }
    """

    try:
        results = list(graph.query(equivalent_rules_query))
        print(f"   Found {len(results)} equivalent class restriction details")

        # Group results by class
        class_restrictions = {}
        for row in results:
            class_uri = str(row[0])
            class_name = class_uri.split("/")[-1]

            if class_name not in class_restrictions:
                class_restrictions[class_name] = []

            class_restrictions[class_name].append(
                {
                    "minInclusive": float(row[6]) if row[6] else None,
                    "maxInclusive": float(row[7]) if row[7] else None,
                    "minExclusive": float(row[8]) if row[8] else None,
                    "maxExclusive": float(row[9]) if row[9] else None,
                }
            )

        # Convert to rules format
        for class_name, restrictions in class_restrictions.items():
            if class_name == "Strong_Match":
                # Find minInclusive value (should be 0.75)
                for restriction in restrictions:
                    if restriction["minInclusive"] is not None:
                        rules["Strong_Match"] = {
                            "property": "similarityScore",
                            "operator": ">=",
                            "threshold": restriction["minInclusive"],
                        }
                        print(
                            f"   Extracted Strong_Match rule: >= {restriction['minInclusive']}"
                        )
                        break

            elif class_name == "Mid_Match":
                # Find range values (should be 0.25 < x < 0.75)
                min_val = None
                max_val = None
                for restriction in restrictions:
                    if restriction["minExclusive"] is not None:
                        min_val = restriction["minExclusive"]
                    if restriction["maxExclusive"] is not None:
                        max_val = restriction["maxExclusive"]

                if min_val is not None and max_val is not None:
                    rules["Mid_Match"] = {
                        "property": "similarityScore",
                        "operator": "range",
                        "min_threshold": min_val,
                        "max_threshold": max_val,
                    }
                    print(f"   Extracted Mid_Match rule: {min_val} < x < {max_val}")

            elif class_name == "Weak_Match":
                # Find maxInclusive value (should be 0.25)
                for restriction in restrictions:
                    if restriction["maxInclusive"] is not None:
                        rules["Weak_Match"] = {
                            "property": "similarityScore",
                            "operator": "<=",
                            "threshold": restriction["maxInclusive"],
                        }
                        print(
                            f"   Extracted Weak_Match rule: <= {restriction['maxInclusive']}"
                        )
                        break

        print(f"   Successfully extracted {len(rules)} rules from ontology")

    except Exception as e:
        print(f"   Error extracting rules from ontology: {e}")
        print("   Falling back to simple threshold rules")

    # Fallback ke rules default jika tidak ada di ontology atau error
    if not rules:
        print("   No rules found in ontology, using simple threshold rules")
        rules = create_simple_threshold_rules()

    return rules


def create_simple_threshold_rules():
    """Create simple threshold-based rules (fallback)"""
    return {
        "Strong_Match": {
            "property": "similarityScore",
            "operator": ">=",
            "threshold": 0.75,
        },
        "Mid_Match": {
            "property": "similarityScore",
            "operator": "range",
            "min_threshold": 0.25,
            "max_threshold": 0.75,
        },
        "Weak_Match": {
            "property": "similarityScore",
            "operator": "<",
            "threshold": 0.25,
        },
    }


def apply_dynamic_categorization(graph, rules):
    """Apply categorization based on rules extracted from ontology"""
    # Get all UserJobMatch with similarity scores
    matches_query = """
    SELECT ?match ?similarity
    WHERE {
        ?match rdf:type <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/UserJobMatch> .
        ?match <http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/similarityScore> ?similarity .
    }
    """

    matches = list(graph.query(matches_query))

    if len(matches) == 0:
        return graph

    categorization_counts = {"Strong_Match": 0, "Mid_Match": 0, "Weak_Match": 0}

    for match, similarity in matches:
        score = float(similarity)

        # Apply rules dynamically
        for category, rule in rules.items():
            if evaluate_rule(score, rule):
                # Convert category name to simple form
                if category == "Strong_Match":
                    match_type = "Strong"
                elif category == "Mid_Match":
                    match_type = "Mid"
                elif category == "Weak_Match":
                    match_type = "Weak"

                graph.add(
                    (
                        match,
                        TALENT_NAMESPACE["matchType"],
                        Literal(match_type, datatype=XSD.string),
                    )
                )
                categorization_counts[category] += 1
                break  # Stop after first match

    return graph


def evaluate_rule(score, rule):
    """Evaluate a single rule against a similarity score"""
    operator = rule["operator"]

    if operator == ">=":
        return score >= rule["threshold"]
    elif operator == "<=":
        return score <= rule["threshold"]
    elif operator == "<":
        return score < rule["threshold"]
    elif operator == ">":
        return score > rule["threshold"]
    elif operator == "range":
        return rule["min_threshold"] < score < rule["max_threshold"]
    elif operator == "range_inclusive":
        return rule["min_threshold"] <= score <= rule["max_threshold"]

    return False


def apply_dynamic_categorization_pipeline(graph):
    """Simple pipeline to extract rules and apply them"""
    # Step 1: Extract rules from ontology equivalent classes
    rules = extract_equivalent_class_rules_from_ontology(graph)

    # Step 2: Apply categorization using extracted rules
    graph = apply_dynamic_categorization(graph, rules)

    return graph
