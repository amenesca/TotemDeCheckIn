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
    
def cadastro_geral(request):
    # Independentemente do método, inicializamos sempre os dois formulários
    manual_form = ParticipanteForm()
    
    # Verificamos qual botão de submissão foi pressionado
    if request.method == 'POST':
        if 'manual_add' in request.POST:
            # Se foi o botão manual, preenchemos esse formulário com os dados do POST
            manual_form = ParticipanteForm(request.POST)
            if manual_form.is_valid():
                manual_form.save()
                messages.success(request, f"Participante '{manual_form.cleaned_data['nome']}' cadastrado com sucesso!")
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

@require_POST
def enviar_emails_gerais_qrcode(request):
    participantes = Participante.objects.all()
    
    if not participantes:
        messages.warning(request, "Não há participantes cadastrados para enviar e-mails.")
        return redirect('lista_geral_participantes')

    enviados_com_sucesso = 0
    erros = []

    for participante in participantes:
        if not participante.qr_code_img:
            erros.append(f"{participante.nome}: QR Code não encontrado.")
            continue
        
        try:
            # Renderiza o template do e-mail com o contexto
            contexto_email = {
                'nome_participante': participante.nome,
            }
            corpo_email = render_to_string('core/email_qrcode_geral.html', contexto_email)

            # Cria o e-mail
            email = EmailMessage(
                subject="Seu QR Code de Acesso para Eventos",
                body=corpo_email,
                from_email='nao-responda@sistema.com', # Um e-mail remetente genérico
                to=[participante.email]
            )
            email.content_subtype = "html" # Define o conteúdo como HTML

            # Anexa a imagem do QR Code
            caminho_qr = participante.qr_code_img.path
            email.attach_file(caminho_qr)

            # Envia o e-mail
            email.send()
            enviados_com_sucesso += 1
        
        except Exception as e:
            erros.append(f"Erro ao enviar para {participante.nome}: {str(e)}")

    if enviados_com_sucesso > 0:
        messages.success(request, f"{enviados_com_sucesso} e-mails com QR Code foram enviados com sucesso!")
    if erros:
        messages.error(request, f"Ocorreram erros: {', '.join(erros)}")

    return redirect('lista_geral_participantes')