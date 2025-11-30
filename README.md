# Sistema de Check-in para Eventos com QR Code

Este é um sistema desenvolvido em Django para a gestão de check-in em eventos. A aplicação permite cadastrar participantes, gerar QR Codes únicos para cada um, gerenciar eventos e realizar o check-in de forma rápida utilizando a câmera de um computador ou totem.

<h3 align="center">Screenshots do Sistema</h3>

<div align="center">
  <img src="https://github.com/user-attachments/assets/0d111134-501c-4169-9596-5b5e5d761ebc" width="700" alt="Tela do Sistema 1" />
  <br/><br/>
  
  <img src="https://github.com/user-attachments/assets/2445c745-e54c-413f-86e0-231abe739151" width="700" alt="Tela do Sistema 2" />
  <br/><br/>

  <img src="https://github.com/user-attachments/assets/8bb66ccd-7805-43b1-9413-86f9f325672c" width="700" alt="Tela do Sistema 3" />
</div>

## Funcionalidades Principais

- **Gestão de Participantes:** Cadastro manual ou em massa via upload de arquivo CSV.
- **QR Codes Permanentes:** Geração automática de um QR Code único para cada participante no momento do cadastro.
- **Check-in Versátil em Tempo Real:** Página de "totem" que permite o registro de presença por QR Code (usando a câmera com espelhamento inteligente para desktops) ou manualmente, através do número de matrícula do participante.
- **Gestão de Eventos:** Crie eventos e inscreva participantes a partir da base geral, com controle de vagas e listas de presentes, inscritos e de espera.
- **Sistema de E-mail Completo:**
    - **Envio Automático:** O QR Code é enviado por e-mail assim que um participante é cadastrado manualmente.
    - **Envio Inteligente:** Botão para enviar e-mails apenas para participantes com envios pendentes.
    - **Envio em Massa e Individual:** Opções para reenviar o e-mail para todos os participantes ou para um único indivíduo, conforme a necessidade.
    - **Rastreamento de Envios:** O sistema registra e exibe o status de envio do e-mail para cada participante.
- **Exportação de Dados:** Exporte a lista de presença de um evento para um arquivo CSV.
- **Suporte a HTTPS local:** Roda em um servidor de desenvolvimento seguro para permitir o uso da câmera em navegadores modernos.

## Tecnologias Utilizadas

- **Backend:** Python, Django
- **Frontend:** HTML, Tailwind CSS
- **Bibliotecas Python:**
  - `pandas` para manipulação de arquivos CSV.
  - `qrcode` e `pillow` para geração das imagens de QR Code.
  - `django-extensions`, `werkzeug`, `pyOpenSSL` para rodar um servidor de desenvolvimento com HTTPS.
  - `python-dotenv` para gerenciar variáveis de ambiente de forma segura.

---

## Pré-requisitos

Antes de começar, garanta que você tem os seguintes softwares instalados:
- [Python 3.8+](https://www.python.org/)
- [Git](https://git-scm.com/)
- `pip` e `venv` (geralmente inclusos no Python)

## Instalação e Configuração

Siga os passos abaixo para configurar o ambiente de desenvolvimento.

**1. Clone o Repositório**
```bash
git clone <url-do-seu-repositorio>
cd <nome-da-pasta-do-projeto>
```

**2. Crie e Ative um Ambiente Virtual**
```bash
# Para Windows
python -m venv venv
.\venv\Scripts\activate

# Para macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Instale as Dependências**
Crie um arquivo `requirements.txt` na raiz do projeto com o seguinte conteúdo:
```
Django
pandas
qrcode
pillow
django-extensions
werkzeug
pyOpenSSL
python-dotenv
```
Em seguida, instale todas as dependências com um único comando:
```bash
pip install -r requirements.txt
```

**4. Execute as Migrações do Banco de Dados**
```bash
python manage.py migrate
```

**5. Crie um Superusuário**
```bash
python manage.py createsuperuser
```

**6. Gere o Certificado SSL Local (para HTTPS)**
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj "/CN=localhost"
```

---

## Configuração para Envio de E-mails (Gmail)

Para testar o envio de e-mails, configure o sistema para usar um servidor SMTP do Gmail.

**1. Gere uma "Senha de App" no Google**
Por segurança, o Google exige uma senha específica para aplicações.
- **Ative a Verificação em Duas Etapas** na sua Conta Google.
- Vá para a página de **[Senhas de App](https://myaccount.google.com/apppasswords)**.
- Selecione "E-mail" como app e "Computador Windows" como dispositivo, e clique em **Gerar**.
- **Copie a senha de 16 caracteres gerada**. Você usará esta senha, e não a sua senha principal do Gmail.

**2. Crie um Arquivo `.env` para as Credenciais**
Nunca coloque senhas diretamente no código.
- Na raiz do projeto, crie um arquivo chamado `.env`.
- Adicione suas credenciais a ele:
  ```
  # .env
  EMAIL_HOST_USER='seu-email@gmail.com'
  EMAIL_HOST_PASSWORD='sua-senha-de-app-de-16-caracteres'
  ```

**3. Adicione os Arquivos Sensíveis ao `.gitignore`**
Garanta que suas chaves e senhas não sejam enviadas para o Git. Abra ou crie o arquivo `.gitignore` e adicione as seguintes linhas:
```
# Arquivos de ambiente
.env

# Certificados SSL de desenvolvimento
*.pem
```

**4. Configure o `settings.py`**
No seu arquivo `settings.py`, adicione o código para carregar as variáveis de ambiente e configurar o serviço de e-mail.
```python
# settings.py

import os
from dotenv import load_dotenv
from pathlib import Path # Certifique-se que Path está importado

# ...
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv(os.path.join(BASE_DIR, '.env'))
# ...

# CONFIGURAÇÃO DE E-MAIL
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
```

---

## Como Rodar a Aplicação

**1. Inicie o Servidor de Desenvolvimento**
O endereço `0.0.0.0` torna o servidor acessível para outros dispositivos na mesma rede (como seu celular).
```bash
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
```

**2. Acesse a Aplicação**
- **No seu computador:** `https://localhost:8000`
- **Em outro dispositivo na mesma rede:** `https://<ip-do-seu-computador>:8000`

> **Aviso de Segurança:** O navegador exibirá um alerta de "conexão não particular". Isso é esperado. Clique em "Avançado" e depois em "Ir para o site (não seguro)" para continuar.

**3. Painel de Administração**
Acesse em `https://localhost:8000/admin` e faça login com o superusuário criado.
