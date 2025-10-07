from django.core.management.base import BaseCommand
from django.utils import timezone
from movies.models import Booking

class Command(BaseCommand):
    help = 'Cleanup expired bookings and update their status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without making changes',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        
        expired_bookings = Booking.objects.filter(
            status='booked',
            show__date_time__lt=now
        )

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would update {expired_bookings.count()} expired bookings')
            )
            for booking in expired_bookings[:10]:
                self.stdout.write(f'  - Booking {booking.id}: {booking.show.movie.title}')
        else:
            count = expired_bookings.update(status='expired')
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {count} expired bookings')
            )
