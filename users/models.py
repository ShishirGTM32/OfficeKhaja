
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from datetime import timedelta, datetime
from django.utils import timezone


class Subscription(models.Model):
    SUBSCRIPTION_TYPE = [
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly")
    ]

    sid = models.AutoField(primary_key=True)
    subscription = models.CharField(max_length=8, choices=SUBSCRIPTION_TYPE, default="WEEKLY")
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(help_text="Duration in days", default=7)

    def __str__(self):
        return f"{self.subscription} - Rs. {self.rate}"

    class Meta:
        verbose_name_plural = "Subscriptions"


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("The Phone Number must be set")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)

email_regex = RegexValidator(
    regex=r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$',
    message="Enter a valid email address."
)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    PAYMENT_METHOD = [
        ("ESEWA", "E-Sewa"),
        ("KHALTI", "Khalti"),
        ("CARD", "Card"),
    ]

    SUBSCRIPTION_STATUS = [
        ("NOT_STARTED", "Not Started"),
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired")
    ]

    USER_TYPE = [
        ("INDIVIDUALS", "Individuals"),
        ("ORGANIZATIONS", "Organizations")
    ]

    phone_number = models.CharField(
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^(?:\+977[- ]?)?(?:9[78]\d{8}|1\d{7})$',
                message="Enter a valid Nepal phone number."
            )
        ]
    )
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    email = models.EmailField(
        max_length=254,
        validators=[email_regex],
        unique=True,
    )

    image = models.ImageField(upload_to='profile/', null=True, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE, default="INDIVIDUALS")
    no_of_peoples = models.IntegerField(default=1)
    payment_method = models.CharField(max_length=255, choices=PAYMENT_METHOD, default='ESEWA')
    street_address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=20, default="Kathmandu")
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default="NOT_STARTED")
    meal_preferences = models.TextField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class UserSubscription(models.Model):
    sub_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user_subscription')
    plan = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    activated_from = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.plan.subscription}"

    def save(self, *args, **kwargs):
        if self.activated_from and self.plan and self.plan.duration_days:
            if isinstance(self.activated_from, datetime):
                self.activated_from = self.activated_from.date()

            self.expires_on = self.activated_from + timedelta(days=self.plan.duration_days)

        if self.expires_on and self.expires_on < timezone.now().date():
            self.is_active = False
        
        super().save(*args, **kwargs)

    def is_expired(self):
        if self.expires_on:
            return self.expires_on < timezone.now().date()
        return True

    def days_remaining(self):
        if self.expires_on and not self.is_expired():
            delta = self.expires_on - timezone.now().date()
            return delta.days
        return 0

    class Meta:
        verbose_name = "User Subscription"
        verbose_name_plural = "User Subscriptions"