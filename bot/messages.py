"""Text templates for bot replies."""

# Default notification messages
DEFAULT_REMINDER_MSG = "Tu suscripción expirará mañana."
DEFAULT_EXPIRATION_MSG = "Tu suscripción ha expirado."

# General
ADMIN_ONLY = "No tienes permiso para usar este comando"
INVALID_TOKEN = "Token inválido"

# Usage strings
GEN_TOKEN_USAGE = "Uso: /gen_token &lt;días&gt;"
TOKEN_USAGE = "Uso: /join &lt;token&gt;"
BROADCAST_USAGE = "Uso: /broadcast &lt;texto&gt;"
ADD_SUB_USAGE = "Uso: /add_sub &lt;@user&gt; &lt;días&gt;"
REMOVE_SUB_USAGE = "Uso: /remove_sub &lt;@user&gt;"
SET_REMINDER_USAGE = "Uso: /set_reminder &lt;texto&gt;"
SET_EXPIRATION_USAGE = "Uso: /set_expiration &lt;texto&gt;"

# Success / info messages
TOKEN_GENERATED = "Token generado: <code>{token}</code>"
SUB_ACTIVATED = "Suscripción activada por {duration} días"
SUB_ACTIVATED_WITH_LINK = (
    "Suscripción activada por {duration} días.\nInvitación: {invite}"
)
ADMIN_MENU = "Menú de administración"
SUBSCRIBER_MENU = "Menú de suscriptor"
SUBSCRIPTION_MENU = "Menú de suscripción"
NOT_REGISTERED = (
    "No estás registrado. Solicita un token y envía /start &lt;token&gt; para suscribirte."
)
BROADCAST_SENT = "Mensaje enviado a {count} usuarios"
USER_NOT_FOUND = "Usuario no encontrado"
SUB_ADDED = "Suscripción añadida por {days} días para @{username}"
SUB_REMOVED = "Suscripción eliminada para @{username}"
REMINDER_UPDATED = "Mensaje de recordatorio actualizado"
EXPIRATION_UPDATED = "Mensaje de expiración actualizado"
# Admin menus
SETTINGS_MENU = "Menú de configuración"
ADMINISTRATION_MENU = "Herramientas de administración"
PRICE_UPDATED = "Precio actualizado: {period} - {amount}"
CURRENT_PRICE = "Precio actual: {period} - {amount}"
STATS_OVERVIEW = (
    "Suscriptores activos: {active}\nRenovaciones: {renewals}\nIngresos estimados: {revenue}"
)
BROADCAST_INSTRUCTIONS = "Envía /broadcast <texto> para enviar un mensaje a todos los suscriptores"
ACCESS_LINK = "Enlace de acceso: {link}"
SUBSCRIBER_INFO = (
    "Usuario {user_id}\nInicio: {start}\nExpira: {end}\nTotal: {days} días\nRenovaciones: {renewals}"
)
USER_REMOVED = "Usuario {user_id} eliminado"
