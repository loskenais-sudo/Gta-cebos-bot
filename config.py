# ⚙️ CONFIGURACIÓN DEL BOT DE CEBOS

# 🔑 Token de Discord (IMPORTANTE: Mantén esto privado)
DISCORD_TOKEN = "TU_TOKEN_AQUI"

# 🎮 Configuración de Cebos
CEBOS_LIMIT = 50  # Límite de cebos por día
COMMAND_PREFIX = "!"  # Prefijo de comandos (ej: !ayuda)

# 📊 Configuración de Base de Datos
DATABASE_FILE = "cebos_data.json"

# 🌍 Zona Horaria
# Formato: "America/New_York", "Europe/Madrid", "America/Mexico_City", etc.
TIMEZONE = "Europe/Madrid"

# 🎨 Colores de Embeds (Color scheme de Discord)
COLOR_SUCCESS = 0x00FF00    # Verde
COLOR_ERROR = 0xFF0000      # Rojo
COLOR_INFO = 0x0000FF       # Azul
COLOR_WARNING = 0xFFA500    # Naranja
COLOR_VETO = 0x8B0000       # Rojo oscuro

# 🚫 Configuración de Vetados
AUTO_DELETE_EXPIRED_BANS = True  # Eliminar automáticamente vetos expirados
LOG_BANS = True                   # Registrar todos los vetados en un log

# 📝 Mensajes Personalizables
MENSAJE_CEBOS_AGOTADOS = "❌ No puedes coger más cebos hoy. Límite: 50"
MENSAJE_USUARIO_VETADO = "🚫 Este usuario está vetado y no puede comprar cebos"
MENSAJE_USUARIO_CREADO = "✅ Usuario registrado correctamente"

# 👨‍💼 Configuración de Administración
# Si establecer a False, todos pueden usar comandos de admin
REQUIRE_ADMIN_FOR_BANS = True
REQUIRE_ADMIN_FOR_DELETE = True

# 📋 Auditoría
LOG_ALL_TRANSACTIONS = True  # Registrar todas las transacciones
LOG_FILE = "audit_log.txt"   # Archivo de log de auditoría
