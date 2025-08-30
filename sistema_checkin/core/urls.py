from django.urls import path
from . import views

urlpatterns = [
    # --- ROTAS DE GERENCIAMENTO GERAL ---
    path('cadastro-geral/', views.cadastro_geral_csv, name='cadastro_geral'),
    path('participantes/', views.lista_geral_participantes, name='lista_geral_participantes'),
    
    # --- ROTAS DE EVENTOS ---
    path('', views.lista_eventos, name='lista_eventos'),
    path('evento/<int:evento_id>/', views.detalhe_evento, name='detalhe_evento'),
    path('evento/<int:evento_id>/inscrever_csv/', views.inscrever_via_csv, name='inscrever_via_csv'),
    path('evento/<int:evento_id>/checkin/', views.pagina_checkin, name='pagina_checkin'),
    
    # --- ROTAS DE API E AÇÕES (NOVAS ROTAS ABAIXO) ---
    path('api/checkin/<int:evento_id>/', views.api_checkin, name='api_checkin'),
    
    # ROTA PARA PROMOVER UM PARTICIPANTE DA LISTA DE ESPERA
    path('inscricao/<int:inscricao_id>/promover/', views.promover_participante, name='promover_participante'),
    
    # ROTA PARA EXPORTAR A LISTA DE PRESENÇA EM CSV
    path('evento/<int:evento_id>/exportar_csv/', views.exportar_presenca_csv, name='exportar_presenca_csv'),
]