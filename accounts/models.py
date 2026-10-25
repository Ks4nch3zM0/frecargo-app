from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        COORDINATOR = "coordinator", "Coordinación"
        COURIER = "courier", "Mensajero"

    role = models.CharField("rol", max_length=20, choices=Role.choices, default=Role.COURIER)
    phone = models.CharField("teléfono", max_length=25, blank=True)

    @property
    def can_dispatch(self):
        return self.is_active and (self.is_superuser or self.role == self.Role.COORDINATOR)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return self.display_name
