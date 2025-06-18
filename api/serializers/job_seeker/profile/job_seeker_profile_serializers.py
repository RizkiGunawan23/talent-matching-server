from rest_framework import serializers


class EditProfileSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": "Nama harus diisi",
            "blank": "Nama harus diisi",
        },
    )
    skills = serializers.ListField(
        child=serializers.CharField(
            required=True,
            error_messages={
                "required": "Nama skill harus diisi",
                "blank": "Nama skill harus diisi",
                "invalid": "Format skill tidak valid",
            },
        ),
        required=True,
        error_messages={
            "required": "Kumpulan skill harus diisi",
            "blank": "Kumpulan skill harus diisi",
            "invalid": "Format skills tidak valid",
        },
    )
    profile_image = serializers.FileField(required=False)

    def validate_profile_image(self, value):
        if value:
            content_type = getattr(value, "content_type", "")
            if not content_type.startswith("image/"):
                raise serializers.ValidationError("File harus berupa gambar")
        return value
