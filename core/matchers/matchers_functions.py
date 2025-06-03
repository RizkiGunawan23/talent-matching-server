from rdflib import Namespace

from core.matchers.helper import is_task_cancelled, update_task_progress
from core.matchers.neo4j_functions import (
    create_calculated_user,
    get_jobs_from_neo4j,
    get_users_from_neo4j,
    import_and_clean_neo4j_with_enrichment,
    set_maintenance,
    update_neo4j_for_specific_user,
)
from core.matchers.ontology_functions import (
    add_user_job_matches_to_ontology,
    apply_dynamic_categorization_pipeline,
    build_temp_graph_for_user,
    calculate_all_user_job_similarities,
    calculate_user_job_similarity_for_specific_user,
    extract_categorized_matches_for_user,
    import_all_jobs_to_ontology,
    import_all_users_to_ontology,
    load_base_ontology,
)


def matching_after_scraping(task_id, update_state_func=None, jobs_data=[]):
    TALENT = Namespace(
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/"
    )

    try:
        set_maintenance(is_maintenance=True)

        if is_task_cancelled(task_id):
            return

        main_graph = load_base_ontology()

        if is_task_cancelled(task_id):
            return

        users_data = get_users_from_neo4j()

        if is_task_cancelled(task_id):
            return

        if update_state_func:
            update_task_progress(
                task_id,
                "IMPORTING_JOB_TO_ONTOLOGY",
                {},
                update_state_func,
            )

        if not jobs_data:
            raise ValueError("Jobs is empty. Cannot proceed.")

        users_count = len(users_data)

        main_graph, missing_skills_map = import_all_jobs_to_ontology(
            main_graph, TALENT, jobs_data
        )

        if is_task_cancelled(task_id):
            return

        if update_state_func:
            update_task_progress(
                task_id,
                "IMPORTING_USER_TO_ONTOLOGY",
                {},
                update_state_func,
            )

        main_graph = import_all_users_to_ontology(main_graph, TALENT, users_data)

        if is_task_cancelled(task_id):
            return

        if users_count > 0:
            if update_state_func:
                update_task_progress(
                    task_id,
                    "MATCHING_BETWEEN_USERS_AND_JOBS",
                    {},
                    update_state_func,
                )

            match_results = calculate_all_user_job_similarities(main_graph)

            if is_task_cancelled(task_id):
                return

            main_graph = add_user_job_matches_to_ontology(
                main_graph, TALENT, match_results
            )

            if is_task_cancelled(task_id):
                return

            if update_state_func:
                update_task_progress(
                    task_id,
                    "REASONING",
                    {},
                    update_state_func,
                )

            main_graph = apply_dynamic_categorization_pipeline(main_graph, TALENT)

            if is_task_cancelled(task_id):
                return

        import_and_clean_neo4j_with_enrichment(
            main_graph,
            users_data=users_data,
            jobs_data=jobs_data,
            missing_skills_map=missing_skills_map,
            task_id=task_id,
            update_state_func=update_state_func,
        )

        print("\n✅ Matching completed successfully.")

    except Exception as e:
        print(f"\n❌ Error during processing: {e}")


def create_user_and_calculate_matches(new_user_data):
    from rdflib import Namespace

    TALENT = Namespace(
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/"
    )

    user_email = new_user_data["email"]
    user_skills = new_user_data["skills"]

    base_graph = load_base_ontology()

    jobs_data = get_jobs_from_neo4j()

    temp_graph, user_uri = build_temp_graph_for_user(
        base_graph, jobs_data, user_email, user_skills, TALENT
    )

    new_matches = calculate_user_job_similarity_for_specific_user(temp_graph, user_uri)

    temp_graph = add_user_job_matches_to_ontology(temp_graph, TALENT, new_matches)

    temp_graph = apply_dynamic_categorization_pipeline(temp_graph, TALENT)

    categorized_matches = extract_categorized_matches_for_user(
        temp_graph, user_uri, TALENT
    )

    created_user = create_calculated_user(new_user_data, categorized_matches)

    return {
        "uid": created_user["uid"],
        "name": created_user["name"],
        "email": created_user["email"],
        "password": created_user["password"],
        "profile_image": created_user["profile_image"],
        "role": created_user["role"],
        "skills": created_user["skills"],
    }


def update_user_skills_and_recalculate_matches(user_email, new_skills):
    """
    Update user skills dan recalculate matches hanya untuk user tersebut
    tanpa mengganggu matches user lain
    """
    TALENT = Namespace(
        "http://www.semanticweb.org/kota203/ontologies/2025/3/talent-matching-ontology/"
    )

    base_graph = load_base_ontology()

    jobs_data = get_jobs_from_neo4j()

    temp_graph, user_uri = build_temp_graph_for_user(
        base_graph, jobs_data, user_email, new_skills, TALENT
    )

    new_matches = calculate_user_job_similarity_for_specific_user(temp_graph, user_uri)

    temp_graph = add_user_job_matches_to_ontology(temp_graph, TALENT, new_matches)

    temp_graph = apply_dynamic_categorization_pipeline(temp_graph, TALENT)

    categorized_matches = extract_categorized_matches_for_user(
        temp_graph, user_uri, TALENT
    )

    update_neo4j_for_specific_user(user_email, new_skills, categorized_matches)
