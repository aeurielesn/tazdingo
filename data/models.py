from django.db import models
from polymorphic.models import PolymorphicModel
from collections import namedtuple


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
