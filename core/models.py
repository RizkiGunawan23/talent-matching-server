from neomodel import StructuredNode, UniqueIdProperty, EmailProperty, DateTimeNeo4jFormatProperty, IntegerProperty, FloatProperty, StringProperty, RelationshipTo, ZeroOrMore, One


class User(StructuredNode):
    uid = UniqueIdProperty()
    email = EmailProperty(required=True, unique_index=True)
    password = StringProperty(required=True)
    name = StringProperty(required=True)
    role = StringProperty(default='user')
    created_at = DateTimeNeo4jFormatProperty(default_now=True)
    updated_at = DateTimeNeo4jFormatProperty(default_now=True)

    skills = RelationshipTo(
        'Skill', 'HAS_SKILLS', cardinality=ZeroOrMore
    )

    educations = RelationshipTo(
        'Education', 'HAS_EDUCATION', cardinality=ZeroOrMore
    )

    experiences = RelationshipTo(
        'Experience', 'HAS_EXPERIENCE', cardinality=ZeroOrMore
    )

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_staff(self) -> bool:
        return self.role == 'admin'


class Education(StructuredNode):
    uid = UniqueIdProperty()
    degree = StringProperty(required=True)
    institution = StringProperty(required=True)
    major = StringProperty(default="Informatika")
    start_year = IntegerProperty()
    end_year = IntegerProperty()
    created_at = DateTimeNeo4jFormatProperty(default_now=True)
    updated_at = DateTimeNeo4jFormatProperty(default_now=True)


class Experience(StructuredNode):
    uid = UniqueIdProperty()
    company = StringProperty(required=True)
    position = StringProperty(required=True)
    start_year = IntegerProperty()
    end_year = IntegerProperty()
    description = StringProperty()
    created_at = DateTimeNeo4jFormatProperty(default_now=True)
    updated_at = DateTimeNeo4jFormatProperty(default_now=True)


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
    skills = RelationshipTo(
        'Skill', 'REQUIRED_SKILLS', cardinality=ZeroOrMore
    )


class Skill(StructuredNode):
    name = StringProperty(required=True, unique_index=True)


# class ReportedJob(StructuredNode):
#     uid = UniqueIdProperty()
#     job = RelationshipTo(
#         'Job', 'REPORTED_JOB', cardinality=One
#     )
#     reason = StringProperty(required=True)

class ScrapingTask(StructuredNode):
    uid = StringProperty(required=True, unique_index=True)
    # RUNNING, FINISHED, FAILED, IMPORTED, DUMPED
    status = StringProperty(required=True)
    started_at = DateTimeNeo4jFormatProperty(default_now=True)
    finished_at = DateTimeNeo4jFormatProperty()
    message = StringProperty(required=True)
    triggered_by = RelationshipTo(
        'User', 'TRIGGERED_BY', cardinality=One
    )
