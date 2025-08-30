import uuid
from django.db import models
from django.core.files.base import ContentFile
from io import BytesIO
import qrcode
from django.utils import timezone

class Participante(models.Model):
    nome = models.CharField(max_length=200, verbose_name="Nome Completo")
    email = models.EmailField(unique=True, verbose_name="E-mail")
    matricula = models.CharField(max_length=50, unique=True, verbose_name="Matrícula")
    id_unico_qr = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="ID do QR Code")
    qr_code_img = models.ImageField(upload_to='qrcodes/', blank=True, null=True, verbose_name="Imagem do QR Code")

    def __str__(self):
        return self.nome

    def gerar_e_salvar_qrcode(self):
        buffer = BytesIO()
        img = qrcode.make(str(self.id_unico_qr))
        img.save(buffer, format='PNG')
        nome_arquivo = f'{self.matricula}.png'
        self.qr_code_img.save(nome_arquivo, ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        if not self.pk or not self.qr_code_img:
            self.gerar_e_salvar_qrcode()
        super().save(*args, **kwargs)

class Evento(models.Model):
    nome = models.CharField(max_length=255, verbose_name="Nome do Evento")
    data = models.DateTimeField(verbose_name="Data e Hora")
    vagas = models.PositiveIntegerField(default=0, verbose_name="Número de Vagas")

    def __str__(self):
        return self.nome

class Inscricao(models.Model):
    STATUS_CHOICES = (('INSCRITO', 'Inscrito'),('PRESENTE', 'Presente'),('LISTA_ESPERA', 'Lista de Espera'),)
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE, related_name='inscricoes')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='inscricoes')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INSCRITO')
    data_checkin = models.DateTimeField(null=True, blank=True, verbose_name="Data do Check-in")
    data_entrada_espera = models.DateTimeField(null=True, blank=True, verbose_name="Entrada na Lista de Espera")

    class Meta:
        unique_together = ('participante', 'evento')

    def __str__(self):
        return f"{self.participante.nome} em {self.evento.nome} - {self.get_status_display()}"

    def registrar_presenca(self):
        """Muda o status para Presente e regista o horário."""
        self.status = 'PRESENTE'
        self.data_checkin = timezone.now()
        self.save()
    
    # NOVO MÉTODO PARA REMOVER A PRESENÇA
    def remover_presenca(self):
        """Muda o status para Lista de Espera, limpa o horário do check-in e
        regista a hora em que voltou para a fila para que vá para o final."""
        self.status = 'LISTA_ESPERA'
        self.data_checkin = None
        self.data_entrada_espera = timezone.now()
        self.save()
