from django.db import models
from khaja.models import Meals, Combo, CustomMeal
from django.contrib.auth.models import User

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
        ("COD", "Cash on Delivery")
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=255, choices=PAYMENT_METHOD, default='ESEWA')
    payment_status = models.BooleanField(default=False)
    delivery_address = models.TextField()
    delivery_time = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def calculate_pricing(self):
        """Calculate subtotal, tax, delivery charge and total"""
        self.subtotal = sum(item.get_total_price() for item in self.order_items.all())
        self.tax = self.subtotal * 0.13
        self.delivery_charge = 50.00 
        self.total_price = self.subtotal + self.tax + self.delivery_charge
        self.save()
        return self.total_price

    def __str__(self):
        return f"Order #{self.id} by {self.user.username if self.user else 'Guest'}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    custom_meal = models.ForeignKey(CustomMeal, on_delete=models.SET_NULL, null=True, blank=True)
    meal_type = models.CharField(max_length=20) 
    meal_category = models.CharField(max_length=50)  
    no_of_servings = models.PositiveIntegerField(default=1)
    preferences = models.TextField(blank=True)
    subscription_plan = models.CharField(max_length=20)
    delivery_time = models.DateTimeField(null=True, blank=True)
    price_per_serving = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1) 
    meal_items_snapshot = models.JSONField(default=dict)  

    def get_total_price(self):
        return self.price_per_serving * self.no_of_servings * self.quantity

    def __str__(self):
        return f"{self.meal_category} x {self.quantity} for Order #{self.order.id}"

    class Meta:
        ordering = ['id']


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_subtotal(self):
        return sum(item.get_total_price() for item in self.cart_items.all())

    def get_tax(self):
        return self.get_subtotal() * 0.13

    def get_delivery_charge(self):
        return 50.00

    def get_total_price(self):
        return self.get_subtotal() + self.get_tax() + self.get_delivery_charge()

    def get_items_count(self):
        return self.cart_items.count()

    def clear(self):
        self.cart_items.all().delete()

    def __str__(self):
        return f"Cart for {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='cart_items', on_delete=models.CASCADE)
    custom_meal = models.ForeignKey(CustomMeal, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = ['cart', 'custom_meal']

    def get_price_per_item(self):
        """Get price for one custom meal with all servings"""
        return self.custom_meal.get_total_price()

    def get_total_price(self):
        """Total price for this cart item (custom_meal price * quantity)"""
        return self.get_price_per_item() * self.quantity

    def __str__(self):
        return f"{self.custom_meal.category} x {self.quantity} in {self.cart.user.username}'s cart"