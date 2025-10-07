from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from movies.models import Movie, Show, Booking
import random

class Command(BaseCommand):
    help = 'Creates sample data for testing the movie booking system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--movies',
            type=int,
            default=10,
            help='Number of movies to create'
        )
        parser.add_argument(
            '--shows',
            type=int,
            default=20,
            help='Number of shows to create'
        )
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of users to create'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))

        movies_data = [
            {'title': 'Avengers: Endgame', 'duration': 181, 'rating': 'PG-13'},
            {'title': 'The Dark Knight', 'duration': 152, 'rating': 'PG-13'},
            {'title': 'Inception', 'duration': 148, 'rating': 'PG-13'},
            {'title': 'Interstellar', 'duration': 169, 'rating': 'PG-13'},
            {'title': 'Spider-Man: No Way Home', 'duration': 148, 'rating': 'PG-13'},
            {'title': 'Black Panther', 'duration': 134, 'rating': 'PG-13'},
            {'title': 'Avatar', 'duration': 162, 'rating': 'PG-13'},
            {'title': 'Titanic', 'duration': 195, 'rating': 'PG-13'},
            {'title': 'The Lion King', 'duration': 118, 'rating': 'G'},
            {'title': 'Frozen 2', 'duration': 103, 'rating': 'G'},
        ]

        screens = ['Screen 1', 'Screen 2', 'Screen 3', 'IMAX 1', 'IMAX 2', 'Premium 1']
        
        movies_created = 0
        for i in range(options['movies']):
            if i < len(movies_data):
                data = movies_data[i]
                movie, created = Movie.objects.get_or_create(
                    title=data['title'],
                    defaults={
                        'duration_minutes': data['duration'],
                        'rating': data['rating'],
                        'description': f"Great {data['title']} movie for entertainment"
                    }
                )
                if created:
                    movies_created += 1
            else:
                movie = Movie.objects.create(
                    title=f'Sample Movie {i+1}',
                    duration_minutes=random.randint(90, 180),
                    rating=random.choice(['G', 'PG', 'PG-13', 'R']),
                    description=f'Sample movie {i+1} description'
                )
                movies_created += 1

        shows_created = 0
        movies = Movie.objects.all()
        for i in range(options['shows']):
            movie = random.choice(movies)
            screen = random.choice(screens)
            
            days_ahead = random.randint(1, 7)
            hour = random.choice([12, 15, 18, 21])
            show_time = timezone.now().replace(
                hour=hour, minute=0, second=0, microsecond=0
            ) + timedelta(days=days_ahead)
            
            try:
                show = Show.objects.create(
                    movie=movie,
                    screen_name=screen,
                    date_time=show_time,
                    total_seats=random.choice([80, 100, 120, 150]),
                    price=random.choice([250.00, 300.00, 350.00, 400.00, 500.00])
                )
                shows_created += 1
            except:
                continue

        users_created = 0
        for i in range(options['users']):
            username = f'user{i+1}'
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    email=f'{username}@example.com',
                    password='password123',
                    first_name=f'User{i+1}',
                    last_name='Test'
                )
                users_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created:\n'
                f'- {movies_created} movies\n'
                f'- {shows_created} shows\n'
                f'- {users_created} users'
            )
        )
