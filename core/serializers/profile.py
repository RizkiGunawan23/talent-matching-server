from rest_framework import serializers
# from ..models import Skill


class ProfileSerializer(serializers.Serializer):
    email = serializers.Serializer(read_only=True)
    name = serializers.CharField(required=True)
    # skills = serializers.ListField(child=serializers.CharField(), required=True)

    # def update(self, instance, validated_data):
    #     instance.name = validated_data.get('name', instance.name)
    #     if 'skills' in validated_data:
    #         for skill in instance.skills.all():
    #             instance.skills.disconnect(skill)
    #         for skill_name in validated_data['skills']:
    #             try:
    #                 skill_obj = Skill.nodes.get(name=skill_name)
    #             except Skill.DoesNotExist:
    #                 skill_obj = Skill(name=skill_name)
    #                 skill_obj.save()
    #             instance.skills.connect(skill_obj)
    #     instance.save()
    #     return instance


class EditProfileSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    name = serializers.CharField(required=False)
    skills = serializers.ListField(child=serializers.CharField(), required=False)
    profile_image = serializers.FileField(required=False)
    def validate_profile_image(self, value):
        if value:
            # Validasi manual tanpa PIL
            content_type = getattr(value, 'content_type', '')
            if not content_type.startswith('image/'):
                raise serializers.ValidationError("File harus berupa gambar")
        return value

class UserProfileSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField()
    skills = serializers.ListField(child=serializers.CharField())
    profile_image_url = serializers.CharField(allow_null=True, required=False)
