from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


class JobRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "get JobRecommendationListView"}, status=status.HTTP_200_OK)
