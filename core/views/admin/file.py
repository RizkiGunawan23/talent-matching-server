import os

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import UploadedFile
from core.serializers import UploadedFileSerializer

# Base directory for file storage
FILE_STORAGE_DIR = os.path.join(settings.BASE_DIR, "uploaded_files/ontology")
os.makedirs(FILE_STORAGE_DIR, exist_ok=True)


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        description = request.data.get("description", "")

        if not uploaded_file:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file type (e.g., only allow PDF, DOCX, etc.)
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        if uploaded_file.content_type not in allowed_types:
            return Response(
                {"error": "File type not allowed"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (e.g., max 10MB)
        if uploaded_file.size > 10 * 1024 * 1024:  # 10MB in bytes
            return Response(
                {"error": "File too large"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create a unique filename to avoid overwriting
        import uuid

        filename = f"{uuid.uuid4()}_{uploaded_file.name}"

        # Save the file to the filesystem
        file_path = os.path.join(FILE_STORAGE_DIR, filename)
        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Create file record in Neo4j
        file_record = UploadedFile(
            filename=filename,
            file_path=file_path,
            content_type=uploaded_file.content_type,
            file_size=str(uploaded_file.size),
            description=description,
        ).save()

        # Connect to the user who uploaded
        file_record.uploaded_by.connect(request.user)

        return Response(
            {
                "message": "File uploaded successfully",
                "file_id": file_record.uid,
                "filename": filename,
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        # List all files
        files = UploadedFile.nodes.all()
        serializer = UploadedFileSerializer(files, many=True)
        return Response(serializer.data)


class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        # Retrieve file
        file_record = UploadedFile.nodes.get_or_none(uid=file_id)
        if not file_record:
            return Response(
                {"error": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if file exists in filesystem
        if not os.path.exists(file_record.file_path):
            file_record.delete()
            return Response(
                {"error": "File not found on server"}, status=status.HTTP_404_NOT_FOUND
            )

        # Return file content
        return FileResponse(
            open(file_record.file_path, "rb"),
            as_attachment=True,
            filename=file_record.filename,
        )

    def delete(self, request, file_id):
        # Delete file
        file_record = UploadedFile.nodes.get_or_none(uid=file_id)
        if not file_record:
            return Response(
                {"error": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Delete from filesystem if exists
        if os.path.exists(file_record.file_path):
            os.remove(file_record.file_path)

        # Delete from database
        file_record.delete()

        return Response(
            {"message": "File deleted successfully"}, status=status.HTTP_200_OK
        )
