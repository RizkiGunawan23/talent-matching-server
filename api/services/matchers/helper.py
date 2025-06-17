from django.core.cache import cache


def is_task_cancelled(task_id: str) -> bool:
    """Check if a task is cancelled by checking the cache."""
    return cache.get(f"matching_cancel_{task_id}") == True


def update_task_progress(
    task_id: str, state: str, progress_data: dict[str, any], update_state_func=None
):
    """
    Update the progress of a matching task in the cache and optionally call a state update function.
    """
    cache.set(f"matching_progress_{task_id}", progress_data, timeout=None)
    if update_state_func:
        update_state_func(state=state, meta=progress_data)
