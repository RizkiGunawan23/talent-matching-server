import random

from django.contrib.auth.hashers import check_password, make_password
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import User


class SeederView(APIView):
    def post(self, request):
        """
        Seed the database with 100 dummy users (1 main admin + 99 mixed users)
        Use POST request to trigger the seeding
        """
        try:
            # Option to delete existing users first via query param
            if request.query_params.get("clear_existing") == "true":
                deleted_count = len(User.nodes.all())
                User.nodes.all().delete()
                return Response(
                    {
                        "message": f"Deleted {deleted_count} existing users. Send another request without clear_existing to seed new users."
                    },
                    status=status.HTTP_200_OK,
                )

            # Get count of existing users
            existing_users = len(User.nodes.all())

            # List of common first names and last names for realistic data
            first_names = [
                "John",
                "Jane",
                "Michael",
                "Sara",
                "David",
                "Lisa",
                "Robert",
                "Emily",
                "William",
                "Olivia",
                "James",
                "Sophia",
                "Daniel",
                "Emma",
                "Matthew",
                "Ava",
                "Joseph",
                "Mia",
                "Thomas",
                "Isabella",
                "Anthony",
                "Aditya",
                "Rizki",
                "Dewi",
                "Budi",
                "Siti",
                "Ahmad",
                "Putri",
                "Agus",
                "Rina",
            ]

            last_names = [
                "Smith",
                "Johnson",
                "Williams",
                "Jones",
                "Brown",
                "Davis",
                "Miller",
                "Wilson",
                "Taylor",
                "Clark",
                "White",
                "Lewis",
                "Harris",
                "Robinson",
                "Walker",
                "Young",
                "Allen",
                "Wright",
                "King",
                "Scott",
                "Green",
                "Baker",
                "Wijaya",
                "Susanto",
                "Hidayat",
                "Gunawan",
                "Kusuma",
                "Santoso",
                "Wibowo",
                "Saputra",
            ]

            domains = [
                "gmail.com",
                "yahoo.com",
                "outlook.com",
                "hotmail.com",
                "mail.com",
                "example.com",
            ]

            companies = [
                "acme",
                "globex",
                "initech",
                "techcorp",
                "innovate",
                "futuretech",
                "webdev",
            ]

            # Create admin user manually to ensure we have one
            admin = User.nodes.get_or_none(email="admin@example.com")
            if not admin:
                admin = User(
                    email="admin@example.com",
                    password=make_password(
                        "Admin123!"
                    ),  # In production, use proper password hashing
                    name="Admin User",
                    role="admin",
                ).save()

            # Create your personal admin account if requested
            personal_admin = User.nodes.get_or_none(email="rizki@gmail.com")
            if not personal_admin:
                personal_admin = User(
                    email="rizki@gmail.com",
                    password=make_password(
                        "sS!45678"
                    ),  # In production, use proper password hashing
                    name="Rizki",
                    role="admin",
                ).save()

            # Count how many users to create (to reach total of 100)
            users_to_create = 100 - len(User.nodes.all())

            if users_to_create <= 0:
                return Response(
                    {
                        "message": f"Database already has {len(User.nodes.all())} users. No new users created.",
                        "hint": "Use ?clear_existing=true to clear existing users first.",
                    },
                    status=status.HTTP_200_OK,
                )

            # Create remaining users (mix of admin and regular users)
            created_count = 0
            attempts = 0  # To prevent infinite loops
            admin_count = 0
            user_count = 0

            while created_count < users_to_create and attempts < 200:
                attempts += 1

                # Decide if this should be an admin (10% chance)
                is_admin = random.random() < 0.1
                role = "admin" if is_admin else "user"

                # Generate random user data
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                name = f"{first_name} {last_name}"

                # Create email with various formats
                email_type = random.randint(1, 4)
                if email_type == 1:
                    email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"
                elif email_type == 2:
                    email = f"{first_name.lower()}{random.randint(1, 999)}@{random.choice(domains)}"
                elif email_type == 3:
                    email = f"{last_name.lower()}.{first_name.lower()}@{random.choice(domains)}"
                else:
                    company = random.choice(companies)
                    email = f"{first_name.lower()[0]}{last_name.lower()}@{company}.com"

                # Check if email already exists
                if User.nodes.get_or_none(email=email):
                    continue

                # Generate password (simple but meets requirements)
                password = f"{first_name.capitalize()}123!"

                # Create user
                user = User(
                    email=email,
                    password=make_password(
                        password
                    ),  # In production, use proper password hashing
                    name=name,
                    role=role,
                ).save()

                created_count += 1
                if role == "admin":
                    admin_count += 1
                else:
                    user_count += 1

            return Response(
                {
                    "message": f"Successfully created {created_count} users",
                    "details": {
                        "existing_users": existing_users,
                        "new_users_created": created_count,
                        "new_admins_created": admin_count,
                        "new_regular_users_created": user_count,
                        "total_users_now": len(User.nodes.all()),
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": "Failed to seed users", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request):
        """Return count of existing users without creating any"""
        try:
            user_count = len(User.nodes.all())
            admin_count = len(User.nodes.filter(role="admin"))
            regular_count = user_count - admin_count

            return Response(
                {
                    "total_users": user_count,
                    "admins": admin_count,
                    "regular_users": regular_count,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": "Failed to get user count", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
