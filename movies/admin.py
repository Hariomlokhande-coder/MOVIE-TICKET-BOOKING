from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from .models import Movie, Show, Booking

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'duration_minutes', 'duration_display', 'total_shows', 'created_at']
    list_filter = ['created_at', 'rating']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    def duration_display(self, obj):
        hours = obj.duration_minutes // 60
        minutes = obj.duration_minutes % 60
        return f"{hours}h {minutes}m"
    duration_display.short_description = 'Duration'

    def total_shows(self, obj):
        return obj.shows.count()
    total_shows.short_description = 'Total Shows'

@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ['movie', 'screen_name', 'date_time', 'total_seats', 
                   'available_seats_display', 'price', 'is_active', 'booking_status']
    list_filter = ['date_time', 'screen_name', 'is_active', 'movie']
    search_fields = ['movie__title', 'screen_name']
    readonly_fields = ['available_seats_display']
    date_hierarchy = 'date_time'
    ordering = ['-date_time']

    def available_seats_display(self, obj):
        available = obj.available_seats
        total = obj.total_seats
        percentage = (available / total) * 100 if total > 0 else 0
        
        if percentage > 50:
            color = 'green'
        elif percentage > 20:
            color = 'orange'
        else:
            color = 'red'
            
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color, available, total, int(percentage)
        )
    available_seats_display.short_description = 'Available Seats'

    def booking_status(self, obj):
        total_bookings = obj.bookings.filter(status='booked').count()
        if total_bookings == 0:
            return format_html('<span style="color: gray;">No Bookings</span>')
        elif obj.available_seats == 0:
            return format_html('<span style="color: red;">Sold Out</span>')
        else:
            return format_html('<span style="color: green;">Booking Open</span>')
    booking_status.short_description = 'Status'

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'user', 'show_info', 'seat_number', 
                   'status', 'created_at', 'is_cancellable_display']
    list_filter = ['status', 'created_at', 'show__movie', 'show__screen_name']
    search_fields = ['user__username', 'booking_reference', 'show__movie__title']
    readonly_fields = ['booking_reference', 'created_at', 'cancelled_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def show_info(self, obj):
        return f"{obj.show.movie.title} - {obj.show.screen_name}"
    show_info.short_description = 'Show'

    def is_cancellable_display(self, obj):
        if obj.is_cancellable:
            return format_html('<span style="color: green;">Yes</span>')
        return format_html('<span style="color: red;">No</span>')
    is_cancellable_display.short_description = 'Cancellable'

    actions = ['cancel_selected_bookings']

    def cancel_selected_bookings(self, request, queryset):
        cancelled_count = 0
        for booking in queryset:
            if booking.is_cancellable:
                booking.cancel()
                cancelled_count += 1
        
        self.message_user(request, f'{cancelled_count} bookings were cancelled.')
    cancel_selected_bookings.short_description = "Cancel selected bookings"
