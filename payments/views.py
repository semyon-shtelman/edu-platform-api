from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Payment
from payments.serializers import PaymentCreateSerializer, PaymentSerializer
from payments.services import (
    create_stripe_price,
    create_stripe_product,
    create_stripe_session,
)


class PaymentListAPIView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["course", "lesson", "method"]
    search_fields = ["course__title", "lesson__title"]
    ordering_fields = ["date", "amount"]
    ordering = ["-date"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)


class CreatePaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course = serializer.validated_data.get("course_id")
        lesson = serializer.validated_data.get("lesson_id")

        item = course if course else lesson

        product = create_stripe_product(name=item.title)

        price = create_stripe_price(amount=item.price, product_id=product.id)

        session = create_stripe_session(price_id=price.id)

        payment = Payment.objects.create(
            user=request.user,
            course=course,
            lesson=lesson,
            amount=item.price,
            method=Payment.PAYMENT_TRANSFER,
            stripe_product_id=product.id,
            stripe_price_id=price.id,
            stripe_session_id=session.id,
            payment_url=session.url,
        )

        return Response(
            {"payment_id": payment.id, "payment_url": payment.payment_url},
            status=status.HTTP_201_CREATED,
        )
