# TotemDeCheckIn

Necessita de Django

Pacotes utilizados
pip install django pandas qrcode pillow django-extensions werkzeug pyOpenSSL

Criar certificado autoassinado
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj "/CN=localhost"

Rodar Servidor Aberto
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000