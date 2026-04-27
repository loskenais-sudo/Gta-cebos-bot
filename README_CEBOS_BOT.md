# 🤖 Bot de Discord - GTA V Roleplay - Sistema de Cebos

Un bot completo para gestionar la distribución de cebos en tu servidor de GTA V roleplay con Discord, incluyendo límite de 50 cebos por día por usuario y sistema de vetados.

## 📋 Características

✅ **Gestión de Cebos**
- Límite de 50 cebos por día por usuario
- Reseteo automático de cebos a medianoche
- Seguimiento de historial de transacciones
- Información de nombre y apellido (pueden repetirse, pero el ID es único)

✅ **Sistema de Vetado**
- Vetado temporal (especificar días)
- Vetado permanente
- Desvetado manual
- Expiración automática de vetos temporales

✅ **Base de Datos**
- Almacenamiento en JSON (fácil de editar y revisar)
- Persistencia de datos
- Historial completo de transacciones

---

## 🔧 Instalación

### 1. **Requisitos Previos**
- Python 3.8+
- pip (gestor de paquetes de Python)

### 2. **Instalar Dependencias**

```bash
pip install discord.py
```

### 3. **Obtener Token de Discord**

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Clic en "New Application" y dale un nombre
3. En la pestaña "Bot", haz clic en "Add Bot"
4. En "TOKEN", copia el token
5. Bajo "SCOPES", selecciona: `bot`
6. Bajo "PERMISSIONS", selecciona:
   - Send Messages
   - Embed Links
   - Read Message History
   - View Channels

7. Copia la URL de invitación generada y úsala para añadir el bot a tu servidor

### 4. **Configurar el Bot**

Abre `gta_cebos_bot.py` y reemplaza:
```python
TOKEN = "TU_TOKEN_AQUI"
```
Con tu token real:
```python
TOKEN = "MTA1NzIwNDI0NzU3MDk3NDI2MQ.GxYz_z.abc123xyz..."
```

### 5. **Ejecutar el Bot**

```bash
python gta_cebos_bot.py
```

Deberías ver:
```
✅ Bot conectado como BotName#1234
Comandos disponibles: !cebos, !añadir, !vetar, !desvetar, !info, !ayuda
```

---

## 📝 Comandos Disponibles

### 1. **Verificar Cebos Disponibles**
```
!cebos <ID>
```
**Ejemplo:**
```
!cebos F1603Q49
```
**Resultado:** Muestra cuántos cebos tiene disponibles el usuario hoy

---

### 2. **Añadir Cebos**
```
!añadir <ID> <CANTIDAD>
```
**Ejemplo:**
```
!añadir F1603Q49 5
```
**Resultado:** 
- Si tiene disponibles: Añade 5 cebos y muestra el total
- Si no tiene disponibles: Rechaza y muestra cuántos le faltan

---

### 3. **Vetar Usuario - Temporal**
```
!vetar <ID> temporal <MOTIVO> <DÍAS>
```
**Ejemplo:**
```
!vetar F1603Q49 temporal Comportamiento inapropiado 7
```
**Resultado:** Usuario vetado durante 7 días. Después se autodesvetará.

---

### 4. **Vetar Usuario - Permanente**
```
!vetar <ID> permanente <MOTIVO>
```
**Ejemplo:**
```
!vetar F1603Q49 permanente Abuso del sistema
```
**Resultado:** Usuario vetado permanentemente

---

### 5. **Desvetar Usuario**
```
!desvetar <ID>
```
**Ejemplo:**
```
!desvetar F1603Q49
```
**Resultado:** Usuario devetado (puede volver a comprar cebos)

---

### 6. **Ver Información del Usuario**
```
!info <ID>
```
**Ejemplo:**
```
!info F1603Q49
```
**Resultado:** 
- ID
- Cebos usados hoy
- Historial de transacciones
- Detalles de veto (si aplica)

---

### 7. **Ayuda**
```
!ayuda
```
Muestra todos los comandos disponibles

---

## 🔐 Permisos

- **!cebos, !añadir, !info, !ayuda**: Cualquiera puede usar
- **!vetar, !desvetar**: Solo administradores del servidor

---

## 📊 Estructura de la Base de Datos

El bot crea automáticamente un archivo `cebos_data.json` con esta estructura:

```json
{
    "usuarios": {
        "F1603Q49": {
            "nombre": "Juan",
            "apellido": "García",
            "cebos_hoy": 25,
            "fecha_actual": "2024-01-15",
            "historial": [
                {
                    "fecha": "2024-01-15T14:30:00",
                    "cantidad": 5,
                    "total_diario": 5
                },
                {
                    "fecha": "2024-01-15T15:45:00",
                    "cantidad": 20,
                    "total_diario": 25
                }
            ]
        }
    },
    "vetados": {
        "F1603Q49": {
            "motivo": "Comportamiento inapropiado",
            "tipo": "temporal",
            "hasta": "2024-01-22T14:30:00",
            "fecha_veto": "2024-01-15T14:30:00"
        }
    }
}
```

---

## ⚠️ Notas Importantes

1. **Reseteo Automático**: Los cebos se resetean a medianoche (00:00) automáticamente
2. **IDs Únicos**: El sistema identifica usuarios por ID único (ej: F1603Q49)
3. **Nombres Repetibles**: Varios usuarios pueden tener el mismo nombre y apellido
4. **Vetos Temporales**: Se autoexpiran después del período especificado
5. **Base de Datos**: Puedes editar manualmente `cebos_data.json` si es necesario

---

## 🐛 Solución de Problemas

### El bot no se conecta
- Comprueba que el TOKEN sea correcto
- Asegúrate de que el bot esté invitado al servidor

### El bot está invitado pero no responde
- Comprueba que tenga permisos "Send Messages" en el canal
- Verifica que el prefijo sea `!` (ej: `!ayuda`)

### Los cebos no se resetean
- El reseteo es automático a medianoche (zona horaria del servidor)
- Puedes editar manualmente `cebos_data.json` para ajustar fechas

---

## 🚀 Mejoras Futuras (Opcional)

Puedes expandir el bot con:
- Base de datos MySQL/PostgreSQL en lugar de JSON
- Panel web para visualizar datos
- Notificaciones automáticas
- Sistema de multas
- Ranking de vendedores
- Comandos de estadísticas

---

## 📧 Soporte

Si tienes problemas, revisa:
1. El archivo `cebos_data.json` (debe existir en el mismo directorio)
2. Los logs de Python para errores
3. Los permisos del bot en el servidor Discord

¡Que disfrutes vendiendo cebos! 🎮
