from neomodel import db
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status


class TopSkillsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        query = """
        MATCH (:Job)-[:REQUIRED_SKILLS]->(s:Skill)
        RETURN s.name AS skill, COUNT(*) AS demand
        ORDER BY demand DESC
        LIMIT 10
        """
        results, _ = db.cypher_query(query)
        response_data = [{"skill": skill, "demand": demand}
                         for skill, demand in results]
        return Response({
            "message": "Berhasil mengambil data top skills",
            "data": response_data
        }, status=status.HTTP_200_OK)


class TopCombinationSkillsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        query = """
        MATCH (j:Job)-[:REQUIRED_SKILLS]->(s1:Skill)
        MATCH (j)-[:REQUIRED_SKILLS]->(s2:Skill)
        WHERE s1.name < s2.name
        RETURN s1.name AS skill1, s2.name AS skill2, COUNT(*) AS co_occurrence
        ORDER BY co_occurrence DESC
        LIMIT 10
        """
        results, _ = db.cypher_query(query)
        response_data = [{"skill1": s1, "skill2": s2, "co_occurrence": count}
                         for s1, s2, count in results]
        return Response({
            "message": "Berhasil mengambil data kombinasi skill terbanyak",
            "data": response_data
        }, status=status.HTTP_200_OK)


class VersatileSkillsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        query = """
        MATCH (j:Job)-[:REQUIRED_SKILLS]->(s:Skill)
        WITH s.name AS skill_name, COLLECT(DISTINCT j.job_title) AS roles
        RETURN skill_name, SIZE(roles) AS diversity
        ORDER BY diversity DESC
        LIMIT 10
        """
        results, _ = db.cypher_query(query)
        response_data = [{"skill": skill, "diversity": diversity}
                         for skill, diversity in results]
        return Response({
            "message": "Berhasil mengambil data skill paling serbaguna",
            "data": response_data
        }, status=status.HTTP_200_OK)


class RelatedSkillsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        # Kamu bisa ubah "Python" ke skill lain lewat query param jika mau
        base_skill = request.query_params.get("skill", "Python")

        query = """
        MATCH (s:Skill)<-[:REQUIRED_SKILLS]-(j:Job)-[:REQUIRED_SKILLS]->(other:Skill)
        WHERE s.name = $skill AND s <> other
        RETURN other.name AS related_skill, COUNT(*) AS frequency
        ORDER BY frequency DESC
        LIMIT 10
        """
        results, _ = db.cypher_query(query, {"skill": base_skill})
        response_data = [{"related_skill": skill, "frequency": freq}
                         for skill, freq in results]
        return Response({
            "message": f"Berhasil mengambil skill yang sering muncul bersama '{base_skill}'",
            "data": response_data
        }, status=status.HTTP_200_OK)


class ExclusiveSkillsInRolesView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        query = """
        MATCH (j:Job)-[:REQUIRED_SKILLS]->(s:Skill)
        WITH s.name AS skill, COLLECT(DISTINCT j.job_title) AS roles
        WHERE SIZE(roles) = 1
        RETURN skill, roles[0] AS exclusive_to_role
        ORDER BY skill
        LIMIT 20
        """
        results, _ = db.cypher_query(query)
        response_data = [{"skill": skill, "exclusive_to_role": role}
                         for skill, role in results]
        return Response({
            "message": "Berhasil mengambil skill eksklusif hanya muncul di satu role",
            "data": response_data
        }, status=status.HTTP_200_OK)


class SalaryStatsBySkillView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        skill_param = request.query_params.get('skill', '').strip()

        if not skill_param:
            return Response({"message": "Parameter 'skill' wajib diisi."},
                            status=status.HTTP_400_BAD_REQUEST)

        query = """
        MATCH (j:Job)-[:REQUIRED_SKILLS]->(s:Skill)
        WHERE toLower(s.name) = toLower($skill) AND j.maximum_salary <> 1000000000
        RETURN 
            min(j.minimum_salary) AS min_salary,
            avg((coalesce(j.minimum_salary, 0) + coalesce(j.maximum_salary, 0)) / 2) AS avg_salary,
            max(j.maximum_salary) AS max_salary
        """

        results, _ = db.cypher_query(query, {'skill': skill_param})

        if results:
            min_salary, avg_salary, max_salary = results[0]
            return Response({
                "message": f"Statistik salary untuk skill '{skill_param}'",
                "skill": skill_param,
                "min_salary": min_salary,
                "avg_salary": round(avg_salary, 2) if avg_salary else None,
                "max_salary": max_salary
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": f"Tidak ditemukan data untuk skill '{skill_param}'"
            }, status=status.HTTP_404_NOT_FOUND)
