import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz
from pymongo import MongoClient

# Zona horaria de España
TZ_SPAIN = pytz.timezone('Europe/Madrid')

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Límite de cebos por día
CEBOS_LIMIT = 50

class CebosDatabase:
    """Gestiona la base de datos de cebos con MongoDB"""

    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError("❌ Error: No se encontró la variable 'MONGO_URI' en Railway")
        client = MongoClient(mongo_uri)
        db = client["cebos_bot"]
        self.usuarios = db["usuarios"]
        self.vetados = db["vetados"]

    # ── Utilidades de tiempo ──────────────────────────────────────────────────

    def now_spain(self) -> datetime:
        return datetime.now(TZ_SPAIN)

    def today_spain(self) -> str:
        return self.now_spain().strftime('%Y-%m-%d')

    def tiempo_hasta_reset(self) -> str:
        """Devuelve el tiempo restante hasta las 08:40 hora España"""
        ahora = self.now_spain()
        reset_hoy = ahora.replace(hour=8, minute=40, second=0, microsecond=0)
        if ahora >= reset_hoy:
            reset_hoy += timedelta(days=1)
        diff = reset_hoy - ahora
        horas, resto = divmod(int(diff.total_seconds()), 3600)
        minutos = resto // 60
        return f"{horas}h {minutos}min"

    # ── Usuarios ──────────────────────────────────────────────────────────────

    def get_usuario_info(self, user_id: str) -> Optional[dict]:
        return self.usuarios.find_one({"_id": user_id})

    def tiene_nombre(self, user_id: str) -> bool:
        doc = self.get_usuario_info(user_id)
        if not doc:
            return False
        return bool(doc.get('nombre', '').strip() or doc.get('apellido', '').strip())

    def crear_usuario(self, user_id: str, nombre: str, apellido: str) -> dict:
        today = self.today_spain()
        doc = self.get_usuario_info(user_id)
        if not doc:
            doc = {
                "_id": user_id,
                "nombre": nombre,
                "apellido": apellido,
                "cebos_hoy": 0,
                "fecha_actual": today,
                "historial": []
            }
            self.usuarios.insert_one(doc)
        else:
            update = {}
            if doc.get('fecha_actual') != today:
                update["cebos_hoy"] = 0
                update["fecha_actual"] = today
            if nombre:
                update["nombre"] = nombre
            if apellido:
                update["apellido"] = apellido
            if update:
                self.usuarios.update_one({"_id": user_id}, {"$set": update})
            doc = self.get_usuario_info(user_id)
        return doc

    def set_nombre(self, user_id: str, nombre: str, apellido: str) -> str:
        today = self.today_spain()
        doc = self.get_usuario_info(user_id)
        if not doc:
            self.usuarios.insert_one({
                "_id": user_id,
                "nombre": nombre,
                "apellido": apellido,
                "cebos_hoy": 0,
                "fecha_actual": today,
                "historial": []
            })
        else:
            self.usuarios.update_one(
                {"_id": user_id},
                {"$set": {"nombre": nombre, "apellido": apellido}}
            )
        return f"✅ Nombre registrado: **{nombre} {apellido}** para el ID `{user_id}`"

    def get_cebos_disponibles(self, user_id: str) -> Tuple[int, int]:
        doc = self.get_usuario_info(user_id)
        if not doc:
            return 0, CEBOS_LIMIT
        today = self.today_spain()
        if doc.get('fecha_actual') != today:
            self.usuarios.update_one(
                {"_id": user_id},
                {"$set": {"cebos_hoy": 0, "fecha_actual": today}}
            )
            doc["cebos_hoy"] = 0
        cebos_usados = doc.get('cebos_hoy', 0)
        return cebos_usados, max(0, CEBOS_LIMIT - cebos_usados)

    def añadir_cebos(self, user_id: str, cantidad: int) -> Tuple[bool, str]:
        doc = self.get_usuario_info(user_id)
        if not doc:
            return False, "Usuario no encontrado"
        cebos_usados, cebos_disponibles = self.get_cebos_disponibles(user_id)
        if cantidad > cebos_disponibles:
            return False, f"No puedes coger {cantidad} cebos. Solo tienes {cebos_disponibles} disponibles hoy."
        nuevo_total = cebos_usados + cantidad
        entrada = {
            "fecha": self.now_spain().isoformat(),
            "cantidad": cantidad,
            "total_diario": nuevo_total
        }
        self.usuarios.update_one(
            {"_id": user_id},
            {"$set": {"cebos_hoy": nuevo_total}, "$push": {"historial": entrada}}
        )
        return True, f"✅ Se han añadido {cantidad} cebos. Total hoy: {nuevo_total}/{CEBOS_LIMIT}"

    def reset_todos_cebos(self):
        today = self.today_spain()
        self.usuarios.update_many({}, {"$set": {"cebos_hoy": 0, "fecha_actual": today}})

    # ── Vetos ─────────────────────────────────────────────────────────────────

    def vetar_usuario(self, user_id: str, motivo: str, tipo: str = 'permanente', dias: int = 0) -> str:
        if tipo not in ['temporal', 'permanente']:
            return "Tipo de veto inválido. Use 'temporal' o 'permanente'"
        if tipo == 'temporal' and dias <= 0:
            return "Para vetos temporales, especifique días > 0"
        fecha_veto = self.now_spain()
        fecha_hasta = (fecha_veto + timedelta(days=dias)).isoformat() if tipo == 'temporal' else None
        self.vetados.update_one(
            {"_id": user_id},
            {"$set": {
                "motivo": motivo,
                "tipo": tipo,
                "hasta": fecha_hasta,
                "fecha_veto": fecha_veto.isoformat()
            }},
            upsert=True
        )
        tipo_texto = f"temporal ({dias} días)" if tipo == 'temporal' else "permanente"
        return f"✅ Usuario {user_id} vetado {tipo_texto}. Motivo: {motivo}"

    def desvetar_usuario(self, user_id: str) -> str:
        result = self.vetados.delete_one({"_id": user_id})
        if result.deleted_count == 0:
            return f"El usuario {user_id} no está vetado"
        return f"✅ Usuario {user_id} desvetado"

    def check_veto(self, user_id: str) -> Tuple[bool, str]:
        veto = self.vetados.find_one({"_id": user_id})
        if not veto:
            return False, ""
        if veto['tipo'] == 'temporal' and veto.get('hasta'):
            fecha_hasta = datetime.fromisoformat(veto['hasta'])
            if self.now_spain() > fecha_hasta:
                self.vetados.delete_one({"_id": user_id})
                return False, ""
            dias_restantes = (fecha_hasta - self.now_spain()).days
            return True, f"🚫 Usuario vetado temporalmente por: {veto['motivo']}. Días restantes: {dias_restantes}"
        return True, f"🚫 Usuario vetado permanentemente por: {veto['motivo']}"

    def get_lista_vetados(self) -> list:
        resultado = []
        for veto in self.vetados.find():
            user_id = veto['_id']
            if veto['tipo'] == 'temporal' and veto.get('hasta'):
                fecha_hasta = datetime.fromisoformat(veto['hasta'])
                if self.now_spain() > fecha_hasta:
                    continue
            doc = self.get_usuario_info(user_id)
            if doc:
                nombre = doc.get('nombre', '').strip()
                apellido = doc.get('apellido', '').strip()
                nombre_completo = f"{nombre} {apellido}".strip() if (nombre or apellido) else "⚠️ Sin nombre"
            else:
                nombre_completo = "⚠️ Sin nombre"
            resultado.append({
                'id': user_id,
                'nombre': nombre_completo,
                'tipo': veto['tipo'],
                'motivo': veto['motivo'],
                'hasta': veto.get('hasta'),
            })
        return resultado


# Instancia de la base de datos
db = CebosDatabase()

# ── Task reset diario ─────────────────────────────────────────────────────────

@tasks.loop(minutes=1)
async def tarea_reset_diario():
    """Comprueba cada minuto si son las 08:40 hora España y resetea los cebos"""
    ahora = datetime.now(TZ_SPAIN)
    if ahora.hour == 8 and ahora.minute == 40:
        db.reset_todos_cebos()
        print(f"✅ Cebos reseteados automáticamente a las 08:40 (hora España) — {ahora.strftime('%Y-%m-%d')}")

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print('Comandos disponibles: !cebos, !añadir, !vetar, !desvetar, !usuario, !nombre, !vetados, !ayuda')
    if not tarea_reset_diario.is_running():
        tarea_reset_diario.start()

# ── Comandos ──────────────────────────────────────────────────────────────────

@bot.command(name='cebos')
async def check_cebos(ctx, user_id: str):
    vetado, msg_veto = db.check_veto(user_id)
    if vetado:
        embed = discord.Embed(title="❌ Usuario Vetado", description=msg_veto, color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    usuario = db.get_usuario_info(user_id)
    if not usuario:
        usuario = db.crear_usuario(user_id, "", "")

    cebos_usados, cebos_disponibles = db.get_cebos_disponibles(user_id)
    nombre = usuario.get('nombre', '').strip()
    apellido = usuario.get('apellido', '').strip()
    nombre_completo = f"{nombre} {apellido}".strip() if (nombre or apellido) else None

    embed = discord.Embed(title="📊 Estado de Cebos", color=discord.Color.blue())
    embed.add_field(name="ID Usuario", value=user_id, inline=False)
    if nombre_completo:
        embed.add_field(name="Nombre", value=nombre_completo, inline=False)
    else:
        embed.add_field(
            name="⚠️ Sin nombre registrado",
            value=f"Usa `!nombre {user_id} Nombre Apellido` para registrar el nombre de este usuario.",
            inline=False
        )
    embed.add_field(name="Cebos Usados Hoy", value=f"🟢 {cebos_usados}", inline=True)
    embed.add_field(name="Cebos Disponibles", value=f"🔵 {cebos_disponibles}", inline=True)
    embed.add_field(name="Límite Diario", value=f"⚫ {CEBOS_LIMIT}", inline=True)
    embed.add_field(name="⏰ Reset en", value=db.tiempo_hasta_reset(), inline=False)
    embed.set_footer(text=f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)


@bot.command(name='añadir')
async def add_cebos(ctx, user_id: str, cantidad: int):
    vetado, msg_veto = db.check_veto(user_id)
    if vetado:
        embed = discord.Embed(
            title="❌ Usuario Vetado — Cebos NO añadidos",
            description=f"{msg_veto}\n\nNo se pueden añadir cebos a un usuario vetado.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if cantidad <= 0:
        await ctx.send("❌ La cantidad debe ser mayor a 0")
        return

    if not db.get_usuario_info(user_id):
        db.crear_usuario(user_id, "", "")

    éxito, mensaje = db.añadir_cebos(user_id, cantidad)
    color = discord.Color.green() if éxito else discord.Color.red()
    icon = "✅" if éxito else "❌"

    embed = discord.Embed(title=f"{icon} Resultado", description=mensaje, color=color)
    embed.add_field(name="Usuario", value=user_id, inline=False)

    if éxito and not db.tiene_nombre(user_id):
        embed.add_field(
            name="⚠️ Sin nombre registrado",
            value=f"Usa `!nombre {user_id} Nombre Apellido` para registrar el nombre de este usuario.",
            inline=False
        )

    if éxito:
        cebos_usados, cebos_disponibles = db.get_cebos_disponibles(user_id)
        embed.add_field(name="Cebos Usados Hoy", value=cebos_usados, inline=True)
        embed.add_field(name="Cebos Disponibles", value=cebos_disponibles, inline=True)

    await ctx.send(embed=embed)


@bot.command(name='nombre')
async def set_nombre(ctx, user_id: str, nombre: str, apellido: str):
    mensaje = db.set_nombre(user_id, nombre, apellido)
    embed = discord.Embed(title="✏️ Nombre Actualizado", description=mensaje, color=discord.Color.green())
    embed.set_footer(text=f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)


@bot.command(name='usuario')
async def user_info(ctx, user_id: str):
    usuario = db.get_usuario_info(user_id)
    if not usuario:
        await ctx.send(f"❌ Usuario `{user_id}` no encontrado en la base de datos")
        return

    vetado, msg_veto = db.check_veto(user_id)
    cebos_usados, cebos_disponibles = db.get_cebos_disponibles(user_id)
    nombre = usuario.get('nombre', '').strip()
    apellido = usuario.get('apellido', '').strip()
    nombre_completo = f"{nombre} {apellido}".strip() if (nombre or apellido) else None

    embed = discord.Embed(title="👤 Información del Usuario", color=discord.Color.purple())
    embed.add_field(name="ID", value=user_id, inline=False)
    if nombre_completo:
        embed.add_field(name="Nombre Completo", value=nombre_completo, inline=False)
    else:
        embed.add_field(
            name="⚠️ Sin nombre registrado",
            value=f"Usa `!nombre {user_id} Nombre Apellido` para registrar el nombre de este usuario.",
            inline=False
        )
    embed.add_field(name="Estado", value="🚫 Vetado" if vetado else "✅ Activo", inline=True)
    embed.add_field(name="Cebos Hoy", value=f"{cebos_usados}/{CEBOS_LIMIT}", inline=True)
    embed.add_field(name="⏰ Reset en", value=db.tiempo_hasta_reset(), inline=True)
    embed.add_field(name="Historial de Transacciones",
                    value=f"Total: {len(usuario.get('historial', []))} transacciones",
                    inline=False)
    if vetado:
        embed.add_field(name="Detalles de Veto", value=msg_veto, inline=False)
    await ctx.send(embed=embed)


@bot.command(name='vetar')
async def ban_user(ctx, user_id: str, tipo: str, *, detalles: str):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Solo administradores pueden vetar usuarios")
        return

    tipo = tipo.lower()
    if tipo == 'temporal':
        try:
            partes = detalles.rsplit(' ', 1)
            if len(partes) != 2:
                await ctx.send("❌ Formato: !vetar ID temporal MOTIVO DÍAS")
                return
            motivo = partes[0]
            dias = int(partes[1])
            mensaje = db.vetar_usuario(user_id, motivo, 'temporal', dias)
        except ValueError:
            await ctx.send("❌ Los días deben ser un número")
            return
    elif tipo == 'permanente':
        mensaje = db.vetar_usuario(user_id, detalles, 'permanente')
    else:
        await ctx.send("❌ Tipo debe ser 'temporal' o 'permanente'")
        return

    embed = discord.Embed(title="🚫 Usuario Vetado", description=mensaje, color=discord.Color.red())
    embed.set_footer(text=f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)


@bot.command(name='desvetar')
async def unban_user(ctx, user_id: str):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Solo administradores pueden desvetar usuarios")
        return

    mensaje = db.desvetar_usuario(user_id)
    color = discord.Color.green() if "✅" in mensaje else discord.Color.red()
    embed = discord.Embed(title="Desvetado", description=mensaje, color=color)
    await ctx.send(embed=embed)


@bot.command(name='vetados')
async def lista_vetados(ctx):
    lista = db.get_lista_vetados()
    if not lista:
        embed = discord.Embed(
            title="✅ No hay usuarios vetados",
            description="No hay ningún usuario vetado actualmente.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title=f"🚫 Usuarios Vetados ({len(lista)})", color=discord.Color.red())
    for v in lista:
        if v['tipo'] == 'temporal' and v['hasta']:
            fecha_hasta = datetime.fromisoformat(v['hasta'])
            dias_restantes = max(0, (fecha_hasta - db.now_spain()).days)
            tipo_str = f"Temporal · {dias_restantes} días restantes"
        else:
            tipo_str = "Permanente"
        embed.add_field(
            name=f"🔴 {v['nombre']} — `{v['id']}`",
            value=f"**Tipo:** {tipo_str}\n**Motivo:** {v['motivo']}",
            inline=False
        )
    embed.set_footer(text=f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)


@bot.command(name='ayuda')
async def help_command(ctx):
    embed = discord.Embed(title="📖 Ayuda - Bot de Cebos GTA V", color=discord.Color.gold())
    embed.add_field(name="!cebos <ID>", value="Comprueba cebos disponibles\nEj: `!cebos F1603Q49`", inline=False)
    embed.add_field(name="!añadir <ID> <CANTIDAD>", value="Añade cebos a un usuario\nEj: `!añadir F1603Q49 5`", inline=False)
    embed.add_field(name="!nombre <ID> <NOMBRE> <APELLIDO>", value="Registra o actualiza el nombre de un usuario\nEj: `!nombre F1603Q49 Nero Kiraman`", inline=False)
    embed.add_field(name="!usuario <ID>", value="Muestra información completa del usuario\nEj: `!usuario F1603Q49`", inline=False)
    embed.add_field(name="!vetar <ID> temporal <MOTIVO> <DÍAS>", value="Veta temporalmente un usuario *(admin)*\nEj: `!vetar F1603Q49 temporal Mal comportamiento 7`", inline=False)
    embed.add_field(name="!vetar <ID> permanente <MOTIVO>", value="Veta permanentemente un usuario *(admin)*\nEj: `!vetar F1603Q49 permanente Estafa`", inline=False)
    embed.add_field(name="!desvetar <ID>", value="Desveta un usuario *(admin)*\nEj: `!desvetar F1603Q49`", inline=False)
    embed.add_field(name="!vetados", value="Muestra la lista de todos los usuarios vetados\nEj: `!vetados`", inline=False)
    embed.set_footer(text="Límite de cebos por día: 50")
    await ctx.send(embed=embed)


# Ejecutar el bot
if __name__ == "__main__":
    # Carga el token desde las variables de entorno de Railway
    TOKEN = os.getenv("TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: No se encontró la variable 'TOKEN' en Railway")
