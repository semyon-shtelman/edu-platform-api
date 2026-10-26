from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.test import APITestCase

from education.models import Course, Lesson
from payments.models import Payment
from payments.services import create_stripe_price
from users.models import User


class PaymentListTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com")
        self.other = User.objects.create_user(email="other@test.com")
        self.admin = User.objects.create_user(email="admin@test.com", is_staff=True)

        self.course = Course.objects.create(title="Python", price=1000)

        self.own_payment = Payment.objects.create(
            user=self.user, course=self.course, amount=1000
        )
        self.other_payment = Payment.objects.create(
            user=self.other, course=self.course, amount=1000
        )

    def test_anonymous_cannot_list_payments(self):
        response = self.client.get("/payments/list/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_own_payments(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/payments/list/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [payment["id"] for payment in response.data]
        self.assertEqual(ids, [self.own_payment.id])

    def test_admin_sees_all_payments(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/payments/list/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class PaymentCreateTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com")
        self.course = Course.objects.create(title="Python", price=1000)
        self.lesson = Lesson.objects.create(
            title="Lesson 1", content="Content", course=self.course, price=200
        )
        self.client.force_authenticate(user=self.user)

    @patch("payments.views.create_stripe_session")
    @patch("payments.views.create_stripe_price")
    @patch("payments.views.create_stripe_product")
    def test_create_course_payment(self, mock_product, mock_price, mock_session):
        mock_product.return_value = MagicMock(id="prod_1")
        mock_price.return_value = MagicMock(id="price_1")
        mock_session.return_value = MagicMock(
            id="cs_1", url="https://checkout.stripe.com/pay/cs_1"
        )

        response = self.client.post(
            "/payments/create/", data={"course_id": self.course.id}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["payment_url"], "https://checkout.stripe.com/pay/cs_1"
        )

        mock_product.assert_called_once_with(name="Python")
        mock_price.assert_called_once_with(amount=1000, product_id="prod_1")
        mock_session.assert_called_once_with(price_id="price_1")

        payment = Payment.objects.get(id=response.data["payment_id"])
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.course, self.course)
        self.assertEqual(payment.amount, 1000)
        self.assertEqual(payment.stripe_session_id, "cs_1")

    @patch("payments.views.create_stripe_session")
    @patch("payments.views.create_stripe_price")
    @patch("payments.views.create_stripe_product")
    def test_create_lesson_payment(self, mock_product, mock_price, mock_session):
        mock_product.return_value = MagicMock(id="prod_1")
        mock_price.return_value = MagicMock(id="price_1")
        mock_session.return_value = MagicMock(id="cs_1", url="https://stripe/cs_1")

        response = self.client.post(
            "/payments/create/", data={"lesson_id": self.lesson.id}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment = Payment.objects.get(id=response.data["payment_id"])
        self.assertEqual(payment.lesson, self.lesson)
        self.assertEqual(payment.amount, 200)

    @patch("payments.views.create_stripe_product")
    def test_course_and_lesson_together(self, mock_product):
        response = self.client.post(
            "/payments/create/",
            data={"course_id": self.course.id, "lesson_id": self.lesson.id},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_product.assert_not_called()

    @patch("payments.views.create_stripe_product")
    def test_nothing_to_pay(self, mock_product):
        response = self.client.post("/payments/create/", data={})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_product.assert_not_called()

    def test_anonymous_cannot_create_payment(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/payments/create/", data={"course_id": self.course.id}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class StripeServicesTestCase(APITestCase):

    @patch("payments.services.stripe.Price.create")
    def test_price_in_rubles_kopecks(self, mock_create):
        create_stripe_price(product_id="prod_1", amount=1000)

        mock_create.assert_called_once_with(
            currency="rub", unit_amount=100000, product="prod_1"
        )
