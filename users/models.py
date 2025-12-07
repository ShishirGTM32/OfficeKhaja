from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator

class Subscription(models.Model):
    SUBSCRIPTION_TYPE = [
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly")
    ]

    sid = models.AutoField(primary_key=True)
    subscription = models.CharField(max_length=8, choices=SUBSCRIPTION_TYPE, default="WEELLY")
    rate = models.DecimalField(max_digits=10, decimal_places=2)


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

class CustomUser(AbstractBaseUser, PermissionsMixin):
    PAYMENT_METHOD = [
        ("ESEWA", "E-Sewa"),
        ("KHALTI", "Khalti"),
        ("CARD", "Card"),
    ]

    SUBSCRIPTION_STATUS = [
        ("NOT STARTED", "Not Started"),
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
    image = models.ImageField(upload_to='profile/', null=True, blank=True)
    user_type = models.CharField(choices=USER_TYPE, default="INDIVIDUALS")
    no_of_peoples = models.IntegerField(default=1)
    payment_method = models.CharField(max_length=255, choices=PAYMENT_METHOD, default='ESEWA')
    street_address = models.CharField(max_length=50, null=True)    
    city = models.CharField(max_length=20, default="Kathmandu")
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default="NOT STARTED")    
    meal_preferences = models.TextField(null=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class UserSubscription(models.Model):
    PAYMENT_STATUS = {
        ("PAID", "Paid"),
        ('UNPAID', 'Unpaid')
    }
    sub_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    plan = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    activated_from = models.DateField(null=True, blank=True)
    payment_status = models.CharField(choices=PAYMENT_STATUS, default="UNPAID")

    def __str__(self):
        return self.plan.subscription



