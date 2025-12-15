from django.db import models
from users.models import CustomUser
from khaja.models import Meals, CustomMeal


class Notification(models.Model):
    nid = models.AutoField(primary_key=True)
    notification = models.TextField()   
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.notification