from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import models
from datetime import timedelta
import logging
import uuid

logger = logging.getLogger(__name__)

def generate_booking_reference():
    return f"BK{str(uuid.uuid4())[:8].upper()}"

def send_booking_confirmation_email(booking):
    subject = f'Booking Confirmation - {booking.show.movie.title}'
    message = f"""
    Dear {booking.user.first_name or booking.user.username},

    Your booking has been confirmed!

    Booking Details:
    - Booking Reference: {booking.booking_reference}
    - Movie: {booking.show.movie.title}
    - Screen: {booking.show.screen_name}
    - Date & Time: {booking.show.date_time.strftime('%B %d, %Y at %I:%M %p')}
    - Seat Number: {booking.seat_number}

    Please arrive 30 minutes before the show time.

    Thank you for choosing our cinema!
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.user.email],
            fail_silently=False,
        )
        logger.info(f'Booking confirmation email sent for booking {booking.id}')
        return True
    except Exception as e:
        logger.error(f'Failed to send booking confirmation email: {e}')
        return False

def send_booking_cancellation_email(booking):
    subject = f'Booking Cancellation - {booking.show.movie.title}'
    message = f"""
    Dear {booking.user.first_name or booking.user.username},

    Your booking has been successfully cancelled.

    Cancelled Booking Details:
    - Booking Reference: {booking.booking_reference}
    - Movie: {booking.show.movie.title}
    - Screen: {booking.show.screen_name}
    - Date & Time: {booking.show.date_time.strftime('%B %d, %Y at %I:%M %p')}
    - Seat Number: {booking.seat_number}

    Refund will be processed within 3-5 business days.

    Thank you!
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.user.email],
            fail_silently=False,
        )
        logger.info(f'Booking cancellation email sent for booking {booking.id}')
        return True
    except Exception as e:
        logger.error(f'Failed to send booking cancellation email: {e}')
        return False

def calculate_show_occupancy(show):
    total_seats = show.total_seats
    booked_seats = show.bookings.filter(status='booked').count()
    return (booked_seats / total_seats) * 100 if total_seats > 0 else 0

def get_available_seats_list(show):
    booked_seats = set(show.bookings.filter(status='booked').values_list('seat_number', flat=True))
    return [seat for seat in range(1, show.total_seats + 1) if seat not in booked_seats]

def is_booking_allowed(user, show, seat_number):
    now = timezone.now()
    
    if show.date_time <= now:
        return False, "Cannot book seats for past shows"
    
    booking_deadline = show.date_time - timedelta(minutes=30)
    if now > booking_deadline:
        return False, "Booking closed 30 minutes before show time"
    
    if show.bookings.filter(seat_number=seat_number, status='booked').exists():
        return False, "Seat already booked"
    
    user_bookings = show.bookings.filter(user=user, status='booked').count()
    if user_bookings >= 5:
        return False, "Maximum 5 seats allowed per user"
    
    return True, "Booking allowed"

def is_cancellation_allowed(booking):
    if booking.status != 'booked':
        return False, "Only active bookings can be cancelled"
    
    cancellation_deadline = booking.show.date_time - timedelta(hours=2)
    if timezone.now() > cancellation_deadline:
        return False, "Cannot cancel booking less than 2 hours before show"
    
    return True, "Cancellation allowed"

def get_booking_statistics(days=30):
    from django.db.models import Count, Avg
    from .models import Booking, Movie, Show
    
    start_date = timezone.now() - timedelta(days=days)
    
    stats = {
        'total_bookings': Booking.objects.filter(created_at__gte=start_date).count(),
        'active_bookings': Booking.objects.filter(
            created_at__gte=start_date, 
            status='booked'
        ).count(),
        'cancelled_bookings': Booking.objects.filter(
            created_at__gte=start_date, 
            status='cancelled'
        ).count(),
        'popular_movies': Movie.objects.annotate(
            booking_count=Count('shows__bookings', 
                              filter=models.Q(shows__bookings__created_at__gte=start_date))
        ).order_by('-booking_count')[:5],
        'average_occupancy': Show.objects.filter(
            date_time__gte=start_date,
            date_time__lt=timezone.now()
        ).annotate(
            occupancy=Count('bookings', filter=models.Q(bookings__status='booked')) * 100.0 / models.F('total_seats')
        ).aggregate(avg_occupancy=Avg('occupancy'))['avg_occupancy'] or 0
    }
    
    return stats

def cleanup_expired_bookings():
    from .models import Booking
    
    expired_bookings = Booking.objects.filter(
        status='booked',
        show__date_time__lt=timezone.now()
    )
    
    count = expired_bookings.update(status='expired')
    logger.info(f'Cleaned up {count} expired bookings')
    return count
