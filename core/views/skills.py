from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services import skill_service


class SkillsListView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request: Request) -> Response:
        """Get all skills for dropdown"""
        try:
            skills = skill_service.get_skills_for_dropdown()
            return Response(
                {
                    "skills": skills,
                    "total": len(skills)
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Error fetching skills: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )