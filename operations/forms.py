from django import forms
from django.db.models import Q
from accounts.models import User
from .models import Customer, Shipment
from .services import EDITABLE_FIELDS


class StyledMixin:
    def style_fields(self):
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = "field-input"


class CustomerForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("name", "phone", "email", "pickup_address", "active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class ShipmentForm(StyledMixin, forms.ModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Shipment
        fields = EDITABLE_FIELDS
        widgets = {"notes": forms.Textarea(attrs={"rows": 3}), "service_fee": forms.NumberInput(attrs={"min": "0", "step": "0.01"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_customer = self.instance.customer_id if not self.instance._state.adding else None
        self.fields["customer"].queryset = Customer.objects.filter(Q(active=True) | Q(pk=current_customer))
        self.fields["customer"].empty_label = "Seleccionar cliente"
        if not self.instance._state.adding:
            self.fields["version"].required = True
            self.fields["version"].initial = self.instance.version
        self.style_fields()


class AssignmentForm(StyledMixin, forms.Form):
    courier = forms.ModelChoiceField(label="Mensajero", queryset=User.objects.none(), empty_label="Seleccionar mensajero")
    version = forms.IntegerField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["courier"].queryset = User.objects.filter(role=User.Role.COURIER, is_active=True, is_superuser=False).order_by("first_name", "username")
        self.style_fields()


class StatusForm(StyledMixin, forms.Form):
    status = forms.ChoiceField(label="Nuevo estado")
    received_by = forms.CharField(label="Nombre de quien recibe", max_length=150, required=False, help_text="Obligatorio al marcar como entregado.")
    note = forms.CharField(label="Observación", max_length=2000, required=False, widget=forms.Textarea(attrs={"rows": 3}), help_text="Indica el motivo si hay novedad, devolución o cancelación.")
    version = forms.IntegerField(widget=forms.HiddenInput)

    def __init__(self, *args, choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = choices
        self.style_fields()
