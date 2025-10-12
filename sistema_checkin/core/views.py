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
            conteudo_arquivo = arquivo_csv.read().decode('utf-8-sig')
            linhas = conteudo_arquivo.splitlines()

            if not linhas:
                messages.error(request, "O arquivo de inscrição está vazio.")
                return redirect('detalhe_evento', evento_id=evento.id)

            novos_inscritos = 0
            ja_inscritos = 0
            nao_encontrados = []
            
            # Carrega todas as matrículas do banco de dados para um set em memória.
            # Esta é a forma mais rápida e garantida de fazer a verificação.
            todas_as_matriculas_db = set(Participante.objects.values_list('matricula', flat=True))

            for i, row in enumerate(csv.reader(linhas), 1):
                if not row: continue

                matricula_csv = row[0].strip()
                if not matricula_csv: continue

                # A BUSCA ACONTECE AQUI: em Python puro, comparando strings.
                if matricula_csv in todas_as_matriculas_db:
                    try:
                        # Pega o participante e cria a inscrição
                        participante = Participante.objects.get(matricula=matricula_csv)
                        _, created = Inscricao.objects.get_or_create(
                            participante=participante, 
                            evento=evento
                        )
                        if created:
                            novos_inscritos += 1
                        else:
                            ja_inscritos += 1
                    except Participante.DoesNotExist:
                        # Esta exceção não deveria acontecer se a lógica estiver correta, mas é uma salvaguarda
                        nao_encontrados.append(f"{matricula_csv} (erro inesperado)")
                else:
                    nao_encontrados.append(matricula_csv)

            if novos_inscritos > 0:
                messages.success(request, f"{novos_inscritos} novos participantes inscritos com sucesso.")
            if ja_inscritos > 0:
                messages.info(request, f"{ja_inscritos} participantes já estavam inscritos no evento.")
            if nao_encontrados:
                messages.warning(request, f"As seguintes matrículas do arquivo não foram encontradas no cadastro geral: {', '.join(nao_encontrados)}")

        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao processar o ficheiro de inscrição: {e}")
    
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

            # --- LÓGICA MODIFICADA ---
            # get_or_create busca uma inscrição existente ou cria uma nova se não existir.
            # Isso lida elegantemente com participantes que não estavam pré-inscritos.
            inscricao, created = Inscricao.objects.get_or_create(
                participante=participante,
                evento=evento
            )

            # Se o participante já tinha feito check-in, apenas retorne um aviso.
            if inscricao.status == 'PRESENTE':
                return JsonResponse({'status': 'aviso', 'mensagem': f'{participante.nome} já realizou o check-in.'})

            # Para todos os outros casos (seja um novo participante ou um que estava 'INSCRITO'),
            # simplesmente registre a presença. A capacidade do evento é ignorada.
            inscricao.registrar_presenca()

            # Fornece uma mensagem um pouco diferente se o participante não estava na lista original.
            if created:
                mensagem = f'Check-in de {participante.nome} (não inscrito) realizado com sucesso!'
            else:
                mensagem = f'Check-in de {participante.nome} realizado!'
            
            return JsonResponse({'status': 'sucesso', 'mensagem': mensagem})

        except Participante.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'QR Code inválido. Participante não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)
            
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'}, status=405)
    
# --- VERSÃO FINAL E DEFINITIVA - CADASTRO GERAL ---
def cadastro_geral_csv(request):
    if request.method == 'POST':
        arquivo_csv = request.FILES.get('arquivo_csv')
        if not arquivo_csv:
            messages.error(request, "Nenhum ficheiro foi enviado.")
            return redirect('cadastro_geral')
        
        try:
            conteudo_arquivo = arquivo_csv.read().decode('utf-8-sig')
            linhas = conteudo_arquivo.splitlines()
            
            # Validação para garantir que o arquivo não está vazio
            if not linhas:
                messages.error(request, "O arquivo CSV está vazio.")
                return redirect('cadastro_geral')
            
            reader = csv.reader(linhas)

            criados = 0
            atualizados = 0
            erros = []

            for i, row in enumerate(reader, 1):
                if not row: continue

                if len(row) != 3:
                    erros.append(f"Linha {i}: Formato inválido. Esperava 3 colunas (matrícula,nome,email).")
                    continue
                
                # Limpeza explícita de cada campo para remover quaisquer espaços
                matricula = row[0].strip()
                nome = row[1].strip()
                email = row[2].strip()

                if not matricula or not nome or not email:
                    erros.append(f"Linha {i}: Dados incompletos.")
                    continue

                try:
                    # Usando get_or_create para ser mais explícito
                    participante, created = Participante.objects.get_or_create(
                        matricula=matricula,
                        defaults={'nome': nome, 'email': email}
                    )
                    if not created:
                        # Se já existia, atualiza o nome e email
                        participante.nome = nome
                        participante.email = email
                        participante.save()
                        atualizados += 1
                    else:
                        criados += 1
                except IntegrityError:
                    erros.append(f"Linha {i}: Erro de integridade. A matrícula '{matricula}' já existe com dados diferentes?")
                except Exception as e:
                    erros.append(f"Linha {i}: Erro inesperado ao salvar: {e}")

            messages.success(request, f"Base de dados atualizada: {criados} participantes criados e {atualizados} atualizados.")
            if erros:
                messages.warning(request, f"Problemas encontrados: {' | '.join(erros)}")
            
            return redirect('lista_geral_participantes')

        except Exception as e:
            messages.error(request, f"Ocorreu um erro crítico ao processar o ficheiro: {e}")
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

