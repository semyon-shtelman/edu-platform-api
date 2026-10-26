from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from users.models import User


@shared_task
def send_course_update_email(course_title, emails):
    send_mail(
        subject="Обновление курса",
        message=f'Курс "{course_title}" был обновлён',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=emails,
        fail_silently=False,
    )


@shared_task
def deactivate_inactive_users(days_inactive=30):
    month_ago = timezone.now() - timedelta(days=days_inactive)

    # Пользователи, которые ни разу не входили, считаются по дате регистрации
    inactive_users = User.objects.filter(is_active=True).filter(
        Q(last_login__lt=month_ago)
        | Q(last_login__isnull=True, date_joined__lt=month_ago)
    )

    for user in inactive_users:
        send_mail(
            subject="Ваш аккаунт заблокирован за не активность",
            message=(
                f"Здравствуйте, {user.email}!\n\n"
                "Ваш аккаунт был заблокирован, так как вы не заходили более месяца.\n"
                "Для разблокировки обратитесь в поддержку."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        user.is_active = False
        user.save()
