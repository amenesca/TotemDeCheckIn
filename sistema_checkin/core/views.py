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
from .forms import ParticipanteForm
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


# --- FUNÇÃO AUXILIAR ATUALIZADA ---
def _enviar_qr_code_email(participante):
    """
    Função auxiliar que monta e envia o e-mail com QR Code para um participante.
    Atualiza o campo 'ultimo_envio_email' se o envio for bem-sucedido.
    Retorna True se o e-mail foi enviado com sucesso, False caso contrário.
    """
    if not participante.qr_code_img:
        return False
    
    try:
        contexto_email = {'nome_participante': participante.nome}
        corpo_email = render_to_string('core/email_qrcode_geral.html', contexto_email)

        email = EmailMessage(
            subject="Seu QR Code de Acesso para Eventos",
            body=corpo_email,
            from_email=None,
            to=[participante.email]
        )
        email.content_subtype = "html"
        email.attach_file(participante.qr_code_img.path)
        
        email.send()

        # --- MUDANÇA IMPORTANTE ---
        # Se o e-mail foi enviado, atualiza o campo com a data e hora atuais
        participante.ultimo_envio_email = timezone.now()
        participante.save(update_fields=['ultimo_envio_email'])

        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail para {participante.nome}: {e}")
        return False

# --- Visões de Gestão de Eventos ---
def lista_eventos(request):
    from itertools import groupby
    from django.utils.timezone import localtime

    # Ordena por data
    eventos = Evento.objects.all().order_by('data')

    # Agrupa os eventos pelo dia (ignorando hora)
    eventos_por_dia = {}
    for data, grupo in groupby(eventos, key=lambda e: localtime(e.data).date()):
        eventos_por_dia[data] = list(grupo)

    return render(request, 'core/lista_eventos.html', {'eventos_por_dia': eventos_por_dia})


def detalhe_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    inscricoes = evento.inscricoes.all()
    inscritos_aguardando = inscricoes.filter(status='INSCRITO').order_by('participante__nome')
    presentes = inscricoes.filter(status='PRESENTE').order_by('-data_checkin')
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
            novos_inscritos, ja_inscritos, nao_encontrados, erros_formato = 0, 0, [], []
            
            todas_as_matriculas_db = set(Participante.objects.values_list('matricula', flat=True))

            for i, row in enumerate(csv.reader(linhas), 1):
                if not row: continue

                # --- MUDANÇA 1: VALIDANDO O FORMATO DA LINHA ---
                if len(row) != 3:
                    erros_formato.append(str(i))
                    continue
                
                # --- MUDANÇA 2: PEGANDO A MATRÍCULA DA SEGUNDA COLUNA ---
                matricula_csv = row[1].strip() # Pega o valor do índice 1
                if not matricula_csv: continue

                if matricula_csv in todas_as_matriculas_db:
                    participante = Participante.objects.get(matricula=matricula_csv)
                    _, created = Inscricao.objects.get_or_create(participante=participante, evento=evento)
                    if created:
                        novos_inscritos += 1
                    else:
                        ja_inscritos += 1
                else:
                    nao_encontrados.append(matricula_csv)

            if novos_inscritos > 0:
                messages.success(request, f"{novos_inscritos} novos participantes inscritos com sucesso.")
            if ja_inscritos > 0:
                messages.info(request, f"{ja_inscritos} participantes já estavam inscritos no evento.")
            if nao_encontrados:
                messages.warning(request, f"Matrículas não encontradas no cadastro geral: {', '.join(nao_encontrados)}")
            if erros_formato:
                 messages.error(request, f"As seguintes linhas foram ignoradas por não conter 3 colunas (nome,matricula,email): {', '.join(erros_formato)}")

        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao processar o ficheiro de inscrição: {e}")
    
    return redirect('detalhe_evento', evento_id=evento.id)

# --- Visões da Página de Check-in ---
def pagina_checkin(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    vagas_disponiveis = evento.vagas - evento.inscricoes.filter(status='PRESENTE').count()
    return render(request, 'core/checkin.html', {
        'evento': evento,
        'vagas_disponiveis': vagas_disponiveis
    })

@csrf_exempt
@csrf_exempt
def api_checkin(request, evento_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id_unico_qr = data.get('id_unico_qr')
            matricula = data.get('matricula')

            evento = get_object_or_404(Evento, id=evento_id)
            participante = None

            # --- BUSCA PELO QR CODE OU CPF ---
            if id_unico_qr:
                participante = get_object_or_404(Participante, id_unico_qr=id_unico_qr)

            elif matricula:
                # Remove espaços, pontos e traços do CPF digitado
                cpf_digitado = matricula.strip().replace('.', '').replace('-', '')

                # Procura participante ignorando formatação
                for p in Participante.objects.all():
                    cpf_salvo = p.matricula.replace('.', '').replace('-', '')
                    if cpf_salvo == cpf_digitado:
                        participante = p
                        break

                if not participante:
                    return JsonResponse({'status': 'erro', 'mensagem': 'Participante não encontrado. Verifique o CPF.'}, status=404)

            else:
                return JsonResponse({'status': 'erro', 'mensagem': 'Nenhum identificador (QR Code ou CPF) foi fornecido.'}, status=400)

            # --- REGISTRO DO CHECK-IN ---
            inscricao, created = Inscricao.objects.get_or_create(
                participante=participante,
                evento=evento
            )

            if inscricao.status == 'PRESENTE':
                return JsonResponse({'status': 'aviso', 'mensagem': f'{participante.nome} já realizou o check-in.'})

            inscricao.registrar_presenca()

            if created:
                mensagem = f'Check-in de {participante.nome} realizado com sucesso!'
            else:
                mensagem = f'Check-in de {participante.nome} realizado com sucesso!'

            return JsonResponse({'status': 'sucesso', 'mensagem': mensagem})

        except Participante.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Participante não encontrado. Verifique o CPF ou QR Code.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)

    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'}, status=405)

    
def cadastro_geral(request):
    manual_form = ParticipanteForm()

    if request.method == 'POST':
        # --- CADASTRO MANUAL ---
        if 'manual_add' in request.POST:
            manual_form = ParticipanteForm(request.POST)
            if manual_form.is_valid():
                novo_participante = manual_form.save()
                messages.success(request, f"Participante '{novo_participante.nome}' cadastrado com sucesso!")

                if _enviar_qr_code_email(novo_participante):
                    messages.info(request, f"O QR Code foi enviado para o e-mail de {novo_participante.nome}.")
                else:
                    messages.error(request, f"Falha ao enviar o e-mail com QR Code para {novo_participante.nome}.")
                return redirect('lista_geral_participantes')

        # --- IMPORTAÇÃO VIA CSV ---
        elif 'upload_csv' in request.POST:
            arquivo_csv = request.FILES.get('arquivo_csv')
            if not arquivo_csv:
                messages.error(request, "Nenhum arquivo CSV foi enviado.")
                return redirect('cadastro_geral')

            try:
                conteudo_arquivo = arquivo_csv.read().decode('utf-8-sig')
                linhas = [l for l in conteudo_arquivo.splitlines() if l.strip()]
                reader = csv.reader(linhas)

                # Ignora o cabeçalho
                next(reader, None)

                criados, atualizados, erros = 0, 0, []

                for i, row in enumerate(reader, start=2):
                    # Esperado: id,nome,matricula,email
                    if len(row) < 4:
                        erros.append(f"Linha {i}: formato incorreto (esperado id,nome,matricula,email).")
                        continue

                    try:
                        nome = row[1].strip()
                        matricula = row[2].strip()
                        email = row[3].strip()
                    except Exception as e:
                        erros.append(f"Linha {i}: erro ao ler campos ({e}).")
                        continue

                    if not nome or not matricula or not email:
                        erros.append(f"Linha {i}: campos vazios.")
                        continue

                    try:
                        participante, created = Participante.objects.update_or_create(
                            matricula=matricula,
                            defaults={'nome': nome, 'email': email}
                        )
                        if created:
                            criados += 1
                        else:
                            atualizados += 1
                    except Exception as e:
                        erros.append(f"Linha {i}: erro ao salvar ({e}).")
                        continue

                messages.success(request, f"Importação concluída: {criados} criados e {atualizados} atualizados.")
                if erros:
                    messages.warning(request, "Problemas encontrados:\n" + " | ".join(erros))

            except Exception as e:
                messages.error(request, f"Erro ao processar o CSV: {e}")

            return redirect('lista_geral_participantes')

    return render(request, 'core/cadastro_geral.html', {'manual_form': manual_form})

    # Independentemente do método, inicializamos sempre os dois formulários
    manual_form = ParticipanteForm()
    
    if request.method == 'POST':
        if 'manual_add' in request.POST:
            manual_form = ParticipanteForm(request.POST)
            if manual_form.is_valid():
                # Salva o participante no banco de dados
                novo_participante = manual_form.save()
                messages.success(request, f"Participante '{novo_participante.nome}' cadastrado com sucesso!")
                
                # --- MUDANÇA: ENVIA O E-MAIL AUTOMATICAMENTE ---
                if _enviar_qr_code_email(novo_participante):
                    messages.info(request, f"O QR Code foi enviado para o e-mail de {novo_participante.nome}.")
                else:
                    messages.error(request, f"Falha ao enviar o e-mail com QR Code para {novo_participante.nome}.")

                return redirect('lista_geral_participantes')

        elif 'upload_csv' in request.POST:
            # Se foi o botão de CSV, executamos a lógica de upload
            arquivo_csv = request.FILES.get('arquivo_csv')
            if not arquivo_csv:
                messages.error(request, "Nenhum ficheiro foi enviado.")
                return redirect('cadastro_geral')
            
            try:
                conteudo_arquivo = arquivo_csv.read().decode('utf-8-sig')
                linhas = conteudo_arquivo.splitlines()
                reader = csv.reader(linhas)
                criados, atualizados, erros = 0, 0, []

                for i, row in enumerate(reader, 1):
                    if not row: continue
                    if len(row) != 3:
                        erros.append(f"Linha {i}: Formato inválido (esperava nome,matricula,email).")
                        continue
                    
                    nome, matricula, email = [field.strip() for field in row]

                    if not matricula or not nome or not email:
                        erros.append(f"Linha {i}: Dados incompletos.")
                        continue

                    _, created = Participante.objects.update_or_create(
                        matricula=matricula, defaults={'nome': nome, 'email': email}
                    )
                    if created:
                        criados += 1
                    else:
                        atualizados += 1

                messages.success(request, f"Base de dados atualizada via CSV: {criados} criados e {atualizados} atualizados.")
                if erros:
                    messages.warning(request, f"Problemas no CSV: {' | '.join(erros)}")
                return redirect('lista_geral_participantes')
            except Exception as e:
                messages.error(request, f"Ocorreu um erro crítico ao processar o ficheiro: {e}")
                return redirect('cadastro_geral')

    # Para um pedido GET, ou se o formulário manual for inválido, renderiza a página
    # A variável 'form' agora chama-se 'manual_form' para maior clareza
    return render(request, 'core/cadastro_geral.html', {'manual_form': manual_form})


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
    
def exportar_todas_presencas_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="presenca_todos_eventos.csv"'
    response.write(u'\ufeff'.encode('utf8'))  # Para abrir corretamente no Excel
    writer = csv.writer(response)

    writer.writerow(['Evento', 'Nome', 'Matrícula', 'Email', 'Horário do Check-in'])

    eventos = Evento.objects.all().order_by('data')
    for evento in eventos:
        presentes = evento.inscricoes.filter(status='PRESENTE').order_by('participante__nome')
        for inscricao in presentes:
            writer.writerow([
                evento.nome,
                inscricao.participante.nome,
                inscricao.participante.matricula,
                inscricao.participante.email,
                inscricao.data_checkin.strftime('%d/%m/%Y %H:%M:%S') if inscricao.data_checkin else ''
            ])

    return response


@require_POST
def enviar_emails_gerais_qrcode(request):
    participantes = Participante.objects.all()
    if not participantes:
        messages.warning(request, "Não há participantes cadastrados.")
        return redirect('lista_geral_participantes')

    enviados_com_sucesso = 0
    erros = []
    for participante in participantes:
        if _enviar_qr_code_email(participante):
            enviados_com_sucesso += 1
        else:
            erros.append(participante.nome)

    if enviados_com_sucesso > 0:
        messages.success(request, f"{enviados_com_sucesso} e-mails com QR Code foram enviados com sucesso!")
    if erros:
        messages.error(request, f"Ocorreram falhas ao enviar e-mails para: {', '.join(erros)}")

    return redirect('lista_geral_participantes')

# --- NOVA VIEW PARA ENVIAR E-MAILS PENDENTES ---
@require_POST
def enviar_emails_pendentes(request):
    # Filtra apenas os participantes que NUNCA receberam o e-mail
    participantes_pendentes = Participante.objects.filter(ultimo_envio_email__isnull=True)
    
    if not participantes_pendentes:
        messages.info(request, "Não há participantes com envios de e-mail pendentes.")
        return redirect('lista_geral_participantes')

    enviados_com_sucesso = 0
    erros = []
    for participante in participantes_pendentes:
        if _enviar_qr_code_email(participante):
            enviados_com_sucesso += 1
        else:
            erros.append(participante.nome)

    if enviados_com_sucesso > 0:
        messages.success(request, f"{enviados_com_sucesso} e-mails pendentes foram enviados com sucesso!")
    if erros:
        messages.error(request, f"Ocorreram falhas ao enviar e-mails para: {', '.join(erros)}")

    return redirect('lista_geral_participantes')

# --- NOVA VIEW PARA ENVIO INDIVIDUAL ---
@require_POST
def enviar_email_individual(request, participante_id):
    participante = get_object_or_404(Participante, id=participante_id)
    
    if _enviar_qr_code_email(participante):
        messages.success(request, f"E-mail com QR Code enviado com sucesso para {participante.nome}!")
    else:
        messages.error(request, f"Ocorreu um erro ao tentar enviar o e-mail para {participante.nome}.")
        
    return redirect('lista_geral_participantes')