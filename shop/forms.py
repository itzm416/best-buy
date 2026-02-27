from django import forms
from .models import CustomerInformation

class CustomerInformationForm(forms.ModelForm):
    class Meta:
        model = CustomerInformation
        fields = [
            'name',
            'mobile_number',
            'locality',
            'city',
            'zipcode',
            'state'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter full name'
            }),
            'mobile_number': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter mobile number'
            }),
            'locality': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'House No, Street, Area'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter city'
            }),
            'zipcode': forms.NumberInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter ZIP / Pincode'
            }),
            'state': forms.Select(attrs={
                'class': 'form-select rounded-3'
            }),
        }

        labels = {
            'name': 'Full Name',
            'mobile_number': 'Mobile Number',
            'locality': 'Address / Locality',
            'city': 'City',
            'zipcode': 'Pincode',
            'state': 'State',
        }