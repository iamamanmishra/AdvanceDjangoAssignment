from rest_framework import serializers
from .models import User, Event, Booking, Payment
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='user')

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'role', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            role=validated_data['role'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['role'] = user.role
        return token


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception as e:
            self.fail('bad_token')


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['created_by', 'available_tickets']


class EventListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'user', 'event', 'number_of_tickets', 'booking_date', 'status']
        read_only_fields = ['user', 'booking_date', 'status']

    def validate(self, attrs):
        event = attrs.get('event')
        number_of_tickets = attrs.get('number_of_tickets')
        if event.available_tickets < number_of_tickets:
            raise serializers.ValidationError("Not enough tickets available.")
        return attrs

    def create(self, validated_data):
        event = validated_data['event']
        number_of_tickets = validated_data['number_of_tickets']
        event.available_tickets -= number_of_tickets
        event.save()
        booking = Booking.objects.create(**validated_data)
        return booking


class BookingDetailSerializer(serializers.ModelSerializer):
    event = EventListSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'event', 'number_of_tickets', 'booking_date', 'status']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'booking', 'payment_method', 'amount', 'payment_date', 'status']
        read_only_fields = ['payment_date', 'status']

    def validate(self, attrs):
        booking = attrs.get('booking')
        if booking.status == 'cancelled':
            raise serializers.ValidationError("Cannot make payment for a cancelled booking.")
        if hasattr(booking, 'payment'):
            raise serializers.ValidationError("Payment already made for this booking.")
        return attrs

    def create(self, validated_data):
        payment = Payment.objects.create(**validated_data)
        return payment


class RevertPaymentSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    reason = serializers.CharField()

    def validate_booking_id(self, value):
        try:
            booking = Booking.objects.get(id=value)
            return booking
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking does not exist.")

    def save(self, **kwargs):
        booking = self.validated_data['booking_id']
        reason = self.validated_data['reason']

        if not hasattr(booking, 'payment'):
            raise serializers.ValidationError("No payment found for this booking.")

        payment = booking.payment
        payment.status = 'reverted'
        payment.save()

        # Update booking status
        booking.status = 'cancelled'
        booking.save()

        # Update available tickets
        event = booking.event
        event.available_tickets += booking.number_of_tickets
        event.save()

        # Send Email Notification (optional)
        # Implement email sending here
