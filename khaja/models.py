from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField

class CustomUser(AbstractUser):
    TYPE_OF_CUSTOMER = [
        ("ORGANIZATION", "organization"),
        ("INDIVIDUALS", "individuals")
    ]
    
    no_of_consumer = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=15, choices=TYPE_OF_CUSTOMER, default="INDIVIDUALS")
1

class Meals(models.Model):
    MEAL_TYPE = [
        ("VEG", "Veg"),
        ("NON-VEG", "Non-veg"),
        ("BOTH", "Both")
    ]
    MEAL_TIME_TYPE = [
        ("MORNING BREAKFAST", "Morning Breakfast"),
        ("MORNING LUNCH", "Morning Lunch"),
        ("AFTERNOON LUNCH", "Afternoon Lunch"),
        ("EVENING LUNCH", "Envening Lunch"),
        ("NIGHT DINNER", "Night Dinner")
    ]

    meal_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    description = models.TextField()
    type = models.CharField(choices=MEAL_TYPE)
    meal_category = models.CharField(choices=MEAL_TIME_TYPE, default="MORNING BREAKFAST")
    price = models.DecimalField(max_digits=6, decimal_places=2)
    
    def __str__(self):
        return f"{self.name}, {self.description}"
    
class Nutrition(models.Model):
    nid = models.AutoField(primary_key=True)
    meal_id = models.ForeignKey(Meals, on_delete=models.CASCADE)
    energy = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    protien = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    carbs = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    fats = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sugar = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)



class CustomMeal(models.Model):
    combo_id = models.AutoField(primary_key=True)
    meals = models.ForeignKey(Meals, on_delete=models.CASCADE)
    no_of_servings = models.IntegerField(default=1)
    preferences = models.TextField()
    delivery_time = models.DateTimeField()





