from datetime import timedelta

from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from education.models import Course, Lesson, Subscription
from education.tasks import deactivate_inactive_users
from users.models import User


class LessonTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="user@gmail.com")

        self.user.set_password("123")
        self.user.save()

        self.moderator = User.objects.create_user(
            "moder@gmail.com",
        )
        moderators = Group.objects.create(name="moderators")
        self.moderator.groups.add(moderators)

        self.moderator.set_password("123")
        self.moderator.save()

        self.course = Course.objects.create(
            title="Python",
        )

        self.lesson = Lesson.objects.create(
            title="Lesson 1", content="Content", course=self.course, owner=self.user
        )
        self.client.force_authenticate(user=self.user)

    def test_create_lesson(self):
        data = {
            "title": "New lesson",
            "content": "New content",
            "course": self.course.id,
        }

        response = self.client.post("/education/lesson/create/", data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_moderator_cannot_create_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        data = {"title": "New lesson", "content": "Content", "course": self.course.id}
        response = self.client.post("/education/lesson/create/", data=data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_lessons(self):
        response = self.client.get("/education/lesson/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_lesson(self):
        response = self.client.get(f"/education/lesson/{self.lesson.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_lesson(self):

        data = {"title": "Updated lesson"}
        response = self.client.patch(
            f"/education/lesson/update/{self.lesson.id}/", data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.lesson.refresh_from_db()

        self.assertEqual(self.lesson.title, "Updated lesson")

    def test_delete_lesson(self):
        response = self.client.delete(f"/education/lesson/delete/{self.lesson.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_moderator_cannot_delete_lesson(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.delete(f"/education/lesson/delete/{self.lesson.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SubscriptionTestCace(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com")
        self.course = Course.objects.create(title="Python")
        self.client.force_authenticate(user=self.user)

    def test_create_subscription(self):
        response = self.client.post(f"/education/course/{self.course.id}/subscribe/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_subscription(self):
        Subscription.objects.create(user=self.user, course=self.course)
        response = self.client.post(f"/education/course/{self.course.id}/subscribe/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class DeactivateInactiveUsersTestCase(TestCase):

    def setUp(self):
        old = timezone.now() - timedelta(days=40)

        self.active = User.objects.create_user(
            email="active@test.com", last_login=timezone.now()
        )
        self.inactive = User.objects.create_user(
            email="inactive@test.com", last_login=old
        )
        self.never_logged_in = User.objects.create_user(email="never@test.com")
        User.objects.filter(pk=self.never_logged_in.pk).update(date_joined=old)
        self.new_user = User.objects.create_user(email="new@test.com")

    def test_deactivate_inactive_users(self):
        deactivate_inactive_users()

        for user in (self.active, self.inactive, self.never_logged_in, self.new_user):
            user.refresh_from_db()

        self.assertTrue(self.active.is_active)
        self.assertFalse(self.inactive.is_active)
        self.assertFalse(self.never_logged_in.is_active)
        self.assertTrue(self.new_user.is_active)

        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ["inactive@test.com", "never@test.com"])
