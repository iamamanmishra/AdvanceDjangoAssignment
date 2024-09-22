from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.

class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('event_manager', 'Event Manager'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    email = models.EmailField(unique=True)

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']  # Use existing fields

    def __str__(self):
        return self.username


class Event(models.Model):
    CATEGORY_CHOICES = (
        ('music', 'Music'),
        ('sports', 'Sports'),
        ('theatre', 'Theatre'),
        # Add more categories as needed
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    payment_options = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    total_tickets = models.PositiveIntegerField(default=100)  # Example field
    available_tickets = models.PositiveIntegerField(default=100)

    def __str__(self):
        return self.title


class Booking(models.Model):
    STATUS_CHOICES = (
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    number_of_tickets = models.PositiveIntegerField()
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')

    def __str__(self):
        return f"{self.user.username} - {self.event.title}"


class Payment(models.Model):
    STATUS_CHOICES = (
        ('completed', 'Completed'),
        ('reverted', 'Reverted'),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    def __str__(self):
        return f"Payment for {self.booking}"
