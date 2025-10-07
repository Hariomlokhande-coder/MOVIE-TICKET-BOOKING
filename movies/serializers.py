from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Movie, Show, Booking
import re

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']

    def validate_username(self, value):
        if not value:
            raise serializers.ValidationError("Username is required")
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long")
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError("Username can only contain letters, numbers, and underscores")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required")
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Invalid email format")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character")
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        username = attrs.get('username', '').lower()
        
        if password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Passwords don't match"})
        
        if username in password.lower():
            raise serializers.ValidationError({"password": "Password cannot contain username"})
        
        first_name = attrs.get('first_name', '').lower()
        last_name = attrs.get('last_name', '').lower()
        if first_name and first_name in password.lower():
            raise serializers.ValidationError({"password": "Password cannot contain your first name"})
        if last_name and last_name in password.lower():
            raise serializers.ValidationError({"password": "Password cannot contain your last name"})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username', '').strip()
        password = attrs.get('password', '')

        if not username:
            raise serializers.ValidationError({"username": "Username is required"})
        if not password:
            raise serializers.ValidationError({"password": "Password is required"})

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid username or password")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")
        attrs['user'] = user
        return attrs

class MovieSerializer(serializers.ModelSerializer):
    duration_hours = serializers.SerializerMethodField()
    total_shows = serializers.SerializerMethodField()
    active_shows = serializers.SerializerMethodField()
    next_show = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = ['id', 'title', 'duration_minutes', 'duration_hours', 'created_at', 
                 'description', 'rating', 'total_shows', 'active_shows', 'next_show']

    def get_duration_hours(self, obj):
        hours = obj.duration_minutes // 60
        minutes = obj.duration_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    def get_total_shows(self, obj):
        return obj.shows.count()
    
    def get_active_shows(self, obj):
        return obj.shows.filter(date_time__gt=timezone.now(), is_active=True).count()
    
    def get_next_show(self, obj):
        next_show = obj.shows.filter(
            date_time__gt=timezone.now(), 
            is_active=True
        ).first()
        if next_show:
            return {
                'id': next_show.id,
                'screen_name': next_show.screen_name,
                'date_time': next_show.date_time.strftime("%Y-%m-%d %H:%M"),
                'available_seats': next_show.available_seats
            }
        return None

class ShowSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    available_seats = serializers.ReadOnlyField()
    is_bookable = serializers.ReadOnlyField()
    formatted_date_time = serializers.SerializerMethodField()
    booking_deadline = serializers.SerializerMethodField()
    booked_seats_list = serializers.SerializerMethodField()
    occupancy_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Show
        fields = ['id', 'movie', 'screen_name', 'date_time', 'formatted_date_time',
                 'total_seats', 'available_seats', 'is_bookable', 'price', 
                 'is_active', 'booking_deadline', 'booked_seats_list', 'occupancy_percentage']

    def get_formatted_date_time(self, obj):
        return obj.date_time.strftime("%A, %B %d, %Y at %I:%M %p")
    
    def get_booking_deadline(self, obj):
        deadline = obj.date_time - timedelta(minutes=30)
        return deadline.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_booked_seats_list(self, obj):
        return sorted(obj.bookings.filter(status='booked').values_list('seat_number', flat=True))
    
    def get_occupancy_percentage(self, obj):
        if obj.total_seats == 0:
            return 0
        booked = obj.total_seats - obj.available_seats
        return round((booked / obj.total_seats) * 100, 1)

class BookingSerializer(serializers.ModelSerializer):
    show = ShowSerializer(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    is_cancellable = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    formatted_created_at = serializers.SerializerMethodField()
    formatted_cancelled_at = serializers.SerializerMethodField()
    show_status = serializers.SerializerMethodField()
    cancellation_deadline = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['id', 'user', 'show', 'seat_number', 'status', 'created_at',
                 'formatted_created_at', 'cancelled_at', 'formatted_cancelled_at',
                 'booking_reference', 'is_cancellable', 'is_expired', 'notes',
                 'show_status', 'cancellation_deadline']

    def get_formatted_created_at(self, obj):
        return obj.created_at.strftime("%A, %B %d, %Y at %I:%M %p")
    
    def get_formatted_cancelled_at(self, obj):
        if obj.cancelled_at:
            return obj.cancelled_at.strftime("%A, %B %d, %Y at %I:%M %p")
        return None
    
    def get_show_status(self, obj):
        now = timezone.now()
        if obj.show.date_time < now:
            return "Completed"
        elif obj.show.date_time - timedelta(minutes=30) < now:
            return "Booking Closed"
        else:
            return "Upcoming"
    
    def get_cancellation_deadline(self, obj):
        if obj.status == 'booked':
            deadline = obj.show.date_time - timedelta(hours=2)
            if deadline > timezone.now():
                return deadline.strftime("%Y-%m-%d %H:%M:%S")
        return None

class BookSeatSerializer(serializers.Serializer):
    seat_number = serializers.IntegerField(min_value=1)

    def validate_seat_number(self, value):
        show = self.context.get('show')
        user = self.context.get('user')
        
        if not show:
            raise serializers.ValidationError("Show context is required")
        
        if not show.is_active:
            raise serializers.ValidationError("This show is not active")
        
        if value > show.total_seats:
            raise serializers.ValidationError(f"Seat number cannot exceed {show.total_seats}")
        
        if show.date_time <= timezone.now():
            raise serializers.ValidationError("Cannot book seats for past shows")
        
        booking_deadline = show.date_time - timedelta(minutes=30)
        if timezone.now() > booking_deadline:
            raise serializers.ValidationError("Booking closed. Cannot book seats 30 minutes before show time")
        
        if show.bookings.filter(seat_number=value, status='booked').exists():
            raise serializers.ValidationError(f"Seat {value} is already booked")
        
        user_booking_count = show.bookings.filter(user=user, status='booked').count()
        if user_booking_count >= 5:
            raise serializers.ValidationError("Maximum 5 seats allowed per user per show")
        
        existing_user_booking = show.bookings.filter(user=user, status='booked').first()
        if existing_user_booking:
            raise serializers.ValidationError(
                f"You already have seat {existing_user_booking.seat_number} booked for this show"
            )
        
        return value

class UserProfileSerializer(serializers.ModelSerializer):
    total_bookings = serializers.SerializerMethodField()
    active_bookings = serializers.SerializerMethodField()
    cancelled_bookings = serializers.SerializerMethodField()
    upcoming_bookings = serializers.SerializerMethodField()
    booking_history_summary = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                 'date_joined', 'total_bookings', 'active_bookings', 
                 'cancelled_bookings', 'upcoming_bookings', 'booking_history_summary']
        read_only_fields = ['id', 'username', 'date_joined']

    def get_total_bookings(self, obj):
        return obj.bookings.count()
    
    def get_active_bookings(self, obj):
        return obj.bookings.filter(
            status='booked',
            show__date_time__gt=timezone.now()
        ).count()
    
    def get_cancelled_bookings(self, obj):
        return obj.bookings.filter(status='cancelled').count()
    
    def get_upcoming_bookings(self, obj):
        upcoming = obj.bookings.filter(
            status='booked',
            show__date_time__gt=timezone.now()
        ).select_related('show__movie')[:3]
        
        return [{
            'id': booking.id,
            'movie': booking.show.movie.title,
            'screen': booking.show.screen_name,
            'seat': booking.seat_number,
            'date_time': booking.show.date_time.strftime("%Y-%m-%d %H:%M")
        } for booking in upcoming]
    
    def get_booking_history_summary(self, obj):
        from django.db.models import Count
        movies = obj.bookings.values('show__movie__title').annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        return [{
            'movie': movie['show__movie__title'],
            'bookings': movie['count']
        } for movie in movies]

class ShowCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Show
        fields = ['movie', 'screen_name', 'date_time', 'total_seats', 'price']

    def validate_date_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Show date and time must be in the future")
        
        min_advance = timezone.now() + timedelta(hours=1)
        if value < min_advance:
            raise serializers.ValidationError("Show must be scheduled at least 1 hour in advance")
        
        return value

    def validate_total_seats(self, value):
        if value < 10:
            raise serializers.ValidationError("Show must have at least 10 seats")
        if value > 1000:
            raise serializers.ValidationError("Show cannot have more than 1000 seats")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        if value > 10000:
            raise serializers.ValidationError("Price cannot exceed ₹10,000")
        return value

    def validate(self, attrs):
        screen_name = attrs.get('screen_name')
        date_time = attrs.get('date_time')
        
        if screen_name and date_time:
            conflicting_show = Show.objects.filter(
                screen_name=screen_name,
                date_time=date_time
            ).exists()
            
            if conflicting_show:
                raise serializers.ValidationError({
                    'date_time': f'Screen {screen_name} is already booked at this time'
                })
        
        return attrs

class CancelBookingSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False)
    
    def validate(self, attrs):
        booking = self.context.get('booking')
        if not booking:
            raise serializers.ValidationError("Booking context is required")
        
        if booking.status != 'booked':
            raise serializers.ValidationError("Only active bookings can be cancelled")
        
        if not booking.is_cancellable:
            raise serializers.ValidationError(
                "Cannot cancel booking less than 2 hours before show time"
            )
        
        return attrs
