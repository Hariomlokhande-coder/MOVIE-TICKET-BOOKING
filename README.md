# Movie Ticket Booking System

A backend application built using **Django** and **Django REST Framework** that allows users to register, browse movies, view showtimes, and book or cancel movie tickets.  
It includes secure authentication, role-based access, and Swagger documentation for easy API testing.

---

## Features

- User authentication using JWT (signup and login)  
- Movie and show management  
- Seat booking with real-time validation  
- Booking management (view and cancel tickets)  
- Swagger API documentation for easy testing  
- Business rules and validation to prevent double-booking or invalid actions  

---

## Tech Stack

| Component | Technology |
|------------|-------------|
| Backend | Django 4.x, Django REST Framework |
| Authentication | JWT (`djangorestframework-simplejwt`) |
| Database | SQLite (Development) |
| Documentation | Swagger (`drf-yasg`) |
| Deployment | Docker (optional) |

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd movie-ticket-booking
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Database
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser
```bash
python manage.py createsuperuser
```

### 6. Run the Server
```bash
python manage.py runserver
```

The server runs at: **http://localhost:8000**

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|-----------|-------------|
| POST | `/api/auth/signup/` | Register new user |
| POST | `/api/auth/login/` | Login and receive JWT tokens |

### Movies & Shows
| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | `/api/movies/` | List all movies |
| GET | `/api/movies/{movie_id}/shows/` | List shows for a specific movie |

### Booking
| Method | Endpoint | Description |
|--------|-----------|-------------|
| POST | `/api/shows/{show_id}/book/` | Book a seat |
| GET | `/api/my-bookings/` | View user bookings |
| POST | `/api/bookings/{booking_id}/cancel/` | Cancel a booking |

### Documentation
| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | `/swagger/` | Swagger UI for API docs |
| GET | `/redoc/` | Alternative API documentation |
| GET | `/admin/` | Django Admin panel |

---

## Authentication

Protected endpoints require a valid JWT access token in the header:
```
Authorization: Bearer <your_access_token>
```

**Token Expiry**
- Access Token: 1 hour  
- Refresh Token: 24 hours  

---

## Data Models (Simplified)

```python
class Movie(models.Model):
    title = models.CharField(max_length=200)
    duration_minutes = models.IntegerField()

class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    screen_name = models.CharField(max_length=100)
    date_time = models.DateTimeField()
    total_seats = models.IntegerField()

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    seat_number = models.IntegerField()
    status = models.CharField(max_length=10, choices=[('booked','Booked'),('cancelled','Cancelled')])
```

---

## Booking Rules

- A user can book up to 5 seats per show.  
- Cannot book seats for past shows.  
- Cannot cancel less than 2 hours before showtime.  
- Seat numbers must be valid and unique for that show.

---

## Common Errors

| Error Type | Example |
|-------------|----------|
| 400 Bad Request | `{ "error": "Seat number must be valid." }` |
| 401 Unauthorized | `{ "detail": "Authentication credentials were not provided." }` |
| 404 Not Found | `{ "error": "Show not found." }` |

---

## Testing

Open Swagger UI in your browser:  
`http://localhost:8000/swagger/`

Or use curl:
```bash
curl -X GET http://localhost:8000/api/movies/   -H "Authorization: Bearer <access_token>"
```

---

## Docker (Optional)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

---

## Future Enhancements

- Integrate online payment gateway  
- Add email and SMS notifications for bookings  
- Implement seat layout selection  
- Introduce user roles (Admin, Manager, Customer)  
- Add multi-language support  
- Implement movie recommendation system  
- Improve caching and performance (Redis)  
- Develop a frontend using React or Next.js  

---

## License

This project is licensed under the **MIT License**.  
You can modify and use it for learning or other projects.

---

## Support

For questions or issues:
- Open a GitHub issue  
- Or contact: `hariomlokhande3456@gmail.com`
