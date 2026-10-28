import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from .models import Order

logger = logging.getLogger(__name__)


@shared_task
def send_order_confirmation_email_task(order_id):
    """
    Асинхронна відправка email-підтвердження клієнту після оформлення замовлення.
    """
    try:
        order = Order.objects.get(id=order_id)
        subject = f"Order #{order.id} Confirmation - Bookstore"
        message = (
            f"Dear {order.first_name},\n\n"
            f"Thank you for your order #{order.id}.\n"
            f"Total cost: ${order.get_total_cost()}\n"
            f"Status: {order.status}\n\n"
            f"Best regards,\nBookstore Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@bookstore.com"),
            recipient_list=[order.email],
            fail_silently=False,
        )
        logger.info(f"Confirmation email sent for Order #{order.id}")
        return f"Email sent for order {order_id}"
    except Order.DoesNotExist:
        logger.error(f"Order #{order_id} does not exist.")
        return f"Order {order_id} not found"


@shared_task
def clear_expired_sessions_task():
    """
    Періодична задача для очищення застарілих сесій Django.
    """
    logger.info("Starting clearing expired sessions...")
    call_command("clearsessions")
    logger.info("Expired sessions cleared successfully.")
    return "Expired sessions cleared"


@shared_task
def generate_sales_report_task():
    """
    Періодична задача генерації звіту з продажів (наприклад, щотижня).
    """
    now = timezone.now()
    orders_count = Order.objects.count()
    total_revenue = sum(order.get_total_cost() for order in Order.objects.all())

    report_summary = (
        f"Sales Report generated at {now.isoformat()}: "
        f"Total Orders: {orders_count}, Total Revenue: ${total_revenue}"
    )
    logger.info(report_summary)
    return report_summary
