from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    TYPE_OF_CUSTOMER = [
        ("ORGANIZATION", "organization"),
        ("INDIVIDUALS", "individuals")
    ]
    
    no_of_consumer = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=15, choices=TYPE_OF_CUSTOMER, default="INDIVIDUALS")




