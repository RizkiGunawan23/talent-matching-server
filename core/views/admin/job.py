import os
from datetime import datetime

from django.conf import settings
from neomodel import db
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

# Base directory for file storage
FILE_STORAGE_DIR = os.path.join(settings.BASE_DIR, "uploaded_files/ontology")
os.makedirs(FILE_STORAGE_DIR, exist_ok=True)


class AdminJobView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request: Request) -> Response:
        try:
            cypher = """
            MATCH (j:Job)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(a:AdditionalSkill)
            RETURN j, collect(DISTINCT s.name) + collect(DISTINCT a.name) AS requiredSkills
            """
            results, meta = db.cypher_query(cypher)
            jobs_data = []
            for record in results:
                job_node = record[0]
                required_skills = [name for name in record[1] if name]  # filter None
                job_dict = dict(job_node)
                job_dict["requiredSkills"] = required_skills
                jobs_data.append(job_dict)
            return Response(
                {
                    "message": "Successfully fetch job data",
                    "data": jobs_data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # def delete(self, request: Request) -> Response:
    #     try:
    #         job_id = request.query_params.get("id")
    #         if not job_id:
    #             return Response(
    #                 {"message": "Job ID is required"},
    #                 status=status.HTTP_400_BAD_REQUEST,
    #             )

    #         job = Job.nodes.get_or_none(uid=job_id)
    #         if not job:
    #             return Response(
    #                 {"message": "Job not found"}, status=status.HTTP_404_NOT_FOUND
    #             )

    #         db.begin()
    #         try:
    #             job.delete()
    #             db.commit()
    #             return Response(
    #                 {"message": "Job deleted successfully"}, status=status.HTTP_200_OK
    #             )
    #         except Exception as e:
    #             db.rollback()
    #             return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    #     except Exception as e:
    #         return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminJobDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        try:
            job_url = request.data.get("job_url")
            if not job_url:
                return Response(
                    {"message": "Job URL is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Decode jobUrl
            cypher = """
            MATCH (j:Job {jobUrl: $job_url})
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(s:Skill)
            OPTIONAL MATCH (j)-[:REQUIRED_SKILL]->(a:AdditionalSkill)
            RETURN j, collect(DISTINCT s.name) + collect(DISTINCT a.name) AS requiredSkills
            """
            results, meta = db.cypher_query(cypher, {"job_url": job_url})
            if not results:
                return Response(
                    {"message": "Job not found"}, status=status.HTTP_404_NOT_FOUND
                )
            record = results[0]
            job_node = record[0]
            required_skills = [name for name in record[1] if name]
            job_dict = dict(job_node)
            job_dict["requiredSkills"] = required_skills
            return Response(
                {
                    "message": "Successfully fetch job detail",
                    "data": job_dict,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
