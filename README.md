# Guardian del Diván

Este bot de Telegram gestiona suscripciones y requiere un token para funcionar.

## Instalación

1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Copia `.env.example` a `.env` y añade tu `BOT_TOKEN` de Telegram:
   ```bash
   cp .env.example .env
   echo "BOT_TOKEN=TU_TOKEN_AQUI" >> .env
   ```

## Ejecución

Inicia el bot ejecutando `python main.py`. Si `BOT_TOKEN` no está definido se
mostrará un error indicando cómo configurarlo.

