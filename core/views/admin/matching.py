import datetime

from celery.result import AsyncResult
from django.core.cache import cache
from django.utils import timezone
from neomodel import db
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import ScrapingTask
from core.tasks import matching_job_after_scraping


class JobMatchingAfterScrapingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        try:
            scraping_task: ScrapingTask | None = (
                ScrapingTask.nodes.filter(status__in=["FINISHED"])
                .order_by("-startedAt")
                .first_or_none()
            )
            if not scraping_task:
                return Response(
                    {"message": "Belum ada task scraping yang selesai"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            scraping_task_id: str = scraping_task.uid
            result = AsyncResult(scraping_task_id)

            task = matching_job_after_scraping.delay(jobs_data=result.result)

            db.begin()
            try:
                cypher = """
                MATCH (s:ScrapingTask {uid: $scraping_uid})
                CREATE (m:MatchingTask {
                    uid: $matching_uid,
                    status: $status,
                    startedAt: $started_at,
                    finishedAt: $finished_at
                })
                CREATE (s)-[:HAS_PROCESS]->(m)
                RETURN m
                """
                params = {
                    "scraping_uid": scraping_task.uid,
                    "matching_uid": task.id,
                    "status": "RUNNING",
                    "started_at": timezone.now(),
                    "finished_at": None,
                }
                db.cypher_query(cypher, params)
                db.commit()
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response(
                {"message": "Matching job sedang berjalan di background"},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JobMatchingCancelView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        scraping_task = (
            ScrapingTask.nodes.filter(status__in=["FINISHED"])
            .order_by("-startedAt")
            .first_or_none()
        )

        if not scraping_task:
            return Response(
                {
                    "message": "Proses scraping belum selesai, tidak bisa cancel matching."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            cypher = """
            MATCH (s:ScrapingTask {uid: $scraping_uid})-[:HAS_PROCESS]->(m:MatchingTask)
            WHERE m.status = 'RUNNING'
            RETURN m.uid AS matching_uid
            ORDER BY m.startedAt DESC
            LIMIT 1
            """
            params = {
                "scraping_uid": scraping_task.uid,
            }
            results, _ = db.cypher_query(cypher, params)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if not results or not results[0][0]:
            return Response(
                {
                    "message": "Tidak ada MatchingTask yang sedang berjalan untuk ScrapingTask ini."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        matching_uid = results[0][0]

        cache.set(f"matching_cancel_{matching_uid}", True, timeout=600)

        db.begin()
        try:
            cypher_update = """
            MATCH (m:MatchingTask {uid: $matching_uid})
            SET m.status = 'CANCELLED',
            RETURN m
            """
            params_update = {"matching_uid": matching_uid}
            db.cypher_query(cypher_update, params_update)
            db.commit()
        except Exception as e:
            db.rollback()
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(f"matching_progress_{matching_uid}")
        result = AsyncResult(matching_uid)
        result.forget()

        return Response(
            {"message": "Matching task berhasil dibatalkan"}, status=status.HTTP_200_OK
        )


class JobMatchingTaskStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request: Request) -> Response:
        scraping_task: ScrapingTask | None = (
            ScrapingTask.nodes.filter(status__in=["FINISHED"])
            .order_by("-startedAt")
            .first_or_none()
        )
        if not scraping_task:
            return Response(
                {"message": "Tidak ada task scraping yang selesai"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cypher = """
        MATCH (s:ScrapingTask {uid: $scraping_uid})-[:HAS_PROCESS]->(m:MatchingTask)
        WHERE m.status = 'RUNNING' or m.status = 'FINISHED'
        RETURN m.uid AS matching_uid
        ORDER BY m.startedAt DESC
        LIMIT 1
        """
        params = {
            "scraping_uid": scraping_task.uid,
        }
        results, _ = db.cypher_query(cypher, params)

        if not results or not results[0][0]:
            return Response(
                {
                    "message": "Tidak ada MatchingTask yang sedang berjalan untuk ScrapingTask ini."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        matching_uid = results[0][0]

        result = AsyncResult(matching_uid)
        task_status: str = result.status

        progress_data: dict[str, int | None] = cache.get(
            f"matching_progress_{matching_uid}", {}
        )

        if task_status == "SUCCESS":
            db.begin()
            try:
                cypher_update = """
                MATCH (m:MatchingTask {uid: $matching_uid})
                SET m.status = 'FINISHED',
                    m.finishedAt = $finished_at
                RETURN m
                """
                params_update = {
                    "matching_uid": matching_uid,
                    "finished_at": datetime.datetime.now().isoformat(),
                }
                db.cypher_query(cypher_update, params_update)
                db.commit()
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        elif task_status == "FAILURE":
            db.begin()
            try:
                cypher_update = """
                MATCH (m:MatchingTask {uid: $matching_uid})
                SET m.status = 'ERROR'
                RETURN m
                """
                params_update = {"matching_uid": matching_uid}
                db.cypher_query(cypher_update, params_update)
                db.commit()
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "task_id": matching_uid,
                "status": task_status,
            },
            status=status.HTTP_200_OK,
        )
