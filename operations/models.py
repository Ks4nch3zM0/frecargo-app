import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

phone_validator = RegexValidator(r"^\+?[0-9 ()-]{7,25}$", "Escribe un teléfono válido, con 7 a 25 caracteres.")


def tracking_code():
    return "FC-" + uuid.uuid4().hex[:16].upper()


class Customer(models.Model):
    name = models.CharField("cliente o empresa", max_length=150)
    phone = models.CharField("teléfono", max_length=25, validators=[phone_validator])
    email = models.EmailField("correo", blank=True)
    pickup_address = models.CharField("dirección de recogida", max_length=255)
    active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return self.name


class Shipment(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Recibido"
        ASSIGNED = "assigned", "Asignado"
        IN_TRANSIT = "in_transit", "En ruta"
        DELIVERED = "delivered", "Entregado"
        INCIDENT = "incident", "Novedad"
        RETURNED = "returned", "Devuelto"
        CANCELLED = "cancelled", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_code = models.CharField("guía FRECARGO", max_length=24, unique=True, default=tracking_code, editable=False)
    external_reference = models.CharField("referencia del cliente", max_length=100, blank=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name="cliente")
    recipient_name = models.CharField("destinatario", max_length=150)
    recipient_phone = models.CharField("teléfono del destinatario", max_length=25, validators=[phone_validator])
    pickup_address = models.CharField("dirección de recogida", max_length=255)
    delivery_address = models.CharField("dirección de entrega", max_length=255)
    city = models.CharField("ciudad o municipio", max_length=100, default="Bogotá")
    neighborhood = models.CharField("barrio o localidad", max_length=100, blank=True)
    description = models.CharField("contenido o descripción del paquete", max_length=255)
    service_fee = models.DecimalField("tarifa del envío (COP)", max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0"))])
    notes = models.TextField("instrucciones de entrega", max_length=2000, blank=True)
    status = models.CharField("estado", max_length=20, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    courier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_shipments", verbose_name="mensajero")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_shipments")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    received_by = models.CharField("recibido por", max_length=150, blank=True)
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "envío"
        verbose_name_plural = "envíos"
        constraints = [models.CheckConstraint(condition=models.Q(service_fee__gte=0), name="shipment_fee_nonnegative")]
        indexes = [models.Index(fields=("courier", "status"))]

    @property
    def is_closed(self):
        return self.status in {self.Status.DELIVERED, self.Status.RETURNED, self.Status.CANCELLED}

    def __str__(self):
        return self.tracking_code


class ShipmentEvent(models.Model):
    class Kind(models.TextChoices):
        CREATED = "created", "Registro"
        ASSIGNED = "assigned", "Asignación"
        STATUS = "status", "Cambio de estado"
        EDITED = "edited", "Corrección de datos"

    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    from_status = models.CharField(max_length=20, blank=True, choices=Shipment.Status.choices)
    to_status = models.CharField(max_length=20, choices=Shipment.Status.choices)
    note = models.TextField(blank=True)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        verbose_name = "movimiento"
        verbose_name_plural = "historial de movimientos"
