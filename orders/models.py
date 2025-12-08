# orders/models.py
from django.db import models
from khaja.models import Meals, Combo, CustomMeal
from users.models import CustomUser
from decimal import Decimal
from datetime import datetime

class Order(models.Model):
    STATUS_CHOICES = [
        ("CANCELLED", "Cancelled"),
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("DELIVERING", "Delivering"),
        ("DELIVERED", "Delivered")
    ]

    PAYMENT_METHOD = [
        ("ESEWA", "E-Sewa"),
        ("KHALTI", "Khalti"),
        ("CARD", "Card"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=255, choices=PAYMENT_METHOD)
    delivery_address = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def calculate_pricing(self):
        subtotal = sum(item.get_total_price() for item in self.order_items.all())
        subtotal += sum(item.get_total_price() for item in self.combo_items.all())
        
        tax_rate = Decimal('0.13')
        delivery_charge = Decimal('50.00')

        tax = subtotal * tax_rate
        total_price = subtotal + tax + delivery_charge
        self.subtotal = subtotal
        self.tax = tax
        self.delivery_charge = delivery_charge
        self.total_price = total_price
        self.save()

    def __str__(self):
        return f"Order #{self.id} by {self.user.first_name if self.user else 'Guest'}"


class OrderItem(models.Model):
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
    
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    custom_meal = models.ForeignKey(CustomMeal, on_delete=models.SET_NULL, null=True, blank=True)
    meals = models.ForeignKey(Meals, on_delete=models.CASCADE, null=True, blank=True)
    meal_type = models.CharField(max_length=20)
    meal_category = models.CharField(max_length=50)
    no_of_servings = models.PositiveIntegerField(default=1)
    subscription_plan = models.CharField(max_length=20)
    delivery_time_slot = models.CharField(max_length=50, choices=DELIVERY_TIME_SLOTS, null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)
    price_per_serving = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    quantity = models.PositiveIntegerField(default=1)
    meal_items_snapshot = models.JSONField(default=dict)

    def get_price_per_item(self):
        if self.custom_meal:
            return self.custom_meal.get_total_price()
        elif self.meals:
            return self.meals.price * Decimal(self.no_of_servings)
        return Decimal('0.00')

    def get_total_price(self):
        return self.get_price_per_item() * Decimal(self.quantity)
    
    def get_time_slot_range(self):
        if self.delivery_time_slot:
            start, end = self.TIME_SLOT_RANGES.get(self.delivery_time_slot, ("", ""))
            return f"{start} - {end}"
        return ""
    
    def get_formatted_delivery_time(self):
        if self.delivery_time:
            date_str = self.delivery_time.strftime('%d %b %Y')
            time_range = self.get_time_slot_range()
            if time_range:
                return f"{date_str}, ({time_range})"
            return date_str
        return ""

    def __str__(self):
        if self.custom_meal:
            return f"CustomMeal ({self.custom_meal.category}) x {self.quantity} for Order #{self.order.id}"
        elif self.meals:
            return f"{self.meals.name} x {self.quantity} for Order #{self.order.id}"
        return f"Empty item for Order #{self.order.id}"

    class Meta:
        ordering = ['id']


class ComboOrderItem(models.Model):
    SUBSCRIPTION_PLAN = [
        ("WEEKLY", "Weekly Plan"),
        ("MONTHLY", "Monthly Plan"),
        ("YEARLY", "Yearly Plan")
    ]
    
    TIME_SLOT_RANGES = {
        "MORNING_BREAKFAST": ("07:00", "10:00"),
        "LUNCH": ("11:00", "14:30"),
        "EVENING_SNACK": ("15:00", "18:00"),
        "DINNER": ("18:30", "22:00"),
    }
    
    order = models.ForeignKey(Order, related_name='combo_items', on_delete=models.CASCADE)
    combo = models.ForeignKey(CustomMeal, on_delete=models.CASCADE)
    subscription_plan = models.CharField(max_length=20, choices=SUBSCRIPTION_PLAN)
    delivery_from_date = models.DateField()
    delivery_to_date = models.DateField()
    delivery_time = models.TimeField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    preferences = models.TextField(blank=True)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    combo_items_snapshot = models.JSONField(default=dict)
    
    def get_total_price(self):
        return self.price_snapshot * Decimal(self.quantity)
    
    def get_formatted_delivery_time(self):
        if self.delivery_time and self.delivery_from_date:
            date_str = self.delivery_from_date.strftime('%d %b %Y')
            time_str = self.delivery_time.strftime('%I:%M %p')
            return f"{date_str}, {time_str}"
        return ""
    
    def __str__(self):
        return f"Combo #{self.combo.combo_id} ({self.subscription_plan}) for Order #{self.order.id}"
    
    class Meta:
        ordering = ['delivery_from_date']


class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_subtotal(self):
        return sum(item.get_total_price() for item in self.cart_items.all())

    def get_tax(self):
        return self.get_subtotal() * Decimal(0.13)

    def get_delivery_charge(self):
        return Decimal(50.00)

    def get_total_price(self):
        return self.get_subtotal() + self.get_tax() + self.get_delivery_charge()

    def get_items_count(self):
        return self.cart_items.count()

    def clear(self):
        self.cart_items.all().delete()

    def __str__(self):
        return f"Cart for {self.user.first_name}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='cart_items', on_delete=models.CASCADE)
    custom_meal = models.ForeignKey(CustomMeal, on_delete=models.CASCADE, null=True, blank=True)
    meals = models.ForeignKey(Meals, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    is_combo = models.BooleanField(default=False, help_text="True for custom meals, False for regular meals")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'custom_meal'],
                condition=models.Q(is_combo=True),
                name='unique_cart_custom_meal'
            ),
            models.UniqueConstraint(
                fields=['cart', 'meals'],
                condition=models.Q(is_combo=False),
                name='unique_cart_meal'
            )
        ]

    def get_price_per_item(self):
        if self.is_combo and self.custom_meal:
            return self.custom_meal.get_total_price()
        elif not self.is_combo and self.meals:
            return self.meals.price
        return Decimal('0.00')

    def get_total_price(self):
        return self.get_price_per_item() * self.quantity

    def __str__(self):
        if self.is_combo and self.custom_meal:
            return f"Custom Meal ({self.custom_meal.category}) x {self.quantity}"
        elif not self.is_combo and self.meals:
            return f"{self.meals.name} x {self.quantity}"
        return f"Empty cart item"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.is_combo and not self.custom_meal:
            raise ValidationError("Combo items must have a custom_meal")
        if not self.is_combo and not self.meals:
            raise ValidationError("Non-combo items must have a meal")
        if self.custom_meal and self.meals:
            raise ValidationError("Item cannot have both custom_meal and meals")
