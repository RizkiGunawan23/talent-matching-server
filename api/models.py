from neomodel import (
    DateTimeProperty,
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
    originalFilename = StringProperty(required=True)
    filePath = StringProperty(required=True)
    contentType = StringProperty(default="image/png")
    fileSize = FloatProperty(default=0.0, help_text="File size in bytes")
    fileType = StringProperty(default="image")
    createdAt = DateTimeProperty(default_now=True)
    uploaded_by = RelationshipTo("User", "UPLOADED_BY", cardinality=ZeroOrOne)


class User(StructuredNode):
    uid = UniqueIdProperty()
    email = EmailProperty(required=True, unique_index=True)
    password = StringProperty(required=True)
    name = StringProperty(required=True)
    role = StringProperty(default="user")
    profilePicture = StringProperty()

    profile_picture = RelationshipTo(
        "UploadedFile", "HAS_PROFILE_PICTURE", cardinality=ZeroOrOne
    )
    skills = RelationshipTo("Skill", "HAS_SKILLS", cardinality=ZeroOrMore)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_staff(self) -> bool:
        return self.role == "admin"


class Job(StructuredNode):
    jobUrl = StringProperty(required=True, unique_index=True)
    imageUrl = StringProperty(required=True)
    jobTitle = StringProperty(required=True)
    companyName = StringProperty(required=True)
    subdistrict = StringProperty(required=True)
    city = StringProperty(required=True)
    province = StringProperty(required=True)
    minimumSalary = IntegerProperty(default=None)
    maximumSalary = IntegerProperty(default=None)
    salaryUnit = StringProperty(default=None)
    salaryType = StringProperty(default=None)
    employmentType = StringProperty(required=True)
    workSetup = StringProperty(required=True)
    minimumEducation = StringProperty(required=True)
    minimumExperience = IntegerProperty(default=None)
    maximumExperience = IntegerProperty(default=None)
    jobDescription = StringProperty(required=True)
    scrapedAt = DateTimeProperty(default_now=True)
    skills = RelationshipTo("Skill", "REQUIRED_SKILLS", cardinality=ZeroOrMore)
    additionalSkills = RelationshipTo(
        "Skill", "REQUIRED_SKILLS", cardinality=ZeroOrMore
    )


class Skill(StructuredNode):
    name = StringProperty(required=True, unique_index=True)


class AdditionalSkill(StructuredNode):
    name = StringProperty(required=True, unique_index=True)


class ReportedJob(StructuredNode):
    uid = UniqueIdProperty()
    job = RelationshipTo("Job", "REPORTED_JOB", cardinality=One)
    reason = StringProperty(required=True)


class ScrapingTask(StructuredNode):
    uid = StringProperty(required=True, unique_index=True)
    # RUNNING, FINISHED, FAILED, IMPORTED, DUMPED
    status = StringProperty(required=True)
    startedAt = DateTimeProperty(default_now=True)
    finishedAt = DateTimeProperty()
    message = StringProperty(required=True)
    triggered_by = RelationshipTo("User", "TRIGGERED_BY", cardinality=One)
