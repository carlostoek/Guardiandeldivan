# Guardiandeldivan
Un bot de Telegram para administrar un canal de pago mediante suscripciones.

## Requisitos

- Python 3.8+
- Dependencias listadas en `requirements.txt`

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

## Despliegue en Railway

1. Crea un proyecto en [Railway](https://railway.app/).
2. Configura en el panel las variables de entorno `BOT_TOKEN`, `CHANNEL_ID` y `ADMIN_IDS`.
3. El repositorio incluye un `Procfile` con el comando necesario para iniciar el bot:

   ```
   worker: python -m bot.main
   ```

Al desplegar, Railway utilizará este archivo automáticamente para ejecutar el bot.

## Uso rápido

Crea las variables de entorno `BOT_TOKEN` (token de tu bot), `CHANNEL_ID` (ID del canal a administrar) y `ADMIN_IDS` (lista de IDs de administradores separada por comas). Luego ejecuta:

```bash
python -m bot.main
```

## Estructura

- `bot/main.py` - Punto de entrada del bot
- `bot/database.py` - Funciones de acceso a base de datos SQLite
- `bot/token_manager.py` - Generación y validación de tokens de suscripción

### Comandos de administración

- `/admin` muestra la ayuda de administradores.
- `/gen_token <duracion>` genera un token.
- `/add_sub <user_id> <duracion>` da de alta a un usuario manualmente.
- `/remove_sub <user_id>` da de baja a un usuario.
- `/list_subs` lista los usuarios activos con su fecha de entrada.

## Notas de desarrollo

El bot gestiona usuarios, fechas de ingreso y expiración de suscripciones. Envía recordatorios por privado y expulsa del canal cuando la suscripción expira. Los administradores podrán consultar estadísticas básicas.
