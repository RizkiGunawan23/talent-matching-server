from core.models import Job
from rest_framework import serializers
from typing import Dict


class JobSerializer(serializers.ModelSerializer):
    job_url = serializers.URLField(
        required=True,
        error_messages={
            'required': 'URL pekerjaan harus diisi',
            'blank': 'URL pekerjaan harus diisi',
            'invalid': 'URL pekerjaan tidak valid',
        }
    )
    image_url = serializers.URLField(
        required=True,
        error_messages={
            'required': 'URL gambar harus diisi',
            'blank': 'URL gambar harus diisi',
            'invalid': 'URL gambar tidak valid',
        }
    )
    job_title = serializers.CharField(
        required=True,
        error_messages={
            'required': 'Judul pekerjaan harus diisi',
            'blank': 'Judul pekerjaan harus diisi',
        }
    )
    company_name = serializers.CharField(
        required=True,
        error_messages={
            'required': 'Nama perusahaan harus diisi',
            'blank': 'Nama perusahaan harus diisi',
        }
    )
    minimum_salary = serializers.IntegerField(
        required=True,
        min_value=0,
        allow_null=True,
        error_messages={
            'required': 'Gaji minimum harus diisi',
            'blank': 'Gaji minimum harus diisi',
            'invalid': 'Gaji minimum tidak valid',
        }
    )
    maximum_salary = serializers.IntegerField(
        required=True,
        min_value=0,
        allow_null=True,
        error_messages={
            'required': 'Gaji maksimum harus diisi',
            'blank': 'Gaji maksimum harus diisi',
            'invalid': 'Gaji maksimum tidak valid',
        }
    )
    salary_type = serializers.ChoiceField(
        required=True,
        allow_null=True,
        choices=[
            'Bonus', 'Base'
        ],
        error_messages={
            'required': 'Tipe gaji harus diisi',
            'blank': 'Tipe gaji harus diisi',
            'invalid_choice': "Tipe gaji harus berisi 'Bonus' atau 'Base'"
        }
    )
    salary_unit = serializers.ChoiceField(
        required=True,
        allow_null=True,
        choices=[
            'Month', 'Year', 'Project'
        ],
        error_messages={
            'required': 'Unit gaji harus diisi',
            'blank': 'Unit gaji harus diisi',
            'invalid_choice': "Tipe gaji harus berisi 'Month', 'Year' atau 'Project'"
        }
    )
    employment_type = serializers.ChoiceField(
        required=True,
        allow_null=True,
        choices=[
            "Freelance",
            "Harian",
            "Kontrak",
            "Magang",
            "Paruh Waktu",
            "Penuh Waktu",
        ],
        error_messages={
            'required': 'Tipe pekerjaan harus diisi',
            'blank': 'Tipe pekerjaan harus diisi',
            'invalid_choice': "Tipe pekerjaan harus berisi 'Freelance', 'Harian', 'Kontrak', 'Magang', 'Paruh Waktu' atau 'Penuh Waktu'"
        }
    )
    work_setup = serializers.ChoiceField(
        required=True,
        allow_null=True,
        choices=[
            "Hybrid",
            "Kerja di kantor",
            "Remote/Dari rumah",
        ],
        error_messages={
            'required': 'Jenis tempat bekerja harus diisi',
            'blank': 'Jenis tempat bekerja harus diisi',
            'invalid_choice': "Jenis tempat bekerja harus berisi 'Hybrid', 'Kerja di kantor' atau 'Remote/Dari rumah'"
        }
    )
    minimum_education = serializers.ChoiceField(
        required=True,
        allow_null=True,
        choices=[
            "Diploma (D1 - D4)",
            "SD",
            "SMA/SMK",
            "SMP",
            "Sarjana (S1)",
        ],
        error_messages={
            'required': 'Pendidikan minimum harus diisi',
            'blank': 'Pendidikan minimum harus diisi',
            'invalid_choice': "Pendidikan minimum harus berisi 'Diploma (D1 - D4)', 'SD', 'SMA/SMK', 'SMP' atau 'Sarjana (S1)'"
        }
    )
    minimum_experience = serializers.IntegerField(
        required=True,
        min_value=0,
        allow_null=True,
        error_messages={
            'required': 'Pengalaman minimum harus diisi',
            'blank': 'Pengalaman minimum harus diisi',
            'invalid': 'Pengalaman minimum tidak valid',
        }
    )
    maximum_experience = serializers.IntegerField(
        required=True,
        min_value=0,
        allow_null=True,
        error_messages={
            'required': 'Pengalaman maksimum harus diisi',
            'blank': 'Pengalaman maksimum harus diisi',
            'invalid': 'Pengalaman maksimum tidak valid',
        }
    )
    job_description = serializers.CharField(
        required=True,
        error_messages={
            'required': 'Deskripsi pekerjaan harus diisi',
            'blank': 'Deskripsi pekerjaan harus diisi',
        }
    )

    def validate(self, attrs: Dict[str, int | None]) -> Dict[str, int | None]:
        min_salary: int | None = attrs.get('minimum_salary')
        max_salary: int | None = attrs.get('maximum_salary')

        minimum_experience: int | None = attrs.get('minimum_experience')
        maximum_experience: int | None = attrs.get('maximum_experience')

        errors = {}

        if minimum_experience is not None and maximum_experience is not None:
            if maximum_experience <= minimum_experience:
                errors['maximum_experience'] = 'Pengalaman maksimum harus lebih besar dari pengalaman minimum'

        if min_salary is not None and max_salary is not None:
            if max_salary <= min_salary:
                errors['maximum_salary'] = 'Gaji maksimum harus lebih besar dari gaji minimum'

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data: Dict[str, int | None]) -> Job:
        job = Job(
            job_url=validated_data['job_url'],
            image_url=validated_data['image_url'],
            job_title=validated_data['job_title'],
            company_name=validated_data['company_name'],
            minimum_salary=validated_data['minimum_salary'],
            maximum_salary=validated_data['maximum_salary'],
            salary_unit=validated_data['salary_unit'],
            salary_type=validated_data['salary_type'],
            employment_type=validated_data['employment_type'],
            work_setup=validated_data['work_setup'],
            minimum_education=validated_data['minimum_education'],
            minimum_experience=validated_data['minimum_experience'],
            maximum_experience=validated_data['maximum_experience'],
            description=validated_data['job_description']
        )
        job.save()

        return job
