from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Participante, Evento, Inscricao
import pandas as pd
import io
import json
import csv
from django.utils import timezone
from django.contrib import messages # Importar o messages framework

# --- Visões de Gestão de Eventos ---
def lista_eventos(request):
    eventos = Evento.objects.all().order_by('-data')
    return render(request, 'core/lista_eventos.html', {'eventos': eventos})

def detalhe_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    inscricoes = evento.inscricoes.all()
    inscritos_aguardando = inscricoes.filter(status='INSCRITO').order_by('participante__nome')
    presentes = inscricoes.filter(status='PRESENTE').order_by('participante__nome')
    lista_espera = inscricoes.filter(status='LISTA_ESPERA').order_by('data_entrada_espera')
    vagas_disponiveis = evento.vagas - presentes.count()
    context = {
        'evento': evento,
        'inscritos_aguardando': inscritos_aguardando,
        'presentes': presentes,
        'lista_espera': lista_espera,
        'vagas_disponiveis': vagas_disponiveis
    }
    return render(request, 'core/detalhe_evento.html', context)

def inscrever_via_csv(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    if request.method == 'POST':
        arquivo_csv = request.FILES.get('arquivo_csv')
        if not arquivo_csv:
            messages.error(request, "Nenhum ficheiro foi enviado.")
            return redirect('detalhe_evento', evento_id=evento.id)
        try:
            decoded_file = arquivo_csv.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            df = pd.read_csv(io_string, header=None, names=['matricula', 'nome'])
            novos_inscritos_count = 0
            for index, row in df.iterrows():
                matricula = str(row['matricula']).strip()
                participante = Participante.objects.filter(matricula=matricula).first()
                if participante:
                    inscricao, created = Inscricao.objects.get_or_create(
                        participante=participante, evento=evento, defaults={'status': 'INSCRITO'}
                    )
                    if created:
                        novos_inscritos_count += 1
            
            if novos_inscritos_count > 0:
                messages.success(request, f"{novos_inscritos_count} novos participantes foram inscritos com sucesso!")
            else:
                messages.info(request, "Nenhuma nova inscrição foi adicionada. Os participantes já estavam inscritos.")

        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao processar o ficheiro CSV: {e}")
    
    return redirect('detalhe_evento', evento_id=evento.id)

# --- Visões da Página de Check-in ---
def pagina_checkin(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    return render(request, 'core/checkin.html', {'evento': evento})

@csrf_exempt
def api_checkin(request, evento_id):
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
                presentes_count = Inscricao.objects.filter(evento=evento, status='PRESENTE').count()
                if evento.vagas > 0 and presentes_count >= evento.vagas:
                    inscricao.status = 'LISTA_ESPERA'
                    inscricao.data_entrada_espera = timezone.now()
                    inscricao.save()
                    return JsonResponse({'status': 'espera', 'mensagem': f'Vagas esgotadas! {participante.nome} (inscrito) foi para a lista de espera.'})
                else:
                    inscricao.registrar_presenca()
                    return JsonResponse({'status': 'sucesso', 'mensagem': f'Check-in de {participante.nome} realizado!'})
            else:
                Inscricao.objects.create(
                    participante=participante, evento=evento, status='LISTA_ESPERA', data_entrada_espera=timezone.now()
                )
                return JsonResponse({'status': 'espera', 'mensagem': f'{participante.nome} (não inscrito) foi para a lista de espera.'})
        except Participante.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'QR Code inválido. Participante não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'}, status=405)

# --- Gestão Geral de Participantes ---
def cadastro_geral_csv(request):
    if request.method == 'POST':
        arquivo_csv = request.FILES.get('arquivo_csv')
        if not arquivo_csv:
            messages.error(request, "Nenhum ficheiro foi enviado.")
            return redirect('cadastro_geral')
        try:
            df = pd.read_csv(arquivo_csv, header=None, names=['matricula', 'nome', 'email'])
            participantes_criados = 0
            participantes_atualizados = 0
            for index, row in df.iterrows():
                obj, created = Participante.objects.update_or_create(
                    matricula=str(row['matricula']).strip(),
                    defaults={'nome': str(row['nome']).strip(), 'email': str(row['email']).strip()}
                )
                if created:
                    participantes_criados += 1
                else:
                    participantes_atualizados += 1
            messages.success(request, f"Base de dados geral atualizada: {participantes_criados} participantes criados e {participantes_atualizados} atualizados.")
            return redirect('lista_geral_participantes')
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao processar o ficheiro CSV: {e}")
            return redirect('cadastro_geral')
    return render(request, 'core/cadastro_geral.html')

def lista_geral_participantes(request):
    participantes = Participante.objects.all().order_by('nome')
    return render(request, 'core/lista_geral_participantes.html', {'participantes': participantes})

# --- Ações de Gestão de Evento ---
@require_POST
def promover_participante(request, inscricao_id):
    inscricao = get_object_or_404(Inscricao, id=inscricao_id)
    inscricao.registrar_presenca()
    messages.success(request, f"{inscricao.participante.nome} foi promovido(a) para a lista de presentes.")
    return redirect('detalhe_evento', evento_id=inscricao.evento.id)

@require_POST
def remover_presenca(request, inscricao_id):
    inscricao = get_object_or_404(Inscricao, id=inscricao_id)
    inscricao.remover_presenca()
    messages.info(request, f"{inscricao.participante.nome} foi movido(a) para o final da lista de espera.")
    return redirect('detalhe_evento', evento_id=inscricao.evento.id)

def exportar_presenca_csv(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="presenca_{evento.nome.lower().replace(" ", "_")}.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow(['Nome', 'Matrícula', 'Email', 'Horário do Check-in'])
    presentes = evento.inscricoes.filter(status='PRESENTE').order_by('participante__nome')
    for inscricao in presentes:
        writer.writerow([
            inscricao.participante.nome,
            inscricao.participante.matricula,
            inscricao.participante.email,
            inscricao.data_checkin.strftime('%d/%m/%Y %H:%M:%S') if inscricao.data_checkin else ''
        ])
    return response

