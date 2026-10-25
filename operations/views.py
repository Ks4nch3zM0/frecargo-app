from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AssignmentForm, CustomerForm, ShipmentForm, StatusForm
from .models import Customer, Shipment
from .services import (allowed_transitions, assign_courier, change_status, create_shipment,
    edit_shipment, require_dispatcher, visible_shipments)


@login_required
def dashboard(request):
    shipments = visible_shipments(request.user)
    counts = shipments.aggregate(
        total=Count("pk"),
        pending=Count("pk", filter=Q(status__in=["received", "assigned"])),
        in_transit=Count("pk", filter=Q(status="in_transit")),
        delivered=Count("pk", filter=Q(status="delivered")),
        incidents=Count("pk", filter=Q(status="incident")),
    )
    return render(request, "operations/dashboard.html", {"counts": counts, "shipments": shipments[:8]})


@login_required
def shipment_list(request):
    shipments = visible_shipments(request.user)
    query = request.GET.get("q", "").strip()[:200]
    status = request.GET.get("status", "")
    if query:
        shipments = shipments.filter(Q(tracking_code__icontains=query) | Q(external_reference__icontains=query) |
            Q(recipient_name__icontains=query) | Q(customer__name__icontains=query) | Q(delivery_address__icontains=query))
    if status in Shipment.Status.values:
        shipments = shipments.filter(status=status)
    else:
        status = ""
    page = Paginator(shipments, 25).get_page(request.GET.get("page"))
    return render(request, "operations/shipment_list.html", {"page": page, "shipments": page, "query": query, "status": status, "statuses": Shipment.Status.choices})


@login_required
def shipment_create(request):
    require_dispatcher(request.user)
    form = ShipmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            shipment = create_shipment(actor=request.user, data=form.cleaned_data)
        except ValidationError as error:
            for message in error.messages:
                form.add_error(None, message)
        else:
            messages.success(request, "Envío registrado. Ya puedes asignarlo a un mensajero.")
            return redirect("shipment_detail", pk=shipment.pk)
    return render(request, "operations/shipment_form.html", {"form": form, "title": "Registrar envío", "has_customers": Customer.objects.filter(active=True).exists()})


@login_required
def shipment_edit(request, pk):
    require_dispatcher(request.user)
    shipment = get_object_or_404(visible_shipments(request.user), pk=pk)
    if shipment.is_closed:
        messages.error(request, "Este envío está cerrado; sus datos están disponibles para consulta.")
        return redirect("shipment_detail", pk=pk)
    form = ShipmentForm(request.POST or None, instance=shipment)
    if request.method == "POST" and form.is_valid():
        try:
            edit_shipment(shipment_id=pk, actor=request.user, data=form.cleaned_data, expected_version=form.cleaned_data["version"])
        except ValidationError as error:
            for message in error.messages:
                form.add_error(None, message)
        else:
            messages.success(request, "Datos actualizados. La corrección quedó registrada en el historial.")
            return redirect("shipment_detail", pk=pk)
    return render(request, "operations/shipment_form.html", {"form": form, "shipment": shipment, "title": "Editar envío", "has_customers": True})


@login_required
def shipment_detail(request, pk):
    shipment = get_object_or_404(visible_shipments(request.user), pk=pk)
    choices = allowed_transitions(shipment, request.user)
    return render(request, "operations/shipment_detail.html", {
        "shipment": shipment,
        "events": shipment.events.select_related("actor").all(),
        "status_form": StatusForm(choices=choices, initial={"version": shipment.version}),
        "assignment_form": AssignmentForm(initial={"version": shipment.version, "courier": shipment.courier_id}) if request.user.can_dispatch else None,
        "can_change_status": bool(choices),
    })


def show_form_errors(request, form):
    for field, errors in form.errors.items():
        for error in errors:
            label = (form.fields[field].label or field) if field in form.fields else "Formulario"
            messages.error(request, f"{label}: {error}")


@login_required
@require_POST
def shipment_assign(request, pk):
    require_dispatcher(request.user)
    get_object_or_404(visible_shipments(request.user), pk=pk)
    form = AssignmentForm(request.POST)
    if form.is_valid():
        try:
            assign_courier(shipment_id=pk, actor=request.user, courier_id=form.cleaned_data["courier"].pk, expected_version=form.cleaned_data["version"])
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "Asignación guardada.")
    else:
        show_form_errors(request, form)
    return redirect("shipment_detail", pk=pk)


@login_required
@require_POST
def shipment_status(request, pk):
    shipment = get_object_or_404(visible_shipments(request.user), pk=pk)
    form = StatusForm(request.POST, choices=allowed_transitions(shipment, request.user))
    if form.is_valid():
        try:
            change_status(shipment_id=pk, actor=request.user, new_status=form.cleaned_data["status"], expected_version=form.cleaned_data["version"], note=form.cleaned_data["note"], received_by=form.cleaned_data["received_by"])
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "Estado actualizado.")
    else:
        show_form_errors(request, form)
    return redirect("shipment_detail", pk=pk)


@login_required
def customer_list(request):
    require_dispatcher(request.user)
    query = request.GET.get("q", "").strip()[:200]
    customers = Customer.objects.all()
    if query:
        customers = customers.filter(Q(name__icontains=query) | Q(phone__icontains=query))
    page = Paginator(customers, 25).get_page(request.GET.get("page"))
    return render(request, "operations/customer_list.html", {"page": page, "query": query})


@login_required
def customer_form(request, pk=None):
    require_dispatcher(request.user)
    customer = get_object_or_404(Customer, pk=pk) if pk else None
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cliente guardado.")
        return redirect("customer_list")
    return render(request, "operations/customer_form.html", {"form": form, "title": "Editar cliente" if customer else "Registrar cliente"})
