from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import timedelta

def validate_future_datetime(value):
    if value <= timezone.now():
        raise ValidationError('Show date and time must be in the future.')

class Movie(models.Model):
    title = models.CharField(max_length=200)
    duration_minutes = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1, "Duration must be at least 1 minute"),
            MaxValueValidator(600, "Duration cannot exceed 10 hours")
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    rating = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['title']

    def __str__(self):
        return self.title
    
    def clean(self):
        super().clean()
        if self.title and len(self.title.strip()) == 0:
            raise ValidationError({'title': 'Title cannot be empty or just whitespace'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='shows')
    screen_name = models.CharField(max_length=100)
    date_time = models.DateTimeField(validators=[validate_future_datetime])
    total_seats = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1, "Must have at least 1 seat"),
            MaxValueValidator(1000, "Cannot exceed 1000 seats")
        ]
    )
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['movie', 'date_time']),
            models.Index(fields=['date_time']),
            models.Index(fields=['screen_name', 'date_time']),
        ]
        ordering = ['date_time']
        unique_together = ['screen_name', 'date_time']

    def __str__(self):
        return f"{self.movie.title} - {self.screen_name} - {self.date_time}"
    
    @property
    def available_seats(self):
        booked_seats = self.bookings.filter(status='booked').count()
        return self.total_seats - booked_seats
    
    @property
    def is_bookable(self):
        booking_deadline = self.date_time - timedelta(minutes=30)
        return (
            self.is_active and 
            timezone.now() < booking_deadline and
            self.available_seats > 0
        )
    
    def clean(self):
        super().clean()
        if self.date_time and self.date_time <= timezone.now():
            raise ValidationError({'date_time': 'Show date and time must be in the future'})
        
        if self.screen_name and len(self.screen_name.strip()) == 0:
            raise ValidationError({'screen_name': 'Screen name cannot be empty'})
        
        if self.screen_name and self.date_time:
            conflicting_shows = Show.objects.filter(
                screen_name=self.screen_name,
                date_time=self.date_time
            ).exclude(id=self.id)
            
            if conflicting_shows.exists():
                raise ValidationError({
                    'date_time': f'Screen {self.screen_name} is already booked at this time'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Booking(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='bookings')
    seat_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1, "Seat number must be positive")]
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='booked'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    booking_reference = models.CharField(max_length=20, unique=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['show', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['booking_reference']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['show', 'seat_number'],
                condition=models.Q(status='booked'),
                name='unique_active_booking_per_seat'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.show} - Seat {self.seat_number}"
    
    @property
    def is_cancellable(self):
        if self.status != 'booked':
            return False
        
        cancellation_deadline = self.show.date_time - timedelta(hours=2)
        return timezone.now() < cancellation_deadline
    
    @property
    def is_expired(self):
        return (
            self.status == 'booked' and 
            self.show.date_time < timezone.now()
        )
    
    def generate_booking_reference(self):
        import uuid
        return f"BK{str(uuid.uuid4())[:8].upper()}"
    
    def clean(self):
        super().clean()
        
        if self.show and self.seat_number:
            if self.seat_number > self.show.total_seats:
                raise ValidationError({
                    'seat_number': f'Seat number cannot exceed {self.show.total_seats}'
                })
        
        if self.show and self.show.date_time <= timezone.now():
            raise ValidationError({
                'show': 'Cannot create bookings for past shows'
            })
        
        if self.show and self.seat_number and self.status == 'booked':
            existing_booking = Booking.objects.filter(
                show=self.show,
                seat_number=self.seat_number,
                status='booked'
            ).exclude(id=self.id)
            
            if existing_booking.exists():
                raise ValidationError({
                    'seat_number': f'Seat {self.seat_number} is already booked'
                })
    
    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        
        if self.status == 'cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        
        if not self.expires_at and self.show:
            self.expires_at = self.show.date_time
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def cancel(self):
        if not self.is_cancellable:
            raise ValidationError("This booking cannot be cancelled")
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save()
