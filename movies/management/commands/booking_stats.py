from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from movies.models import Movie, Show, Booking

class Command(BaseCommand):
    help = 'Display booking statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7)'
        )

    def handle(self, *args, **options):
        days = options['days']
        start_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(self.style.SUCCESS(f'Booking Statistics (Last {days} days)'))
        self.stdout.write('=' * 50)

        total_bookings = Booking.objects.filter(created_at__gte=start_date)
        active_bookings = total_bookings.filter(status='booked')
        cancelled_bookings = total_bookings.filter(status='cancelled')

        self.stdout.write(f'Total Bookings: {total_bookings.count()}')
        self.stdout.write(f'Active Bookings: {active_bookings.count()}')
        self.stdout.write(f'Cancelled Bookings: {cancelled_bookings.count()}')
        
        if total_bookings.count() > 0:
            cancellation_rate = (cancelled_bookings.count() / total_bookings.count()) * 100
            self.stdout.write(f'Cancellation Rate: {cancellation_rate:.1f}%')

        self.stdout.write('\nTop Movies:')
        top_movies = Movie.objects.annotate(
            booking_count=Count('shows__bookings', 
                              filter=models.Q(shows__bookings__created_at__gte=start_date))
        ).order_by('-booking_count')[:5]

        for movie in top_movies:
            self.stdout.write(f'  {movie.title}: {movie.booking_count} bookings')

        self.stdout.write('\nBusiest Screens:')
        from django.db import models
        busy_screens = Show.objects.filter(
            bookings__created_at__gte=start_date
        ).values('screen_name').annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')[:5]

        for screen in busy_screens:
            self.stdout.write(f'  {screen["screen_name"]}: {screen["booking_count"]} bookings')
