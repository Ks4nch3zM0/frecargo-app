from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from .models import Customer, Shipment, ShipmentEvent
from .services import assign_courier, change_status, create_shipment, edit_shipment

User = get_user_model()


def fixtures():
    dispatcher = User.objects.create_user(username="coord", password="Local-test-only!123", role="coordinator")
    first = User.objects.create_user(username="courier1", password="Local-test-only!123")
    second = User.objects.create_user(username="courier2", password="Local-test-only!123")
    customer = Customer.objects.create(name="Cliente de prueba", phone="3000000000", pickup_address="Recogida de prueba")
    return dispatcher, first, second, customer


def payload(customer):
    return {"customer": customer, "recipient_name": "Destinatario de prueba", "recipient_phone": "3000000000",
        "pickup_address": "Origen de prueba", "delivery_address": "Destino de prueba", "city": "Bogotá",
        "description": "Paquete de prueba", "service_fee": Decimal("15000.50")}


class ShipmentFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dispatcher, cls.courier, cls.other, cls.customer = fixtures()

    def new_shipment(self):
        return create_shipment(actor=self.dispatcher, data=payload(self.customer))

    def assigned_shipment(self):
        shipment = self.new_shipment()
        return assign_courier(shipment_id=shipment.pk, actor=self.dispatcher, courier_id=self.courier.pk, expected_version=1)

    def in_transit(self):
        shipment = self.assigned_shipment()
        return change_status(shipment_id=shipment.pk, actor=self.courier, new_status="in_transit", expected_version=shipment.version)

    def test_delivery_records_who_received_actor_and_time(self):
        shipment = self.in_transit()
        result = change_status(shipment_id=shipment.pk, actor=self.courier, new_status="delivered", expected_version=shipment.version, received_by="Persona de prueba")
        self.assertEqual(result.status, "delivered")
        self.assertEqual(result.received_by, "Persona de prueba")
        self.assertIsNotNone(result.delivered_at)
        self.assertEqual(result.events.count(), 4)
        latest = result.events.first()
        self.assertEqual(latest.actor, self.courier)
        self.assertIn("Persona de prueba", latest.note)

    def test_cannot_complete_delivery_without_recipient(self):
        shipment = self.in_transit()
        with self.assertRaises(ValidationError):
            change_status(shipment_id=shipment.pk, actor=self.courier, new_status="delivered", expected_version=shipment.version)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, "in_transit")
        self.assertEqual(shipment.events.count(), 3)

    def test_incident_requires_a_reason(self):
        shipment = self.in_transit()
        with self.assertRaises(ValidationError):
            change_status(shipment_id=shipment.pk, actor=self.courier, new_status="incident", expected_version=shipment.version, note="   ")

    def test_invalid_status_jump_is_rejected(self):
        shipment = self.new_shipment()
        with self.assertRaises(ValidationError):
            change_status(shipment_id=shipment.pk, actor=self.dispatcher, new_status="delivered", expected_version=1, received_by="Persona")

    def test_stale_form_does_not_overwrite_assignment(self):
        shipment = self.assigned_shipment()
        with self.assertRaises(ValidationError):
            assign_courier(shipment_id=shipment.pk, actor=self.dispatcher, courier_id=self.other.pk, expected_version=1)
        shipment.refresh_from_db()
        self.assertEqual(shipment.courier, self.courier)
        self.assertEqual(shipment.events.count(), 2)

    def test_stale_edit_does_not_overwrite_address(self):
        shipment = self.assigned_shipment()
        with self.assertRaises(ValidationError):
            edit_shipment(shipment_id=shipment.pk, actor=self.dispatcher, expected_version=1, data={"delivery_address": "Dirección antigua"})
        shipment.refresh_from_db()
        self.assertEqual(shipment.delivery_address, "Destino de prueba")

    def test_edit_preserves_before_after_history(self):
        shipment = self.new_shipment()
        result = edit_shipment(shipment_id=shipment.pk, actor=self.dispatcher, expected_version=1, data={"delivery_address": "Dirección corregida"})
        event = result.events.first()
        self.assertEqual(event.changes["dirección de entrega"], {"antes": "Destino de prueba", "después": "Dirección corregida"})

    def test_status_and_audit_are_atomic(self):
        shipment = self.assigned_shipment()
        with patch("operations.services.record_event", side_effect=RuntimeError("test rollback")):
            with self.assertRaises(RuntimeError):
                change_status(shipment_id=shipment.pk, actor=self.courier, new_status="in_transit", expected_version=shipment.version)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, "assigned")
        self.assertEqual(shipment.version, 2)
        self.assertEqual(shipment.events.count(), 2)

    def test_closed_shipment_cannot_be_reassigned_or_edited(self):
        shipment = self.new_shipment()
        shipment = change_status(shipment_id=shipment.pk, actor=self.dispatcher, new_status="cancelled", expected_version=1, note="Cancelado por el cliente")
        with self.assertRaises(ValidationError):
            assign_courier(shipment_id=shipment.pk, actor=self.dispatcher, courier_id=self.courier.pk, expected_version=shipment.version)
        with self.assertRaises(ValidationError):
            edit_shipment(shipment_id=shipment.pk, actor=self.dispatcher, expected_version=shipment.version, data={"description": "cambio"})

    def test_assignment_only_accepts_active_couriers(self):
        shipment = self.new_shipment()
        self.other.is_active = False
        self.other.save()
        for user in [self.other, self.dispatcher]:
            with self.subTest(user=user.username), self.assertRaises(ValidationError):
                assign_courier(shipment_id=shipment.pk, actor=self.dispatcher, courier_id=user.pk, expected_version=1)

    def test_negative_fee_and_inactive_customer_are_rejected(self):
        data = payload(self.customer)
        data["service_fee"] = -1
        with self.assertRaises(ValidationError):
            create_shipment(actor=self.dispatcher, data=data)
        self.customer.active = False
        self.customer.save()
        with self.assertRaises(ValidationError):
            self.new_shipment()

    def test_creation_ignores_forged_status_and_owner(self):
        data = payload(self.customer) | {"status": "delivered", "created_by": self.other, "courier": self.other}
        shipment = create_shipment(actor=self.dispatcher, data=data)
        self.assertEqual(shipment.status, "received")
        self.assertEqual(shipment.created_by, self.dispatcher)
        self.assertIsNone(shipment.courier)

    def test_courier_cannot_create_or_change_someone_elses_shipment(self):
        shipment = self.assigned_shipment()
        with self.assertRaises(PermissionDenied):
            create_shipment(actor=self.courier, data=payload(self.customer))
        with self.assertRaises(PermissionDenied):
            change_status(shipment_id=shipment.pk, actor=self.other, new_status="in_transit", expected_version=shipment.version)

    def test_reassignment_immediately_revokes_previous_courier_access(self):
        shipment = self.assigned_shipment()
        shipment = assign_courier(shipment_id=shipment.pk, actor=self.dispatcher, courier_id=self.other.pk, expected_version=shipment.version)
        with self.assertRaises(PermissionDenied):
            change_status(shipment_id=shipment.pk, actor=self.courier, new_status="in_transit", expected_version=shipment.version)

    def test_demo_seed_refuses_normal_settings(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo")


class AccessAndWebTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dispatcher, cls.courier, cls.other, cls.customer = fixtures()
        cls.mine = create_shipment(actor=cls.dispatcher, data=payload(cls.customer))
        cls.mine = assign_courier(shipment_id=cls.mine.pk, actor=cls.dispatcher, courier_id=cls.courier.pk, expected_version=1)
        cls.theirs = create_shipment(actor=cls.dispatcher, data=payload(cls.customer))
        cls.theirs = assign_courier(shipment_id=cls.theirs.pk, actor=cls.dispatcher, courier_id=cls.other.pk, expected_version=1)

    def test_pages_require_login(self):
        for name in ["dashboard", "shipment_list", "customer_list"]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn("/cuenta/entrar/", response.url)

    def test_courier_list_and_totals_only_include_own_work(self):
        self.client.force_login(self.courier)
        response = self.client.get(reverse("shipment_list"))
        self.assertContains(response, self.mine.tracking_code)
        self.assertNotContains(response, self.theirs.tracking_code)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["counts"]["total"], 1)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_unassigned_record_detail_and_mutation_are_hidden(self):
        self.client.force_login(self.courier)
        self.assertEqual(self.client.get(reverse("shipment_detail", args=[self.theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("shipment_status", args=[self.theirs.pk]), {"status": "in_transit", "version": 2}).status_code, 404)

    def test_courier_cannot_access_dispatcher_actions(self):
        self.client.force_login(self.courier)
        for name in ["customer_list", "customer_create", "shipment_create"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.assertEqual(self.client.get(reverse("shipment_edit", args=[self.mine.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("shipment_assign", args=[self.mine.pk]), {"courier": self.other.pk, "version": 2}).status_code, 403)

    def test_csrf_protects_mutations(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.courier)
        response = browser.post(reverse("shipment_status", args=[self.mine.pk]), {"status": "in_transit", "version": 2})
        self.assertEqual(response.status_code, 403)
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.status, "assigned")

    def test_post_updates_state_for_assigned_courier(self):
        self.client.force_login(self.courier)
        response = self.client.post(reverse("shipment_status", args=[self.mine.pk]), {"status": "in_transit", "version": 2}, follow=True)
        self.assertContains(response, "Estado actualizado.")
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.status, "in_transit")

    def test_dispatcher_can_create_via_form(self):
        self.client.force_login(self.dispatcher)
        data = payload(self.customer) | {"customer": self.customer.pk, "notes": "", "external_reference": "WEB-123", "neighborhood": ""}
        response = self.client.post(reverse("shipment_create"), data, follow=True)
        self.assertContains(response, "Envío registrado.")
        self.assertEqual(Shipment.objects.get(external_reference="WEB-123").events.count(), 1)

    def test_search_and_status_filters_combine(self):
        self.client.force_login(self.dispatcher)
        response = self.client.get(reverse("shipment_list"), {"q": self.mine.tracking_code, "status": "assigned"})
        self.assertEqual(response.context["page"].paginator.count, 1)
        response = self.client.get(reverse("shipment_list"), {"q": self.mine.tracking_code, "status": "delivered"})
        self.assertEqual(response.context["page"].paginator.count, 0)

    def test_stored_html_is_escaped(self):
        self.mine.notes = '<script>alert("unsafe")</script>'
        self.mine.save()
        self.client.force_login(self.courier)
        response = self.client.get(reverse("shipment_detail", args=[self.mine.pk]))
        self.assertNotContains(response, self.mine.notes)
        self.assertContains(response, "&lt;script&gt;")

    def test_inactive_user_cannot_login(self):
        self.courier.is_active = False
        self.courier.save()
        self.assertFalse(self.client.login(username="courier1", password="Local-test-only!123"))

    def test_admin_cannot_bypass_shipment_history(self):
        admin = User.objects.create_superuser(username="root_test", password="Local-test-only!123")
        self.client.force_login(admin)
        response = self.client.post(reverse("admin:operations_shipment_change", args=[self.mine.pk]), {"status": "delivered"})
        self.assertEqual(response.status_code, 403)

    def test_state_endpoints_reject_get(self):
        self.client.force_login(self.dispatcher)
        self.assertEqual(self.client.get(reverse("shipment_assign", args=[self.mine.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("shipment_status", args=[self.mine.pk])).status_code, 405)


class ConcurrentUpdateTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_only_one_concurrent_update_is_accepted(self):
        dispatcher, courier, other, customer = fixtures()
        shipment = create_shipment(actor=dispatcher, data=payload(customer))
        shipment = assign_courier(shipment_id=shipment.pk, actor=dispatcher, courier_id=courier.pk, expected_version=1)
        barrier = Barrier(2)

        def update():
            close_old_connections()
            try:
                actor = User.objects.get(pk=courier.pk)
                barrier.wait(timeout=15)
                change_status(shipment_id=shipment.pk, actor=actor, new_status="in_transit", expected_version=2)
                return "saved"
            except ValidationError:
                return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: update(), range(2)))
        self.assertCountEqual(results, ["saved", "conflict"])
        shipment.refresh_from_db()
        self.assertEqual(shipment.version, 3)
        self.assertEqual(ShipmentEvent.objects.filter(shipment=shipment).count(), 3)
