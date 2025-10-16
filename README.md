# Sistema de Check-in para Eventos com QR Code

Este é um sistema desenvolvido em Django para a gestão de check-in em eventos. A aplicação permite cadastrar participantes, gerar QR Codes únicos para cada um, gerenciar eventos e realizar o check-in de forma rápida utilizando a câmera de um computador ou totem.

## Funcionalidades Principais

- **Gestão de Participantes:** Cadastro manual ou em massa via upload de arquivo CSV.
- **QR Codes Permanentes:** Geração automática de um QR Code único para cada participante no momento do cadastro.
- **Gestão de Eventos:** Crie eventos e inscreva participantes a partir da base geral.
- **Check-in em Tempo Real:** Uma página de "totem" que usa a câmera para ler os QR Codes e registrar a presença instantaneamente.
- **Controle de Vagas e Listas:** Gestão de presentes, inscritos aguardando e lista de espera.
- **Exportação de Dados:** Exporte a lista de presença de um evento para um arquivo CSV.
- **Envio de QR Code por E-mail:** Funcionalidade para enviar o QR Code permanente para todos os participantes cadastrados.
- **Suporte a HTTPS local:** Roda em um servidor de desenvolvimento seguro para permitir o uso da câmera em navegadores modernos.

## Tecnologias Utilizadas

- **Backend:** Python, Django
- **Frontend:** HTML, Tailwind CSS
- **Bibliotecas Python:**
  - `pandas` para manipulação de arquivos CSV.
  - `qrcode` e `pillow` para geração das imagens de QR Code.
  - `django-extensions`, `werkzeug`, `pyOpenSSL` para rodar um servidor de desenvolvimento com suporte a HTTPS.

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

**2. Crie e Ative um Ambiente Virtual (Virtual Environment)**
É uma boa prática isolar as dependências do projeto.
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
```
Em seguida, instale todas as dependências com um único comando:
```bash
pip install -r requirements.txt
```

**4. Execute as Migrações do Banco de Dados**
Este comando cria o arquivo de banco de dados (`db.sqlite3`) e as tabelas necessárias.
```bash
python manage.py migrate
```

**5. Crie um Superusuário**
Você precisará de um usuário administrador para acessar o painel de controle do Django.
```bash
python manage.py createsuperuser
```
Siga as instruções para criar seu usuário.

**6. Gere o Certificado SSL Local**
Para que o navegador permita o acesso à câmera, o site precisa ser servido via HTTPS. Este comando cria um certificado autoassinado válido por 1 ano, apenas para desenvolvimento.
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj "/CN=localhost"
```
**Importante:** Adicione `*.pem` ao seu arquivo `.gitignore` para não enviar as chaves para o repositório.

## Uso

**1. Inicie o Servidor de Desenvolvimento**
Use o comando abaixo para iniciar o servidor seguro. O endereço `0.0.0.0` torna o servidor acessível para outros dispositivos na mesma rede (como seu celular).
```bash
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
```

**2. Acesse a Aplicação**
- **No seu computador:** Abra o navegador e acesse `https://localhost:8000` ou `https://127.0.0.1:8000`
- **Em outro dispositivo na mesma rede (ex: celular):** Acesse `https://<ip-do-seu-computador>:8000`

> **Aviso de Segurança:** O navegador exibirá um alerta de "conexão não particular". Isso é esperado. Clique em "Avançado" e depois em "Ir para o site (não seguro)" para continuar.

**3. Painel de Administração**
Para gerenciar eventos e ver os modelos de dados diretamente, acesse o painel de administração em `https://localhost:8000/admin` e faça login com o superusuário criado anteriormente.
