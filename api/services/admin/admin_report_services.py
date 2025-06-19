from neomodel import db
from rest_framework import status
from rest_framework.exceptions import APIException

from api.models import HasReportedRel, Job, User


def get_report_list_with_job() -> list[dict[str, any]]:
    """Get all reports with job information"""
    try:
        # Query untuk mendapatkan semua report dengan detail user dan job
        query = """
        MATCH (u:User)-[r:HAS_REPORTED]->(j:Job)
        RETURN u, r, j
        ORDER BY r.reportDate DESC
        """

        results, meta = db.cypher_query(query)

        reports_list = []
        for row in results:
            user_data = row[0]
            report_rel = row[1]
            job_data = row[2]

            report_info = {
                "user_uid": user_data["uid"],
                "user_name": user_data["name"],
                "user_email": user_data["email"],
                "job_url": job_data["jobUrl"],
                "job_title": job_data["jobTitle"],
                "company_name": job_data["companyName"],
                "report_type": report_rel["reportType"],
                "report_description": report_rel["reportDescription"],
                "report_date": report_rel["reportDate"],
                "report_status": report_rel["reportStatus"],
            }
            reports_list.append(report_info)

        return reports_list

    except Exception as e:
        raise APIException(
            detail=f"Error retrieving reports: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def get_report_detail_with_job_and_skills(
    user_uid: str, job_url: str
) -> dict[str, any]:
    """Get detailed report information with job and skills"""
    try:
        # Cari user berdasarkan UID
        user = User.nodes.get_or_none(uid=user_uid)
        if not user:
            raise APIException(
                detail="User not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        # Cari job berdasarkan URL
        job = Job.nodes.get_or_none(jobUrl=job_url)
        if not job:
            raise APIException(
                detail="Job not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        # Cari report relationship
        query = """
        MATCH (u:User {uid: $user_uid})-[r:HAS_REPORTED]->(j:Job {jobUrl: $job_url})
        RETURN r
        """

        results, meta = db.cypher_query(
            query, {"user_uid": user_uid, "job_url": job_url}
        )

        if not results:
            raise APIException(
                detail="Report not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        report_rel = results[0][0]

        # Get job skills
        job_skills = [skill.name for skill in job.skills.all()]
        additional_skills = [skill.name for skill in job.additional_skills.all()]

        # Get user skills
        user_skills = [skill.name for skill in user.has_skill.all()]

        report_detail = {
            "user_info": {
                "uid": user.uid,
                "name": user.name,
                "email": user.email,
                "profile_picture": user.profilePicture,
                "skills": user_skills,
            },
            "job_info": {
                "job_url": job.jobUrl,
                "image_url": job.imageUrl,
                "job_title": job.jobTitle,
                "company_name": job.companyName,
                "location": f"{job.city}, {job.province}",
                "employment_type": job.employmentType,
                "work_setup": job.workSetup,
                "minimum_salary": job.minimumSalary,
                "maximum_salary": job.maximumSalary,
                "minimum_education": job.minimumEducation,
                "minimum_experience": job.minimumExperience,
                "maximum_experience": job.maximumExperience,
                "job_description": job.jobDescription,
                "required_skills": job_skills,
                "additional_skills": additional_skills,
                "scraped_at": job.scrapedAt,
            },
            "report_info": {
                "report_type": report_rel["reportType"],
                "report_description": report_rel["reportDescription"],
                "report_date": report_rel["reportDate"],
                "report_status": report_rel["reportStatus"],
            },
        }

        return report_detail

    except APIException:
        raise
    except Exception as e:
        raise APIException(
            detail=f"Error retrieving report detail: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def approve_report(user_uid: str, job_url: str) -> dict[str, str]:
    """Approve a report and delete the reported job"""
    try:
        # Verify user exists
        user = User.nodes.get_or_none(uid=user_uid)
        if not user:
            raise APIException(
                detail="User not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        # Verify job exists
        job = Job.nodes.get_or_none(jobUrl=job_url)
        if not job:
            raise APIException(
                detail="Job not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        # Update report status to APPROVED
        query = """
        MATCH (u:User {uid: $user_uid})-[r:HAS_REPORTED]->(j:Job {jobUrl: $job_url})
        SET r.reportStatus = 'Sudah Ditinjau'
        RETURN r
        """

        results, meta = db.cypher_query(
            query, {"user_uid": user_uid, "job_url": job_url}
        )

        if not results:
            raise APIException(
                detail="Report not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        # Delete the job (this will also cleanup relationships)
        from api.services.admin.admin_job_services import _cleanup_job_relationships

        cleanup_stats = _cleanup_job_relationships(job)
        job.delete()

        return {
            "message": f"Report approved and job {job_url} has been deleted",
            "cleanup_stats": cleanup_stats,
            "user_uid": user_uid,
            "job_url": job_url,
        }

    except APIException:
        raise
    except Exception as e:
        raise APIException(
            detail=f"Error approving report: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def reject_report(
    user_uid: str, job_url: str, rejection_reason: str = ""
) -> dict[str, str]:
    """Reject a report"""
    try:
        # Verify user exists
        user = User.nodes.get_or_none(uid=user_uid)
        if not user:
            raise APIException(
                detail="User not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        # Verify job exists
        job = Job.nodes.get_or_none(jobUrl=job_url)
        if not job:
            raise APIException(
                detail="Job not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        # Update report status to REJECTED
        query = """
        MATCH (u:User {uid: $user_uid})-[r:HAS_REPORTED]->(j:Job {jobUrl: $job_url})
        SET r.reportStatus = 'Sudah Ditinjau'
        RETURN r
        """

        results, meta = db.cypher_query(
            query, {"user_uid": user_uid, "job_url": job_url}
        )

        if not results:
            raise APIException(
                detail="Report not found",
                code=status.HTTP_404_NOT_FOUND,
            )

        return {
            "message": f"Report rejected for job {job_url}",
            "user_uid": user_uid,
            "job_url": job_url,
            "rejection_reason": rejection_reason,
        }

    except APIException:
        raise
    except Exception as e:
        raise APIException(
            detail=f"Error rejecting report: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
