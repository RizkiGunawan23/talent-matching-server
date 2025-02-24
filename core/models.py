from neomodel import StructuredNode, UniqueIdProperty, EmailProperty, StringProperty, RelationshipTo, ZeroOrMore


class User(StructuredNode):
    uid = UniqueIdProperty()
    email = EmailProperty(required=True, unique_index=True)
    password = StringProperty(required=True)
    name = StringProperty(required=True)
    role = StringProperty(default='user')
    # skills = RelationshipTo('Skill', 'HAS_SKILL', cardinality=ZeroOrMore)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_staff(self):
        return self.role == 'admin'


# class Skill(StructuredNode):
#     uid = UniqueIdProperty()
#     name = StringProperty(required=True, unique_index=True)


class Job(StructuredNode):
    uid = UniqueIdProperty()
    title = StringProperty(required=True)
    # description = StringProperty()
    # required_skills = RelationshipTo(
    #     'Skill', 'REQUIRED_SKILL', cardinality=ZeroOrMore)
