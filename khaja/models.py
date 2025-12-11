# khaja/models.py
from django.db import models
from users.models import CustomUser
from django.contrib.postgres.fields import ArrayField
from users.models import UserSubscription
from datetime import datetime

class Meals(models.Model):
    MEAL_TYPE = [
        ("VEG", "Veg"),
        ("NON-VEG", "Non-veg"),
    ]
    
    MEAL_TIME_TYPE = [
        ("MORNING BREAKFAST", "Morning Breakfast"),
        ("MORNING LUNCH", "Morning Lunch"),
        ("AFTERNOON LUNCH", "Afternoon Lunch"),
        ("EVENING LUNCH", "Evening Lunch"),
        ("NIGHT DINNER", "Night Dinner")
    ]

    meal_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    description = models.TextField()
    type = models.CharField(choices=MEAL_TYPE, max_length=10)
    meal_category = models.CharField(choices=MEAL_TIME_TYPE, default="MORNING BREAKFAST", max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='meals/', null=True, blank=True)
    weight = models.IntegerField(default=0, help_text="Weight in grams")
    is_available = models.BooleanField(default=True, help_text="Is this meal available for ordering?")
    def __str__(self):
        return f"{self.name} - {self.meal_category}"

    class Meta:
        verbose_name_plural = "Meals"


class Ingredient(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Ingredients"
        ordering = ['name']


class MealIngredient(models.Model):
    meal = models.OneToOneField(Meals, on_delete=models.CASCADE, related_name='meal_ingredients', primary_key=True)
    ingredient_ids = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="List of ingredient IDs"
    )
    
    def get_ingredients(self):
        return Ingredient.objects.filter(id__in=self.ingredient_ids)
    
    def add_ingredient(self, ingredient_id):
        if ingredient_id not in self.ingredient_ids:
            self.ingredient_ids.append(ingredient_id)
            self.save()
    
    def remove_ingredient(self, ingredient_id):
        if ingredient_id in self.ingredient_ids:
            self.ingredient_ids.remove(ingredient_id)
            self.save()
    
    def __str__(self):
        return f"Ingredients for {self.meal.name}"

    class Meta:
        verbose_name_plural = "Meal Ingredients"


class Nutrition(models.Model):
    nid = models.AutoField(primary_key=True)
    meal_id = models.OneToOneField(Meals, on_delete=models.CASCADE, related_name='nutrition')
    energy = models.DecimalField(max_digits=7, decimal_places=2, default=0.0, help_text="in kcal")
    protein = models.DecimalField(max_digits=7, decimal_places=2, default=0.0, help_text="in grams")
    carbs = models.DecimalField(max_digits=7, decimal_places=2, default=0.0, help_text="in grams")
    fats = models.DecimalField(max_digits=7, decimal_places=2, default=0.0, help_text="in grams")
    sugar = models.DecimalField(max_digits=7, decimal_places=2, default=0.0, help_text="in grams")
    
    def __str__(self):
        return f"Nutrition for {self.meal_id.name}"

    class Meta:
        verbose_name_plural = "Nutrition"


class Combo(models.Model):
    cid = models.AutoField(primary_key=True)
    meals = models.ManyToManyField(Meals, related_name='combos')

    def get_total_price(self):
        return sum(meal.price for meal in self.meals.all())

    def get_total_nutrition(self):
        total = {
            'energy': 0,
            'protein': 0,
            'carbs': 0,
            'fats': 0,
            'sugar': 0,
            'weight': 0
        }
        for meal in self.meals.all():
            if hasattr(meal, 'nutrition'):
                total['energy'] += float(meal.nutrition.energy)
                total['protein'] += float(meal.nutrition.protein)
                total['carbs'] += float(meal.nutrition.carbs)
                total['fats'] += float(meal.nutrition.fats)
                total['sugar'] += float(meal.nutrition.sugar)
            total['weight'] += meal.weight
        return total

    def __str__(self):
        return f"Combo #{self.cid}"

    class Meta:
        verbose_name_plural = "Combos"



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
    
    DELIVERY_TIME_SLOTS = [
        ("MORNING_BREAKFAST", "Morning Breakfast"),
        ("LUNCH", "Lunch"),
        ("EVENING_SNACK", "Evening Snack"),
        ("DINNER", "Dinner"),
    ]
    
    TIME_SLOT_RANGES = {
        "MORNING_BREAKFAST": ("07:00", "10:00"),
        "LUNCH": ("11:00", "14:30"),
        "EVENING_SNACK": ("15:00", "18:00"),
        "DINNER": ("18:30", "22:00"),
    }

    combo_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='custom_users')
    type = models.CharField(max_length=20, choices=MEAL_TYPE, default="VEG")
    meals = models.ForeignKey(Combo, on_delete=models.CASCADE, null=True, related_name='custom_meals')
    category = models.CharField(max_length=50, choices=MEAL_CATEGORY)
    no_of_servings = models.IntegerField(default=1, help_text="Number of people")
    preferences = models.TextField(blank=True)
    subscription_plan = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, null=True)
    delivery_time_slot = models.CharField(max_length=50,choices=DELIVERY_TIME_SLOTS,null=True,blank=True,help_text="Preferred delivery time window")
    delivery_time = models.DateTimeField(null=True, blank=True,help_text="Specific delivery date and time")
    delivery_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def get_total_price(self):
        if self.meals:
            base_price = self.meals.get_total_price()
            return base_price * self.no_of_servings
        return 0
    
    def get_time_slot_range(self):
        if self.delivery_time_slot:
            return self.TIME_SLOT_RANGES.get(self.delivery_time_slot, ("00:00", "00:00"))
        return ("00:00", "00:00")

    def get_formatted_delivery_time(self):
        if self.delivery_time:
            date_str = self.delivery_time.strftime('%d %b %Y')
            start_str, end_str = self.get_time_slot_range() 
            start_time = datetime.strptime(start_str, '%H:%M').strftime('%I:%M %p')
            end_time = datetime.strptime(end_str, '%H:%M').strftime('%I:%M %p')
            return f"{date_str}, ({start_time}-{end_time})"
        return ""



    def __str__(self):
        return f"Custom Meal #{self.combo_id} - {self.category} for {self.user.first_name}"

    class Meta:
        verbose_name_plural = "Custom Meals"
        ordering = ['-created_at']