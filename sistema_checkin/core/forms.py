from django import forms
from .models import Participante

class ParticipanteForm(forms.ModelForm):
    class Meta:
        model = Participante
        fields = ['nome', 'matricula', 'email']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500'}),
            'matricula': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500'}),
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500'}),
        }
        labels = {
            'nome': 'Nome Completo',
            'matricula': 'CPF',
            'email': 'E-mail',
        }

    def clean_matricula(self):
        matricula = self.cleaned_data.get('matricula')
        if Participante.objects.filter(matricula=matricula).exists():
            raise forms.ValidationError("Já existe um participante com esta matrícula.")
        return matricula

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Participante.objects.filter(email=email).exists():
            raise forms.ValidationError("Já existe um participante com este e-mail.")
        return email