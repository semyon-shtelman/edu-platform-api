from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class UserRegisterTestCase(APITestCase):

    def setUp(self):
        self.data = {
            "email": "new@test.com",
            "password": "Strong-pass-123",
            "password2": "Strong-pass-123",
        }

    def test_register_user(self):
        response = self.client.post("/users/register/", data=self.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)

        user = User.objects.get(email="new@test.com")
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password("Strong-pass-123"))

    def test_register_and_obtain_token(self):
        self.client.post("/users/register/", data=self.data)

        response = self.client.post(
            "/users/token/",
            data={"email": "new@test.com", "password": "Strong-pass-123"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_register_passwords_mismatch(self):
        self.data["password2"] = "Other-pass-123"

        response = self.client.post("/users/register/", data=self.data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="new@test.com").exists())

    def test_register_weak_password(self):
        self.data["password"] = self.data["password2"] = "123"

        response = self.client.post("/users/register/", data=self.data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        User.objects.create_user(email="new@test.com", password="Strong-pass-123")

        response = self.client.post("/users/register/", data=self.data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_wrong_password(self):
        User.objects.create_user(email="new@test.com", password="Strong-pass-123")

        response = self.client.post(
            "/users/token/", data={"email": "new@test.com", "password": "wrong"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
