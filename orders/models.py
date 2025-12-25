# orders/models.py
from django.db import models
from khaja.models import Meals, Combo, CustomMeal, DeliveryTimeSlot
from users.models import CustomUser
from decimal import Decimal
from datetime import datetime
import uuid

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

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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

    def calculate_pricing(self):
        subtotal = sum(item.get_total_price() for item in self.combo_items.all())
        subtotal += sum(item.get_total_price() for item in self.order_items.all())

        
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
        return f"Order #{self.uuid} by {self.user.first_name if self.user.user_type == "INDIVIDUALS" else self.user.organization_name}"


class OrderItem(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)   
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    meals = models.ForeignKey(Meals, on_delete=models.CASCADE, null=True, blank=True)
    meal_type = models.CharField(max_length=20)
    meal_category = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)

    def get_price_per_item(self):
        return self.meals.price

    def get_total_price(self):
        return self.get_price_per_item() * Decimal(self.quantity)
    

    def __str__(self):
        return f"{self.meals.name} x {self.quantity} for Order #{self.order.uuid}"


    class Meta:
        ordering = ['uuid']


class ComboOrderItem(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)   
    order = models.ForeignKey(Order, related_name='combo_items', on_delete=models.CASCADE)
    combo = models.ForeignKey(CustomMeal, on_delete=models.CASCADE)
    delivery_from_date = models.DateField()
    delivery_to_date = models.DateField()
    delivery_time_slot = models.ForeignKey(DeliveryTimeSlot, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    preferences = models.TextField(blank=True)
    price_snapshot = models.DecimalField(max_digits=10,decimal_places=2,default=0)

    
    def get_total_price(self):
        return self.price_snapshot * Decimal(self.quantity)
    
    def __str__(self):
        return f"Combo #{self.combo.combo_id} ({self.subscription_plan}) for Order #{self.order.uuid}"
    
    class Meta:
        ordering = ['delivery_from_date']


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default= uuid.uuid4, editable=False)
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
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']

    def get_price_per_item(self):
        if self.custom_meal:
            return self.custom_meal.get_total_price()
        elif  self.meals:
            return self.meals.price
        return Decimal('0.00')

    def get_total_price(self):
        return self.get_price_per_item() * self.quantity

    def __str__(self):
        if self.custom_meal:
            return f"Custom Meal ({self.custom_meal.meal_category}) x {self.quantity}"
        elif self.meals:
            return f"{self.meals.name} x {self.quantity}"
        return f"Empty cart item"

