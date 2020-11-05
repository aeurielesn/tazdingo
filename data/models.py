from django.core.validators import int_list_validator
from django.db import models
from polymorphic.models import PolymorphicModel


class Shield(PolymorphicModel):
    name = models.CharField(max_length=255)
    user_id = models.IntegerField(primary_key=True)
    display_name = models.CharField(max_length=255)
    entered = models.DateTimeField()
    expires = models.DateTimeField()
    expired_notification = models.BooleanField(default=False)  # expired shield notification
    expiring_notification = models.BooleanField(default=False)  # shield is expiring soon (<1h)


class Reinforcement(PolymorphicModel):
    name = models.CharField(max_length=255)
    user_id = models.IntegerField(primary_key=True)
    display_name = models.CharField(max_length=255)
    entered = models.DateTimeField()


class Prey(models.Model):
    user_id = models.IntegerField()
    prey_name = models.CharField(max_length=255, primary_key=True)
    coords = models.CharField(max_length=255, null=True, validators=[int_list_validator])
    entered = models.DateTimeField()
    four_notification = models.BooleanField(default=False)
    eight_notification = models.BooleanField(default=False)
    twelve_notification = models.BooleanField(default=False)
    twenty_four_notification = models.BooleanField(default=False)
