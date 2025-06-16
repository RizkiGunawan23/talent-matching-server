from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class AdminJobView(ViewSet):
    def list(self, request):
        return Response({"message": f"AdminJobsView base"})
