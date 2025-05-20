from rest_framework import serializers

from core.models import UploadedFile, User


class UploadedFileSerializer(serializers.Serializer):
    uid = serializers.CharField(read_only=True)
    filename = serializers.CharField(read_only=True)
    original_filename = serializers.CharField(read_only=True)
    file_path = serializers.CharField(read_only=True)
    content_type = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)
    file_type = serializers.CharField(read_only=True)
    description = serializers.CharField(required=False)
    created_at = serializers.DateTimeField(read_only=True)
