from django.urls import path
from . import views

urlpatterns = [
    # --- ROTAS DE GESTÃO GERAL ---
    path('cadastro-geral/', views.cadastro_geral, name='cadastro_geral'),
    path('participantes/', views.lista_geral_participantes, name='lista_geral_participantes'),
    
    # --- ROTAS DE EVENTOS ---
    path('', views.lista_eventos, name='lista_eventos'),
    path('evento/<int:evento_id>/', views.detalhe_evento, name='detalhe_evento'),
    path('evento/<int:evento_id>/inscrever_csv/', views.inscrever_via_csv, name='inscrever_via_csv'),
    path('evento/<int:evento_id>/checkin/', views.pagina_checkin, name='pagina_checkin'),
    
    # --- ROTAS DE API E AÇÕES ---
    path('api/checkin/<int:evento_id>/', views.api_checkin, name='api_checkin'),
    path('inscricao/<int:inscricao_id>/promover/', views.promover_participante, name='promover_participante'),
    path('evento/<int:evento_id>/exportar_csv/', views.exportar_presenca_csv, name='exportar_presenca_csv'),
    
    # ROTA PARA REMOVER A PRESENÇA DE UM PARTICIPANTE
    path('inscricao/<int:inscricao_id>/remover_presenca/', views.remover_presenca, name='remover_presenca'),

    # --- NOVA ROTA PARA ENVIO GERAL DE E-MAILS ---
    path('participantes/enviar_emails/', views.enviar_emails_gerais_qrcode, name='enviar_emails_gerais_qrcode'),

    # --- NOVA ROTA PARA ENVIO INDIVIDUAL ---
    path('participante/<int:participante_id>/enviar_email/', views.enviar_email_individual, name='enviar_email_individual'),

    # --- NOVA ROTA PARA ENVIOS PENDENTES ---
    path('participantes/enviar_pendentes/', views.enviar_emails_pendentes, name='enviar_emails_pendentes'),
]

