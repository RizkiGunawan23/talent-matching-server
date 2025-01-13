from rest_framework.views import APIView
from rest_framework.response import Response
from core.db import get_db

class PersonAPI(APIView):
    def get(self, request):
        session = get_db()
        query = "MATCH (p:Person) RETURN p.name AS name"
        result = session.run(query)
        data = [record["name"] for record in result]
        return Response({"people": data})

    def post(self, request):
        session = get_db()
        name = request.data.get("name")
        query = "CREATE (p:Person {name: $name}) RETURN p"
        session.run(query, name=name)
        return Response({"message": f"Person {name} created successfully!"})
