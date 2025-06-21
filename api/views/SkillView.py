from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.permissions import AllowAny

from api.models import Skill

class SkillView(ViewSet):
    """
    ViewSet for working with Skill nodes from Neo4j database.
    """
    permission_classes = [AllowAny]
    def list(self, request):
        """Get all skill nodes that have a non-null name"""
        try:
            # Query skills that have a non-null name property
            skills = Skill.nodes.filter(name__isnull=False).order_by('name')
            
            # Format the results as a list of dictionaries
            skills_data = [{"name": skill.name} for skill in skills]
            
            return Response({
                "message": "Skills retrieved successfully",
                "data": {
                    "skills": skills_data,
                    "total": len(skills_data)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                "message": f"Error retrieving skills: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)