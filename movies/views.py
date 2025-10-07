from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import logging
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Movie, Show, Booking
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, MovieSerializer,
    ShowSerializer, BookingSerializer, BookSeatSerializer
)


logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Register a new user",
        responses={201: "User created successfully", 400: "Validation error"}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "User created successfully", 
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            },
            status=status.HTTP_201_CREATED
        )


class LoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login user and return JWT tokens",
        responses={200: "Login successful", 400: "Invalid credentials"}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Login successful',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })


class MovieListView(generics.ListAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(operation_description="Get list of all movies")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MovieShowsView(generics.ListAPIView):
    serializer_class = ShowSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        movie_id = self.kwargs.get('movie_id')
        return Show.objects.filter(
            movie_id=movie_id,
            date_time__gt=timezone.now()
        ).order_by('date_time')

    @swagger_auto_schema(
        operation_description="Get all future shows for a specific movie",
        manual_parameters=[
            openapi.Parameter('movie_id', openapi.IN_PATH, description="Movie ID", type=openapi.TYPE_INTEGER)
        ]
    )
    def get(self, request, *args, **kwargs):
        movie_id = self.kwargs.get('movie_id')
        if not Movie.objects.filter(id=movie_id).exists():
            return Response(
                {"error": "Movie not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        return super().get(request, *args, **kwargs)


def check_user_booking_limits(user, show):
    """Check if user has exceeded booking limits"""
    user_bookings_count = Booking.objects.filter(
        user=user, show=show, status='booked'
    ).count()
    return user_bookings_count < 5, "Maximum 5 seats allowed per user per show"


@swagger_auto_schema(
    method='post',
    operation_description="Book a seat for a show",
    request_body=BookSeatSerializer,
    responses={201: BookingSerializer, 400: "Validation error"}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_seat(request, show_id):
    logger.info(f"User {request.user.username} attempting to book seat for show {show_id}")
    
    try:
        show = Show.objects.get(id=show_id)
    except Show.DoesNotExist:
        return Response({
            'error': 'Show not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    seat_number = request.data.get('seat_number')
    
    if not seat_number:
        return Response({
            'error': 'Seat number is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        seat_number = int(seat_number)
    except (ValueError, TypeError):
        return Response({
            'error': 'Seat number must be a valid integer'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if seat_number <= 0:
        return Response({
            'error': 'Seat number must be positive'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if seat_number > show.total_seats:
        return Response({
            'error': f'Seat number cannot exceed {show.total_seats}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if show.date_time < timezone.now():
        return Response({
            'error': 'Cannot book seats for past shows'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    booking_deadline = show.date_time - timedelta(minutes=30)
    if timezone.now() > booking_deadline:
        return Response({
            'error': 'Booking closed. Cannot book seats 30 minutes before show time'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    existing_user_booking = Booking.objects.filter(
        user=request.user, 
        show=show, 
        status='booked'
    ).first()
    
    if existing_user_booking:
        return Response({
            'error': f'You already have seat {existing_user_booking.seat_number} booked for this show'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    can_book, limit_message = check_user_booking_limits(request.user, show)
    if not can_book:
        return Response({
            'error': limit_message
        }, status=status.HTTP_400_BAD_REQUEST)
    
    with transaction.atomic():
        existing_booking = Booking.objects.filter(
            show=show, 
            seat_number=seat_number, 
            status='booked'
        ).first()
        
        if existing_booking:
            return Response({
                'error': f'Seat {seat_number} is already booked by {existing_booking.user.username}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        booking = Booking.objects.create(
            user=request.user,
            show=show,
            seat_number=seat_number,
            status='booked'
        )
        
        logger.info(f"Seat {seat_number} booked successfully by {request.user.username}")
    
    booking_serializer = BookingSerializer(booking)
    return Response(
        {
            "message": "Seat booked successfully",
            "booking": booking_serializer.data
        },
        status=status.HTTP_201_CREATED
    )


@swagger_auto_schema(
    method='post',
    operation_description="Cancel a booking",
    responses={200: "Booking cancelled successfully", 400: "Cannot cancel booking"}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({
            'error': 'Booking not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if booking.user != request.user:
        return Response({
            'error': 'You can only cancel your own bookings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if booking.status == 'cancelled':
        return Response({
            'error': 'Booking is already cancelled'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if booking.show.date_time < timezone.now():
        return Response({
            'error': 'Cannot cancel bookings for past shows'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    cancellation_deadline = booking.show.date_time - timedelta(hours=2)
    if timezone.now() > cancellation_deadline:
        return Response({
            'error': 'Cannot cancel booking less than 2 hours before show time'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    booking.status = 'cancelled'
    booking.save()
    
    logger.info(f"Booking {booking_id} cancelled by {request.user.username}")
    
    booking_serializer = BookingSerializer(booking)
    return Response({
        'message': 'Booking cancelled successfully',
        'booking': booking_serializer.data
    }, status=status.HTTP_200_OK)


class MyBookingsView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')

    @swagger_auto_schema(operation_description="Get current user's bookings")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
