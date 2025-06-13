# Guardiandeldivan

Un bot de Telegram para administrar un canal de pago mediante suscripciones.

## Requisitos

- Python 3.8+
- Dependencias listadas en `requirements.txt`

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

## Uso rápido

Crea la variable de entorno `BOT_TOKEN` con el token de tu bot y ejecuta:

```bash
python -m bot.main
```

## Estructura

- `bot/main.py` - Punto de entrada del bot
- `bot/database.py` - Funciones de acceso a base de datos SQLite
- `bot/token_manager.py` - Generación y validación de tokens de suscripción

## Notas de desarrollo

El bot gestiona usuarios, fechas de ingreso y expiración de suscripciones. Envía recordatorios por privado y expulsa del canal cuando la suscripción expira. Los administradores podrán consultar estadísticas básicas.
