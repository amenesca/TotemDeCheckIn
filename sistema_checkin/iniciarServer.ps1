# Caminho: iniciar_checkin.ps1


# Ativar o ambiente Conda
conda activate TotemCheckin

# Executar o servidor Django com HTTPS
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
