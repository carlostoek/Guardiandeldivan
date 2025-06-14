MESSAGES = {
    "access_denied": "⛔ Acceso denegado",
    "start": "👋 Bienvenido. Contacta con un administrador para obtener un token y luego selecciona una opción:",
    "gen_token_usage": "📝 Uso: /gen_token <1d|1w|2w|1m|forever>",
    "gen_token_result": "🔗 Enlace de acceso: {link}\nVálido por {days} días.",
    "join_token_missing": "🔑 Debes proporcionar el token",
    "join_token_invalid": "❌ Token inválido o expirado",
    "join_success": "✅ Acceso concedido al canal: {link}",
    "add_sub_usage": "📝 Uso: /add_sub <user_id> <duracion>",
    "add_sub_user_id_numeric": "⚠️ user_id debe ser numérico",
    "add_sub_success": "✅ Suscripción creada para {user_id}. Token: {token}",
    "remove_sub_usage": "📝 Uso: /remove_sub <user_id>",
    "remove_sub_user_id_numeric": "⚠️ user_id debe ser numérico",
    "remove_sub_success": "✅ Suscripción eliminada",
    "list_subs_none": "ℹ️ No hay suscriptores activos",
    "set_rate_usage": "📝 Uso: /set_rate <dias> <monto>",
    "set_rate_invalid": "⚠️ Valores inválidos",
    "set_rate_saved": "✅ Tarifa guardada: cada {days} días por {amount}",
    "set_rate_prompt": "📝 Envía la tarifa en formato <dias> <monto>:",
    "broadcast_usage": "📝 Uso: /broadcast <mensaje>",
    "broadcast_sent": "✅ Mensaje enviado a {sent} usuarios",
    "broadcast_prompt": "📝 Envía el mensaje a todos los suscriptores:",
    "list_tokens_usage": "📝 Uso: /list_tokens [user_id] [desde] [hasta]",
    "list_tokens_none": "ℹ️ No se encontraron tokens",
    "gen_link_usage": "📝 Uso: /gen_link <user_id> <duracion>",
    "gen_link_user_id_numeric": "⚠️ user_id debe ser numérico",
    "gen_link_result": "🔗 Enlace de acceso: {link}",
    "admin_help": (
        "ℹ️ <b>Comandos admin</b>:\n"
        "/add_sub <user_id> <duracion> - Alta manual\n"
        "/remove_sub <user_id> - Baja manual\n"
        "/list_subs - Listar suscriptores activos\n"
        "/set_rate <dias> <monto> - Configurar tarifa\n"
        "/broadcast <mensaje> - Enviar mensaje a todos"
    ),
    "help": (
        "ℹ️ <b>Comandos disponibles</b>:\n"
        "/start - Mensaje de bienvenida\n"
        "/join <token> - Unirte al canal con un token válido\n"
        "/stats - Estadísticas básicas\n"
        "/help - Mostrar esta ayuda\n"
        "/menu - Mostrar menú de botones"
    ),
    "menu_prompt": "📋 Selecciona una opción:",
    "notify_admins": "🔔 Se ha notificado a los administradores, recibirás tu token pronto",
    "config_menu": "⚙️ Menú de configuración:",
    "admin_menu": "🔒 Menú de administración:",
    "token_duration_menu": "🕒 Elige duración para el token:",
    "subscriber_not_found": "❌ Suscriptor no encontrado",
    "user_removed": "✅ Usuario expulsado",
    "token_generated": "🔗 Enlace generado:\n{link}\nVálido por {days} días",
    "add_sub_menu_usage": "📝 Uso: /add_sub <user_id> <duracion>",
    "remove_sub_menu_usage": "📝 Uso: /remove_sub <user_id>",
    "join_menu_usage": "📝 Uso: /join <token>",
    "stats_template": (
        "📊 <b>Estadísticas</b>\n"
        "👥 Suscriptores activos: <b>{total}</b>\n"
        "✅ Entraron esta semana: <b>{joined_week}</b>\n"
        "❌ Salieron esta semana: <b>{left_week}</b>\n"
        "👍 Reacciones totales: <b>{reactions}</b>"
    ),
}
