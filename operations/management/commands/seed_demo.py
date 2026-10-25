import secrets
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from accounts.models import User
from operations.models import Customer, Shipment
from operations.services import assign_courier, change_status, create_shipment


class Command(BaseCommand):
    help = "Crea datos ficticios y claves aleatorias únicamente en settings_demo."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Usa --settings=config.settings_demo. No se cargan datos de ejemplo en MySQL.")
        accounts = {}
        for username, first_name, superuser in [("admin_demo", "Coordinación demo", True), ("mensajero_demo", "Mensajero demo", False)]:
            user, created = User.objects.get_or_create(username=username, defaults={"first_name": first_name, "is_superuser": superuser, "is_staff": superuser})
            if created:
                password = secrets.token_urlsafe(15)
                user.set_password(password)
                user.save()
                self.stdout.write(f"{username}: {password}")
            else:
                self.stdout.write(f"{username}: cuenta existente, contraseña conservada.")
            accounts[username] = user
        admin, courier = accounts["admin_demo"], accounts["mensajero_demo"]
        if Shipment.objects.exists():
            self.stdout.write("Los envíos demo ya existen; no se duplicaron.")
            return
        customer = Customer.objects.create(name="Tienda de ejemplo · DEMO", phone="3000000000", pickup_address="Calle 26 # 30-10 · dirección de ejemplo")
        scenarios = [
            ("Destino demo 01", "Chapinero", "Carrera 13 # 60-20", "delivered"),
            ("Destino demo 02", "Suba", "Calle 145 # 101-15", "assigned"),
            ("Destino demo 03", "Kennedy", "Carrera 78 # 38-10 Sur", "received"),
            ("Destino demo 04", "Teusaquillo", "Calle 45 # 24-30", "incident"),
            ("Destino demo 05", "Engativá", "Carrera 90 # 80-15", "in_transit"),
            ("Destino demo 06", "Usaquén", "Calle 116 # 15-40", "in_transit"),
        ]
        for name, neighborhood, address, final in scenarios:
            shipment = create_shipment(actor=admin, data={"customer": customer, "recipient_name": name, "recipient_phone": "3000000000", "pickup_address": customer.pickup_address, "delivery_address": address + " · ejemplo", "city": "Bogotá", "neighborhood": neighborhood, "description": "Paquete ficticio de demostración", "service_fee": "12000.00", "external_reference": "DEMO-" + neighborhood.upper(), "notes": "Datos ficticios. No realizar entregas."})
            if final == "received":
                continue
            shipment = assign_courier(shipment_id=shipment.pk, actor=admin, courier_id=courier.pk, expected_version=shipment.version)
            if final == "assigned":
                continue
            shipment = change_status(shipment_id=shipment.pk, actor=courier, new_status="in_transit", expected_version=shipment.version)
            if final in {"delivered", "incident"}:
                change_status(shipment_id=shipment.pk, actor=courier, new_status=final, expected_version=shipment.version,
                    received_by="Persona demo" if final == "delivered" else "", note="Entrega de ejemplo." if final == "delivered" else "Ejemplo: destinatario ausente. Pendiente de coordinación.")
        self.stdout.write(self.style.SUCCESS("Demo creada con 6 envíos ficticios. Conserva las claves mostradas para entrar."))
