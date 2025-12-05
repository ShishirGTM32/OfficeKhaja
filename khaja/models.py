from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User

# class CustomUser(AbstractUser):
#     TYPE_OF_CUSTOMER = [
#         ("ORGANIZATION", "organization"),
#         ("INDIVIDUALS", "individuals")
#     ]
    
#     no_of_consumer = models.IntegerField(null=True, blank=True)
#     type = models.CharField(max_length=15, choices=TYPE_OF_CUSTOMER, default="INDIVIDUALS")
# 1

class Meals(models.Model):
    MEAL_TYPE = [
        ("VEG", "Veg"),
        ("NON-VEG", "Non-veg"),
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

class Ingredients(models.Model):
    iid = models.AutoField(primary_key=True)
    meals = models.ForeignKey(Meals, on_delete=models.CASCADE)
    ingridents = models.CharField(max_length=50)

    def __str__(self):
        return self.ingridents

class Nutrition(models.Model):
    nid = models.AutoField(primary_key=True)
    meal_id = models.ForeignKey(Meals, on_delete=models.CASCADE)
    energy = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    protien = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    carbs = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    fats = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sugar = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    def __str__(self):
        return f"{self.meal.name}, {self.energy}"

# class CustomMeal(models.Model):
#     combo_id = models.AutoField(primary_key=True)
#     meals = models.ForeignKey(Meals, on_delete=models.CASCADE)
#     no_of_servings = models.IntegerField(default=1)
#     preferences = models.TextField()
#     delivery_time = models.DateTimeField()

class Combo(models.Model):
    cid = models.AutoField(primary_key=True)
    meals = models.ForeignKey(Meals, on_delete=models.CASCADE)

class CustomMeal(models.Model):
    MEAL_TYPE = [
        ("VEG", "Veg"),
        ("NON-VEG", "Non-veg"),
        ("BOTH", "Both"),
    ]
    MEAL_CATEGORY = [
        ("MORNING BREAKFAST", "Morning Breakfast"),
        ("MORNING LUNCH", "Morning Lunch"),
        ("AFTERNOON LUNCH", "Afternoon Lunch"),
        ("EVENING LUNCH", "Evening Lunch"),
        ("NIGHT DINNER", "Night Dinner")
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    combo_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=20, choices=MEAL_TYPE, default="VEG")
    meals = models.ForeignKey(Combo, on_delete=models.CASCADE, null=True)
    category = models.CharField(max_length=50, choices=MEAL_CATEGORY)
    no_of_consumer = models.IntegerField(default=1)
    preferences = models.TextField()







