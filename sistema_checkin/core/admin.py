from django.contrib import admin
from .models import Participante, Evento, Inscricao

@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'matricula', 'email')
    search_fields = ('nome', 'matricula')

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data')

@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ('participante', 'evento', 'status', 'data_checkin')
    list_filter = ('evento', 'status')
    search_fields = ('participante__nome', 'participante__matricula')
