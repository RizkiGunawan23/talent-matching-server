from rest_framework import status
from rest_framework.exceptions import APIException

from api.models import Job, UserJobMatch


def get_job_list_with_skills() -> list[dict[str, str | int | list[str] | None]]:
    """Get all jobs with their required skills"""
    try:
        jobs = Job.all_with_skills()
        jobs_list = []

        for item in jobs:
            job: Job = item.get("job")
            skills = [skill.name for skill in item["skills"]]

            job_data = {
                "job_url": job.jobUrl,
                "job_title": job.jobTitle,
                "company_name": job.companyName,
                "province": job.province,
                "employment_type": job.employmentType,
                "minimum_salary": job.minimumSalary,
                "maximum_salary": job.maximumSalary,
                "required_skills": skills,
                "scraped_at": job.scrapedAt,
            }
            jobs_list.append(job_data)

        return jobs_list
    except Exception:
        raise APIException(
            detail="Error saat mengambil daftar pekerjaan",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def get_job_detail_with_skills(job_url: str) -> dict[str, str | int | list[str] | None]:
    """Get detailed job information with skills"""
    try:
        job: Job = Job.nodes.get_or_none(jobUrl=job_url)
        if not job:
            raise APIException(
                detail="Job not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        # Get job skills
        skills = [skill.name for skill in job.skills.all()]

        job_data = {
            "job_url": job.jobUrl,
            "image_url": job.imageUrl,
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

        return job_data
    except APIException:
        raise
    except Exception as e:
        raise APIException(
            detail=f"Error retrieving job detail: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def delete_multiple_jobs(job_urls: list[str]) -> dict[str, any]:
    """Delete multiple jobs with complete cleanup"""
    if not job_urls:
        raise APIException(
            detail="Job URLs list cannot be empty",
            code=status.HTTP_400_BAD_REQUEST,
        )

    deleted_jobs = []
    failed_jobs = []
    total_cleanup_stats = {
        "skills_disconnected": 0,
        "orphaned_skills_deleted": 0,
        "additional_skills_disconnected": 0,
        "orphaned_additional_skills_deleted": 0,
        "user_job_matches_deleted": 0,
        "bookmarks_removed": 0,
        "reports_removed": 0,
    }

    for job_url in job_urls:
        try:
            job: Job = Job.nodes.get_or_none(jobUrl=job_url)
            if not job:
                failed_jobs.append({"job_url": job_url, "reason": "Job not found"})
                continue

            cleanup_stats = _cleanup_job_relationships(job)

            # Aggregate cleanup stats
            for key, value in cleanup_stats.items():
                total_cleanup_stats[key] += value

            # Delete the job
            job.delete()
            deleted_jobs.append(job_url)

        except Exception as e:
            failed_jobs.append({"job_url": job_url, "reason": str(e)})

    return {
        "deleted_count": len(deleted_jobs),
        "deleted_jobs": deleted_jobs,
        "failed_count": len(failed_jobs),
        "failed_jobs": failed_jobs,
        "cleanup_stats": total_cleanup_stats,
        "message": f"Berhasil menghapus {len(deleted_jobs)} pekerjaan, {len(failed_jobs)} gagal",
    }


def _cleanup_job_relationships(job: Job) -> dict[str, int]:
    """Cleanup all relationships and orphaned nodes when deleting a job"""
    cleanup_stats = {
        "skills_disconnected": 0,
        "orphaned_skills_deleted": 0,
        "additional_skills_disconnected": 0,
        "orphaned_additional_skills_deleted": 0,
        "user_job_matches_deleted": 0,
        "bookmarks_removed": 0,
        "reports_removed": 0,
    }

    try:
        # 1. Handle Skills relationships
        connected_skills = list(job.skills.all())
        if connected_skills:
            job.skills.disconnect_all()
            cleanup_stats["skills_disconnected"] = len(connected_skills)

            # Check for orphaned skills and delete them
            for skill in connected_skills:
                try:
                    # Check if this skill is still connected to any other job
                    remaining_jobs = skill.job_set.all()
                    if len(remaining_jobs) == 0:
                        # Also check if any user has this skill
                        users_with_skill = skill.user_set.all()
                        if len(users_with_skill) == 0:
                            skill.delete()
                            cleanup_stats["orphaned_skills_deleted"] += 1
                except Exception as e:
                    print(
                        f"[CLEANUP_WARNING] Error checking skill {skill.name}: {str(e)}"
                    )

        # 2. Handle AdditionalSkills relationships
        try:
            connected_additional_skills = list(job.additional_skills.all())
            if connected_additional_skills:
                job.additional_skills.disconnect_all()
                cleanup_stats["additional_skills_disconnected"] = len(
                    connected_additional_skills
                )

                # Check for orphaned additional skills and delete them
                for additional_skill in connected_additional_skills:
                    try:
                        remaining_jobs = additional_skill.job_set.all()
                        if len(remaining_jobs) == 0:
                            additional_skill.delete()
                            cleanup_stats["orphaned_additional_skills_deleted"] += 1
                    except Exception as e:
                        print(
                            f"[CLEANUP_WARNING] Error checking additional skill: {str(e)}"
                        )
        except AttributeError:
            # If additional_skills relationship doesn't exist, skip
            print("[CLEANUP_INFO] No additional_skills relationship found")

        # 3. Handle UserJobMatch relationships
        from neomodel import db

        # More efficient approach using Cypher query
        match_delete_query = """
        MATCH (m:UserJobMatch)-[:JOB_MATCH]->(j:Job {jobUrl: $job_url})
        OPTIONAL MATCH (m)-[r1:USER_MATCH]->(u:User)
        OPTIONAL MATCH (m)-[r2:JOB_MATCH]->(j2:Job)
        DELETE r1, r2, m
        RETURN count(m) as deleted_matches
        """

        results, meta = db.cypher_query(match_delete_query, {"job_url": job.jobUrl})
        if results:
            cleanup_stats["user_job_matches_deleted"] = results[0][0]

        # 4. Handle user bookmarks (HAS_BOOKMARKED relationship)
        bookmark_query = """
        MATCH (u:User)-[r:HAS_BOOKMARKED]->(j:Job {jobUrl: $job_url})
        DELETE r
        RETURN count(r) as bookmark_count
        """

        results, meta = db.cypher_query(bookmark_query, {"job_url": job.jobUrl})
        if results:
            cleanup_stats["bookmarks_removed"] = results[0][0]

        # 5. Handle user reports (HAS_REPORTED relationship)
        report_query = """
        MATCH (u:User)-[r:HAS_REPORTED]->(j:Job {jobUrl: $job_url})
        DELETE r
        RETURN count(r) as report_count
        """

        results, meta = db.cypher_query(report_query, {"job_url": job.jobUrl})
        if results:
            cleanup_stats["reports_removed"] = results[0][0]

        print(f"[CLEANUP] Job {job.jobUrl} cleanup completed: {cleanup_stats}")

    except Exception as e:
        print(f"[CLEANUP_ERROR] Error during cleanup for job {job.jobUrl}: {str(e)}")
        # Don't raise exception here, let the main delete continue

    return cleanup_stats
