from neomodel import (
    BooleanProperty,
    DateProperty,
    EmailProperty,
    FloatProperty,
    IntegerProperty,
    One,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    StructuredRel,
    UniqueIdProperty,
    ZeroOrMore,
    ZeroOrOne,
)


class HasReportedRel(StructuredRel):
    reportType = StringProperty(required=True)
    reportDescription = StringProperty(required=True)
    reportDate = DateProperty(required=True)
    reportStatus = StringProperty(required=True)


class User(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(required=True)
    email = EmailProperty(required=True, unique_index=True)
    password = StringProperty(required=True)
    profilePicture = StringProperty(default=None)
    role = StringProperty(default="user")
    has_skill = RelationshipTo(
        "Skill",
        "HAS_SKILL",
        cardinality=ZeroOrMore,
        model=StructuredRel,
    )
    has_reported = RelationshipTo(
        "Job",
        "HAS_REPORTED",
        cardinality=ZeroOrMore,
        model=HasReportedRel,
    )
    has_bookmarked = RelationshipTo(
        "Job",
        "HAS_BOOKMARKED",
        cardinality=ZeroOrMore,
        model=StructuredRel,
    )

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_staff(self) -> bool:
        return self.role == "admin"

    @staticmethod
    def all() -> list["User"]:
        """
        Fetch all users from the database.
        """
        return User.nodes.all()

    @staticmethod
    def get_by_uid(user_uid: str) -> "User | None":
        """
        Fetch a user by their unique identifier (UID).
        """
        return User.nodes.get_or_none(uid=user_uid)

    @staticmethod
    def get_by_email(email: str) -> "User | None":
        """
        Fetch a user by their email address.
        """
        return User.nodes.get_or_none(email=email)


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
    employmentType = StringProperty(required=True)
    workSetup = StringProperty(required=True)
    minimumEducation = StringProperty(required=True)
    minimumExperience = IntegerProperty(default=None)
    maximumExperience = IntegerProperty(default=None)
    jobDescription = StringProperty(required=True)
    scrapedAt = StringProperty(default=None)
    skills = RelationshipTo(
        "Skill",
        "REQUIRED_SKILL",
        cardinality=ZeroOrMore,
        model=StructuredRel,
    )
    additional_skills = RelationshipTo(
        "AdditionalSkill",
        "REQUIRED_SKILL",
        cardinality=ZeroOrMore,
        model=StructuredRel,
    )

    @staticmethod
    def all_with_skills() -> list[dict[str, "Job | list[Skill]"]]:
        """
        Fetch all jobs beserta list of Skill object (bukan string), hasil sudah digroup per job.
        """
        # Ambil semua job beserta skills-nya (fetch_relations menghasilkan satu row per relasi)
        raw = Job.nodes.fetch_relations("skills").all()
        jobs_dict = {}
        for row in raw:
            job = row[0]
            skill = row[1]
            key = job.jobUrl  # atau pakai UID jika ada
            if key not in jobs_dict:
                jobs_dict[key] = {
                    "job": job,
                    "skills": [],
                }
            if skill:
                # Hindari duplikasi skill jika ada
                if skill not in jobs_dict[key]["skills"]:
                    jobs_dict[key]["skills"].append(skill)
        return list(jobs_dict.values())


class UserJobMatch(StructuredNode):
    similarityScore = FloatProperty(required=True)
    # Strong, Mid, Weak
    matchType = StringProperty(required=True)
    user_match = RelationshipTo(
        "User", "USER_MATCH", cardinality=ZeroOrOne, model=StructuredRel
    )
    job_match = RelationshipTo(
        "Job", "JOB_MATCH", cardinality=ZeroOrOne, model=StructuredRel
    )


class Skill(StructuredNode):
    name = StringProperty(required=True, unique_index=True)


class AdditionalSkill(StructuredNode):
    name = StringProperty(required=True, unique_index=True)


class ScrapingTask(StructuredNode):
    uid = StringProperty(required=True, unique_index=True)
    # RUNNING, FINISHED, FAILED, IMPORTED, DUMPED
    status = StringProperty(required=True)
    startedAt = StringProperty(default=None)
    finishedAt = StringProperty(default=None)
    message = StringProperty(required=True)
    triggered_by = RelationshipTo(
        "User",
        "TRIGGERED_BY",
        cardinality=ZeroOrOne,
        model=StructuredRel,
    )
    has_process = RelationshipTo(
        "MatchingTask",
        "HAS_PROCESS",
        cardinality=ZeroOrOne,
        model=StructuredRel,
    )


class MatchingTask(StructuredNode):
    uid = StringProperty(required=True, unique_index=True)
    # RUNNING, FINISHED
    status = StringProperty(required=True)
    startedAt = StringProperty(default=None)
    finishedAt = StringProperty(default=None)


class Maintenance(StructuredNode):
    isMaintenance = BooleanProperty(required=True)

    @staticmethod
    def get_current_maintenance() -> "Maintenance | None":
        """
        Fetch the current maintenance status.
        """
        return Maintenance.nodes.first_or_none()

    @staticmethod
    def set_maintenance(is_maintenance: bool) -> None:
        """
        Set the maintenance status.
        """
        current_maintenance = Maintenance.get_current_maintenance()
        if not current_maintenance:
            current_maintenance = Maintenance(isMaintenance=is_maintenance)
            current_maintenance.save()
        else:
            current_maintenance.isMaintenance = is_maintenance
            current_maintenance.save()
