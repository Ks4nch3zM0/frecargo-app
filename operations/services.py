"""Las mutaciones de envíos y su historial comparten una transacción."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from .models import Shipment, ShipmentEvent

S = Shipment.Status
TRANSITIONS = {
    S.RECEIVED: {S.CANCELLED},
    S.ASSIGNED: {S.IN_TRANSIT, S.INCIDENT, S.CANCELLED},
    S.IN_TRANSIT: {S.DELIVERED, S.INCIDENT, S.RETURNED},
    S.INCIDENT: {S.IN_TRANSIT, S.RETURNED, S.CANCELLED},
    S.DELIVERED: set(), S.RETURNED: set(), S.CANCELLED: set(),
}
EDITABLE_FIELDS = (
    "customer", "external_reference", "recipient_name", "recipient_phone",
    "pickup_address", "delivery_address", "city", "neighborhood",
    "description", "service_fee", "notes",
)


def require_dispatcher(user):
    if not user.is_authenticated or not user.can_dispatch:
        raise PermissionDenied


def visible_shipments(user):
    if not user.is_authenticated or not user.is_active:
        return Shipment.objects.none()
    base = Shipment.objects.select_related("customer", "courier")
    return base if user.can_dispatch else base.filter(courier=user)


def allowed_transitions(shipment, user):
    if not user.is_active or (not user.can_dispatch and shipment.courier_id != user.pk):
        return []
    allowed = TRANSITIONS.get(shipment.status, set()).copy()
    if not user.can_dispatch:
        allowed.discard(S.CANCELLED)
    return [(value, label) for value, label in S.choices if value in allowed]


def check_version(shipment, expected_version):
    if shipment.version != expected_version:
        raise ValidationError("Otra persona ya actualizó este envío. Recarga la página para ver los cambios antes de guardar.")


def record_event(shipment, actor, kind, old_status="", note="", changes=None):
    ShipmentEvent.objects.create(shipment=shipment, actor=actor, kind=kind,
        from_status=old_status, to_status=shipment.status, note=note, changes=changes or {})


@transaction.atomic
def create_shipment(*, actor, data):
    require_dispatcher(actor)
    values = {key: data[key] for key in EDITABLE_FIELDS if key in data}
    shipment = Shipment(created_by=actor, **values)
    if not shipment.customer.active:
        raise ValidationError("El cliente está inactivo.")
    shipment.full_clean()
    shipment.save()
    record_event(shipment, actor, ShipmentEvent.Kind.CREATED, note="Envío registrado en FRECARGO.")
    return shipment


@transaction.atomic
def edit_shipment(*, shipment_id, actor, data, expected_version):
    require_dispatcher(actor)
    shipment = Shipment.objects.select_for_update().get(pk=shipment_id)
    check_version(shipment, expected_version)
    if shipment.is_closed:
        raise ValidationError("Este envío ya está cerrado; sus datos se conservan para consulta.")
    changes = {}
    for key in EDITABLE_FIELDS:
        if key not in data:
            continue
        old, new = getattr(shipment, key), data[key]
        if old != new:
            if key == "customer" and not new.active:
                raise ValidationError("El cliente seleccionado está inactivo.")
            changes[str(shipment._meta.get_field(key).verbose_name)] = {"antes": str(old), "después": str(new)}
            setattr(shipment, key, new)
    if not changes:
        return shipment
    shipment.version += 1
    shipment.full_clean()
    shipment.save()
    record_event(shipment, actor, ShipmentEvent.Kind.EDITED, shipment.status, "Datos del envío corregidos.", changes)
    return shipment


@transaction.atomic
def assign_courier(*, shipment_id, actor, courier_id, expected_version):
    require_dispatcher(actor)
    shipment = Shipment.objects.select_for_update().get(pk=shipment_id)
    check_version(shipment, expected_version)
    if shipment.is_closed:
        raise ValidationError("No se puede asignar un envío cerrado.")
    courier = User.objects.filter(pk=courier_id, role=User.Role.COURIER, is_active=True, is_superuser=False).first()
    if not courier:
        raise ValidationError("Selecciona un mensajero activo.")
    if shipment.courier_id == courier.pk:
        raise ValidationError("Este mensajero ya tiene asignado el envío.")
    old_status = shipment.status
    previous = str(shipment.courier) if shipment.courier_id else "Sin asignar"
    shipment.courier = courier
    if shipment.status == S.RECEIVED:
        shipment.status = S.ASSIGNED
    shipment.version += 1
    shipment.save(update_fields=("courier", "status", "version", "updated_at"))
    record_event(shipment, actor, ShipmentEvent.Kind.ASSIGNED, old_status,
        f"{previous} → {courier.display_name}.")
    return shipment


@transaction.atomic
def change_status(*, shipment_id, actor, new_status, expected_version, note="", received_by=""):
    shipment = Shipment.objects.select_for_update().get(pk=shipment_id)
    if not actor.is_active or (not actor.can_dispatch and shipment.courier_id != actor.pk):
        raise PermissionDenied
    check_version(shipment, expected_version)
    allowed = dict(allowed_transitions(shipment, actor))
    if new_status not in allowed:
        raise ValidationError("Ese cambio de estado no está permitido.")
    note = note.strip()
    received_by = received_by.strip()
    if new_status in {S.INCIDENT, S.RETURNED, S.CANCELLED} and not note:
        raise ValidationError("Describe el motivo de la novedad, devolución o cancelación.")
    if new_status == S.DELIVERED and not received_by:
        raise ValidationError("Indica el nombre de quien recibió el paquete.")
    if len(note) > 2000 or len(received_by) > 150:
        raise ValidationError("La observación o el nombre supera la longitud permitida.")
    old_status = shipment.status
    shipment.status = new_status
    shipment.version += 1
    if new_status == S.DELIVERED:
        shipment.delivered_at = timezone.now()
        shipment.received_by = received_by
        note = f"Recibió: {received_by}. {note}".strip()
    shipment.save(update_fields=("status", "version", "updated_at", "delivered_at", "received_by"))
    record_event(shipment, actor, ShipmentEvent.Kind.STATUS, old_status, note)
    return shipment
