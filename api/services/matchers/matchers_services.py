from api.models import Maintenance
from api.services.matchers.helper import update_task_progress
from api.services.matchers.matchers_neo4j_services import (
    get_jobs_from_neo4j,
    get_users_from_neo4j,
    import_and_clean_neo4j_with_enrichment,
    update_neo4j_for_specific_user,
)
from api.services.matchers.matchers_ontology_services import (
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
    try:
        Maintenance.set_maintenance(True)

        main_graph = load_base_ontology()

        users_data = get_users_from_neo4j()

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
            main_graph, jobs_data
        )

        if update_state_func:
            update_task_progress(
                task_id,
                "IMPORTING_USER_TO_ONTOLOGY",
                {},
                update_state_func,
            )

        main_graph = import_all_users_to_ontology(main_graph, users_data)

        if users_count > 0:
            if update_state_func:
                update_task_progress(
                    task_id,
                    "MATCHING_BETWEEN_USERS_AND_JOBS",
                    {},
                    update_state_func,
                )

            match_results = calculate_all_user_job_similarities(main_graph)

            main_graph = add_user_job_matches_to_ontology(main_graph, match_results)

            if update_state_func:
                update_task_progress(
                    task_id,
                    "REASONING",
                    {},
                    update_state_func,
                )

            main_graph = apply_dynamic_categorization_pipeline(main_graph)

        import_and_clean_neo4j_with_enrichment(
            main_graph,
            users_data=users_data,
            jobs_data=jobs_data,
            missing_skills_map=missing_skills_map,
            task_id=task_id,
            update_state_func=update_state_func,
        )
        Maintenance.set_maintenance(False)
    except Exception as e:
        Maintenance.set_maintenance(False)
