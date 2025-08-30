from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Participante, Evento, Inscricao
import pandas as pd
import io
import json
import csv

# --- Visões de Gerenciamento de Eventos ---
def lista_eventos(request):
    """
    Exibe uma lista com todos os eventos cadastrados, ordenados por data.
    """
    eventos = Evento.objects.all().order_by('-data')
    return render(request, 'core/lista_eventos.html', {'eventos': eventos})

def detalhe_evento(request, evento_id):
    """
    Mostra a página de detalhes de um evento específico, incluindo as listas
    de participantes por status e a mensagem de sucesso de inscrição.
    """
    evento = get_object_or_404(Evento, id=evento_id)
    novos_inscritos_nomes = request.session.pop('novos_inscritos', None)
    
    inscricoes = evento.inscricoes.all().order_by('participante__nome')
    inscritos_aguardando = inscricoes.filter(status='INSCRITO')
    presentes = inscricoes.filter(status='PRESENTE')
    lista_espera = inscricoes.filter(status='LISTA_ESPERA')
    
    context = {
        'evento': evento,
        'inscritos_aguardando': inscritos_aguardando,
        'presentes': presentes,
        'lista_espera': lista_espera,
        'novos_inscritos_nomes': novos_inscritos_nomes
    }
    return render(request, 'core/detalhe_evento.html', context)

def inscrever_via_csv(request, evento_id):
    """
    Processa o upload de um arquivo CSV com 'matrícula' e 'nome' para inscrever
    alunos em um evento.
    """
    evento = get_object_or_404(Evento, id=evento_id)
    if request.method == 'POST':
        arquivo_csv = request.FILES.get('arquivo_csv')
        if not arquivo_csv:
            return redirect('detalhe_evento', evento_id=evento.id)
        try:
            decoded_file = arquivo_csv.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            df = pd.read_csv(io_string, header=None, names=['matricula', 'nome'])
            
            novos_inscritos_nomes = []
            for index, row in df.iterrows():
                matricula = str(row['matricula']).strip()
                participante = Participante.objects.filter(matricula=matricula).first()
                if participante:
                    inscricao, created = Inscricao.objects.get_or_create(
                        participante=participante,
                        evento=evento,
                        defaults={'status': 'INSCRITO'}
                    )
                    if created:
                        novos_inscritos_nomes.append(participante.nome)
            request.session['novos_inscritos'] = novos_inscritos_nomes
        except Exception as e:
            print(f"Erro ao processar CSV de inscrição: {e}")
    
    return redirect('detalhe_evento', evento_id=evento.id)


# --- Visões da Página de Check-in ---
def pagina_checkin(request, evento_id):
    """
    Renderiza a página HTML que contém o scanner de QR Code.
    """
    evento = get_object_or_404(Evento, id=evento_id)
    return render(request, 'core/checkin.html', {'evento': evento})

@csrf_exempt
def api_checkin(request, evento_id):
    """
    Endpoint da API que recebe os dados do QR Code lido pelo scanner.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id_unico_qr = data.get('id_unico_qr')
            evento = get_object_or_404(Evento, id=evento_id)
            participante = get_object_or_404(Participante, id_unico_qr=id_unico_qr)
            inscricao = Inscricao.objects.filter(participante=participante, evento=evento).first()
            
            if inscricao:
                if inscricao.status == 'PRESENTE':
                    return JsonResponse({'status': 'aviso', 'mensagem': f'{participante.nome} já realizou o check-in.'})
                else:
                    inscricao.registrar_presenca()
                    return JsonResponse({'status': 'sucesso', 'mensagem': f'Check-in de {participante.nome} realizado!'})
            else:
                Inscricao.objects.create(participante=participante, evento=evento, status='LISTA_ESPERA')
                return JsonResponse({'status': 'espera', 'mensagem': f'{participante.nome} adicionado(a) à lista de espera.'})

        except Participante.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'QR Code inválido. Participante não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)

    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'}, status=405)

# --- Visões de Gerenciamento Geral de Participantes ---
def cadastro_geral_csv(request):
    """
    Renderiza a página para o upload do CSV mestre e processa o arquivo,
    cadastrando ou atualizando os participantes na base de dados geral.
    """
    if request.method == 'POST':
        arquivo_csv = request.FILES.get('arquivo_csv')
        if not arquivo_csv:
            return redirect('cadastro_geral')
        try:
            df = pd.read_csv(arquivo_csv, header=None, names=['matricula', 'nome', 'email'])
            for index, row in df.iterrows():
                Participante.objects.update_or_create(
                    matricula=str(row['matricula']).strip(),
                    defaults={'nome': str(row['nome']).strip(),'email': str(row['email']).strip()}
                )
            return redirect('lista_geral_participantes')
        except Exception as e:
            print(f"Erro ao processar CSV geral: {e}")
            return redirect('cadastro_geral')
    return render(request, 'core/cadastro_geral.html')

def lista_geral_participantes(request):
    """
    Exibe a lista completa de todos os participantes cadastrados no sistema,
    com seus respectivos QR Codes.
    """
    participantes = Participante.objects.all().order_by('nome')
    return render(request, 'core/lista_geral_participantes.html', {'participantes': participantes})

# --- NOVAS FUNÇÕES ---

@require_POST # Garante que esta função só pode ser chamada com o método POST
def promover_participante(request, inscricao_id):
    """
    Promove um participante da lista de espera para a lista de presentes.
    """
    inscricao = get_object_or_404(Inscricao, id=inscricao_id)
    # Chama a função que já existe no nosso modelo para registrar a presença
    inscricao.registrar_presenca()
    # Redireciona de volta para a página de detalhes do evento
    return redirect('detalhe_evento', evento_id=inscricao.evento.id)

def exportar_presenca_csv(request, evento_id):
    """
    Gera e oferece para download um arquivo CSV com todos os participantes
    que estão com o status 'PRESENTE'.
    """
    evento = get_object_or_404(Evento, id=evento_id)
    
    # Prepara a resposta HTTP para ser um arquivo CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="presenca_{evento.nome.lower().replace(" ", "_")}.csv"'
    response.write(u'\ufeff'.encode('utf8')) # BOM para garantir a codificação correta

    # Cria o "escritor" de CSV
    writer = csv.writer(response)
    
    # Escreve a linha do cabeçalho
    writer.writerow(['Nome', 'Matrícula', 'Email', 'Horário do Check-in'])

    # Busca no banco de dados todas as inscrições com status 'PRESENTE' para este evento
    presentes = evento.inscricoes.filter(status='PRESENTE').order_by('participante__nome')

    # Escreve uma linha no CSV para cada participante presente
    for inscricao in presentes:
        writer.writerow([
            inscricao.participante.nome,
            inscricao.participante.matricula,
            inscricao.participante.email,
            inscricao.data_checkin.strftime('%d/%m/%Y %H:%M:%S') if inscricao.data_checkin else ''
        ])

    return response

# Fim do arquivo views.py