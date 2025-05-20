from neomodel import (
    DateTimeFormatProperty,
    EmailProperty,
    FloatProperty,
    IntegerProperty,
    One,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    UniqueIdProperty,
    ZeroOrMore,
    ZeroOrOne,
)


class UploadedFile(StructuredNode):
    uid = UniqueIdProperty()
    filename = StringProperty(required=True)
    original_filename = StringProperty(required=True)
    file_path = StringProperty(required=True)
    content_type = StringProperty(default="image/png")
    file_size = FloatProperty(default=0.0, help_text="File size in bytes")
    file_type = StringProperty(default="image")
    created_at = DateTimeFormatProperty(default_now=True)
    uploaded_by = RelationshipTo("User", "UPLOADED_BY", cardinality=ZeroOrOne)


class User(StructuredNode):
    uid = UniqueIdProperty()
    email = EmailProperty(required=True, unique_index=True)
    password = StringProperty(required=True)
    name = StringProperty(required=True)
    role = StringProperty(default="user")
    created_at = DateTimeFormatProperty(default_now=True)
    updated_at = DateTimeFormatProperty(default_now=True)

    skills = RelationshipTo("Skill", "HAS_SKILLS", cardinality=ZeroOrMore)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_staff(self) -> bool:
        return self.role == "admin"


class Job(StructuredNode):
    uid = UniqueIdProperty()
    job_url = StringProperty(required=True, unique_index=True)
    image_url = StringProperty(required=True)
    job_title = StringProperty(required=True)
    company_name = StringProperty(required=True)
    subdistrict = StringProperty(required=True)
    city = StringProperty(required=True)
    province = StringProperty(required=True)
    minimum_salary = IntegerProperty(default=None)
    maximum_salary = IntegerProperty(default=None)
    salary_unit = StringProperty(default=None)
    salary_type = StringProperty(default=None)
    employment_type = StringProperty(required=True)
    work_setup = StringProperty(required=True)
    minimum_education = StringProperty(required=True)
    minimum_experience = IntegerProperty(default=None)
    maximum_experience = IntegerProperty(default=None)
    job_description = StringProperty(required=True)
    skills = RelationshipTo("Skill", "REQUIRED_SKILLS", cardinality=ZeroOrMore)


class Skill(StructuredNode):
    name = StringProperty(required=True, unique_index=True)


class ReportedJob(StructuredNode):
    uid = UniqueIdProperty()
    job = RelationshipTo("Job", "REPORTED_JOB", cardinality=One)
    reason = StringProperty(required=True)


class ScrapingTask(StructuredNode):
    uid = StringProperty(required=True, unique_index=True)
    # RUNNING, FINISHED, FAILED, IMPORTED, DUMPED
    status = StringProperty(required=True)
    started_at = DateTimeFormatProperty(default_now=True)
    finished_at = DateTimeFormatProperty()
    message = StringProperty(required=True)
    triggered_by = RelationshipTo("User", "TRIGGERED_BY", cardinality=One)
