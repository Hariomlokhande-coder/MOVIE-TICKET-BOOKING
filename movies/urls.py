from django.urls import path
from .views import (
    RegisterView, LoginView, MovieListView, MovieShowsView,
    book_seat, cancel_booking, MyBookingsView
)

urlpatterns = [
    path('auth/signup/', RegisterView.as_view(), name='signup'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('movies/', MovieListView.as_view(), name='movie-list'),
    path('movies/<int:movie_id>/shows/', MovieShowsView.as_view(), name='movie-shows'),
    path('shows/<int:show_id>/book/', book_seat, name='book-seat'),
    path('bookings/<int:booking_id>/cancel/', cancel_booking, name='cancel-booking'),
    path('my-bookings/', MyBookingsView.as_view(), name='my-bookings'),
]
