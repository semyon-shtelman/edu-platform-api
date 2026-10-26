from django.conf import settings
from django.db import models
from rest_framework.exceptions import ValidationError

from education.models import Course, Lesson


class Payment(models.Model):
    PAYMENT_CASH = "cash"
    PAYMENT_TRANSFER = "transfer"

    PAYMENT_CHOICES = [(PAYMENT_CASH, "наличные"), (PAYMENT_TRANSFER, "перевод")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Оплаты",
    )
    date = models.DateTimeField(auto_now_add=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        related_name="payments",
        verbose_name="курс",
        null=True,
        blank=True,
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        related_name="payments",
        verbose_name="урок",
        null=True,
        blank=True,
    )
    amount = models.IntegerField()
    method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default=PAYMENT_TRANSFER,
        verbose_name="Способ оплаты",
    )

    stripe_product_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    payment_url = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.course if self.course else self.lesson} - {self.amount}"

    def clean(self):
        if self.course and self.lesson:
            raise ValidationError("Нельзя оплатить одновременно курс и урок")
        if not self.course and not self.lesson:
            raise ValidationError("Должен быть указан либо курс, либо урок")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Оплата"
        verbose_name_plural = "Оплаты"
