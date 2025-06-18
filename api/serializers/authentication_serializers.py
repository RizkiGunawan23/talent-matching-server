from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "Email harus diisi",
            "blank": "Email harus diisi",
            "invalid": "Format email tidak valid",
        },
    )
    password = serializers.CharField(
        min_length=8,
        required=True,
        write_only=True,
        error_messages={
            "required": "Password harus diisi",
            "blank": "Password harus diisi",
            "min_length": "Password minimal 8 karakter",
            "min_length": "Password minimal 8 karakter",
        },
    )
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": "Nama harus diisi",
            "blank": "Nama harus diisi",
        },
    )
    role = serializers.ChoiceField(
        choices=["user", "admin"],
        default="user",
        error_messages={"invalid_choice": "Role harus berisi 'user' atau 'admin'"},
    )

    profile_picture = serializers.FileField(
        required=False,
        allow_empty_file=False,
        error_messages={
            "invalid": "File tidak valid",
        },
    )

    # Skills field - list of skill names
    skills = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        error_messages={
            "invalid": "Skills harus berupa list",
        },
    )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "Email harus diisi",
            "blank": "Email harus diisi",
            "invalid": "Format email tidak valid",
        },
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            "required": "Password harus diisi",
            "blank": "Password harus diisi",
        },
    )
