from django.db import models
from users.models import CustomUser
from django.contrib.postgres.fields import ArrayField
from users.models import UserSubscription
from django.utils.text import slugify
from datetime import datetime, time
import uuid


class Type(models.Model):
    type_id = models.AutoField(primary_key=True)
    slug = models.SlugField(unique=True)
    type_name = models.CharField(max_length=100, null=False)

    def __str__(self):
        return self.type_name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            super().save(*args, **kwargs)
            self.slug = slugify(self.type_name)
            kwargs['force_insert'] = False
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class MealCategory(models.Model):
    cat_id = models.AutoField(primary_key=True)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=30)

    def __str__(self):
        return self.category
    
    def save(self, *args, **kwargs):
        if not self.slug:
            super().save(*args, **kwargs)
            self.slug = slugify(self.category)
            kwargs['force_insert'] = False
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class DeliveryTimeSlot(models.Model):
    slot_id = models.AutoField(primary_key=True)
    slug = models.SlugField(unique=True, blank=True)
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['start_time']
        verbose_name_plural = "Delivery Time Slots"
        constraints = [
            models.UniqueConstraint(fields=['start_time', 'end_time'], name='unique_time_slot')
        ]
        indexes = [
            models.Index(fields=['start_time', 'end_time'])
        ]

    def __str__(self):
        return f"{self.display_name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"
    
    def get_time_range(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    def is_time_in_slot(self, check_time):
        if isinstance(check_time, datetime):
            check_time = check_time.time()
        return self.start_time <= check_time <= self.end_time

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Meals(models.Model):
    meal_id = models.AutoField(primary_key=True)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField()
    type = models.ForeignKey(Type, on_delete=models.CASCADE)
    meal_category = models.ForeignKey(MealCategory, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='meals/', null=True, blank=True)
    weight = models.IntegerField(default=0, help_text="Weight in grams")
    is_available = models.BooleanField(default=True, help_text="Is this meal available for ordering?")
    
    def __str__(self):
        return f"{self.name} - {self.meal_category}"

    class Meta:
        verbose_name_plural = "Meals"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            super().save(*args, **kwargs)
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{self.meal_id}"
            kwargs['force_insert'] = False
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class Ingredient(models.Model):
    id = models.AutoField(primary_key=True)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            super().save(*args, **kwargs)
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}"
            kwargs['force_insert'] = False
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Ingredients"
        ordering = ['name']


class MealIngredient(models.Model):
    meal = models.OneToOneField(Meals, on_delete=models.CASCADE, related_name='meal_ingredients', primary_key=True)
    ingredient_ids = ArrayField(models.IntegerField(), default=list, blank=True, help_text="List of ingredient IDs")
    
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
        total = {'energy': 0, 'protein': 0, 'carbs': 0, 'fats': 0, 'sugar': 0, 'weight': 0}
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

def generate_unique_uuid():
    while True:
        new_uuid = uuid.uuid4()
        if not CustomMeal.objects.filter(public_id=new_uuid).exists():
            return new_uuid

class CustomMeal(models.Model):
    combo_id = models.AutoField(primary_key=True)
    public_id = models.UUIDField(default=generate_unique_uuid, editable=False, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='custom_users')
    meals = models.ForeignKey(Combo, on_delete=models.CASCADE, null=True, related_name='custom_meals')
    type = models.ForeignKey(Type, on_delete=models.CASCADE)
    meal_category = models.ForeignKey(MealCategory, on_delete=models.CASCADE)
    no_of_servings = models.IntegerField(default=1, help_text="Number of people")
    preferences = models.TextField(blank=True)
    subscription_plan = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, null=True)
    delivery_time_slot = models.ForeignKey(DeliveryTimeSlot, on_delete=models.CASCADE,help_text="Preferred delivery time window")
    delivery_date = models.DateField(null=True, blank=True, help_text="Specific delivery date")
    delivery_address = models.TextField(blank=True, help_text="Delivery address for this meal")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def get_total_price(self):
        if self.meals:
            base_price = self.meals.get_total_price()
            return base_price * self.no_of_servings
        return 0
    
    def get_formatted_delivery_time(self):
        if self.delivery_date and self.delivery_time_slot:
            formatted_date = self.delivery_date.strftime('%d %b %Y')
            time_range = self.delivery_time_slot.get_time_range()
            return f"{formatted_date}, ({time_range})"
        return ""

    def __str__(self):
        return f"Custom Meal #{self.combo_id} - {self.meal_category} for {self.user.first_name}"

    class Meta:
        verbose_name_plural = "Custom Meals"
        ordering = ['-created_at']
