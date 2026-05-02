import discord
from discord.ext import commands, tasks
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz
import motor.motor_asyncio

# Zona horaria de España
TZ_SPAIN = pytz.timezone('Europe/Madrid')

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Límite de cebos por día
CEBOS_LIMIT = 50

# ── Roles ─────────────────────────────────────────────────────────────────────

# Acceso completo (todos los comandos)
ROLES_ADMIN = {"OWNER", "JEFE", "INSTRUCTOR", "Jefatura"}

# Acceso limitado: !añadir, !nombre, !cebos, !usuario
ROLES_NAUTICS = {"NAUTICS"}

def tiene_rol_admin(member: discord.Member) -> bool:
    """Comprueba si el miembro tiene un rol con acceso completo."""
    return any(rol.name in ROLES_ADMIN for rol in member.roles)

def tiene_rol_nautics(member: discord.Member) -> bool:
    """Comprueba si el miembro tiene el rol NAUTICS."""
    return any(rol.name in ROLES_NAUTICS for rol in member.roles)

def tiene_acceso_basico(member: discord.Member) -> bool:
    """Comprueba si el miembro tiene acceso a los comandos básicos."""
    return tiene_rol_admin(member) or tiene_rol_nautics(member)

# ── Conexión MongoDB (async con motor) ────────────────────────────────────────

mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise RuntimeError("❌ Error: No se encontró la variable 'MONGO_URI' en Railway")

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
mongo_db = mongo_client["cebos_bot"]
col_usuarios = mongo_db["usuarios"]
col_vetados = mongo_db["vetados"]

# ── Utilidades de tiempo ──────────────────────────────────────────────────────

def now_spain() -> datetime:
    return datetime.now(TZ_SPAIN)

def today_spain() -> str:
    return now_spain().strftime('%Y-%m-%d')

def tiempo_hasta_reset() -> str:
    """Devuelve el tiempo restante hasta las 00:00 hora España"""
    ahora = now_spain()
    reset_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    diff = reset_hoy - ahora
    horas, resto = divmod(int(diff.total_seconds()), 3600)
    minutos = resto // 60
    return f"{horas}h {minutos}min"

# ── Funciones de base de datos (todas async) ──────────────────────────────────

async def get_usuario(user_id: str) -> Optional[dict]:
    return await col_usuarios.find_one({"_id": user_id})

async def tiene_nombre(user_id: str) -> bool:
    doc = await get_usuario(user_id)
    if not doc:
        return False
    return bool(doc.get('nombre', '').strip() or doc.get('apellido', '').strip())

async def crear_usuario(user_id: str, nombre: str = "", apellido: str = "") -> dict:
    today = today_spain()
    doc = await get_usuario(user_id)
    if not doc:
        doc = {
            "_id": user_id,
            "nombre": nombre,
            "apellido": apellido,
            "cebos_hoy": 0,
            "fecha_actual": today,
            "historial": []
        }
        await col_usuarios.insert_one(doc)
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
            await col_usuarios.update_one({"_id": user_id}, {"$set": update})
        doc = await get_usuario(user_id)
    return doc

async def set_nombre(user_id: str, nombre: str, apellido: str) -> str:
    today = today_spain()
    doc = await get_usuario(user_id)
    if not doc:
        await col_usuarios.insert_one({
            "_id": user_id,
            "nombre": nombre,
            "apellido": apellido,
            "cebos_hoy": 0,
            "fecha_actual": today,
            "historial": []
        })
    else:
        await col_usuarios.update_one(
            {"_id": user_id},
            {"$set": {"nombre": nombre, "apellido": apellido}}
        )
    return f"✅ Nombre registrado: **{nombre} {apellido}** para el ID `{user_id}`"

async def get_cebos_disponibles(user_id: str) -> Tuple[int, int]:
    doc = await get_usuario(user_id)
    if not doc:
        return 0, CEBOS_LIMIT
    today = today_spain()
    if doc.get('fecha_actual') != today:
        await col_usuarios.update_one(
            {"_id": user_id},
            {"$set": {"cebos_hoy": 0, "fecha_actual": today}}
        )
        doc["cebos_hoy"] = 0
    cebos_usados = doc.get('cebos_hoy', 0)
    return cebos_usados, max(0, CEBOS_LIMIT - cebos_usados)

async def añadir_cebos(user_id: str, cantidad: int, vendedor_id: str = "", vendedor_nombre: str = "") -> Tuple[bool, str]:
    doc = await get_usuario(user_id)
    if not doc:
        return False, "Usuario no encontrado"
    cebos_usados, cebos_disponibles = await get_cebos_disponibles(user_id)
    if cantidad > cebos_disponibles:
        return False, f"No puedes coger {cantidad} cebos. Solo tienes {cebos_disponibles} disponibles hoy."
    nuevo_total = cebos_usados + cantidad
    entrada = {
        "fecha": now_spain().isoformat(),
        "cantidad": cantidad,
        "total_diario": nuevo_total,
        "vendedor_id": vendedor_id,
        "vendedor_nombre": vendedor_nombre
    }
    await col_usuarios.update_one(
        {"_id": user_id},
        {"$set": {"cebos_hoy": nuevo_total}, "$push": {"historial": entrada}}
    )
    return True, f"✅ Se han añadido {cantidad} cebos. Total hoy: {nuevo_total}/{CEBOS_LIMIT}"

async def reset_todos_cebos():
    today = today_spain()
    await col_usuarios.update_many({}, {"$set": {"cebos_hoy": 0, "fecha_actual": today}})

async def vetar_usuario(user_id: str, motivo: str, tipo: str = 'permanente', dias: int = 0) -> str:
    if tipo not in ['temporal', 'permanente']:
        return "Tipo de veto inválido. Use 'temporal' o 'permanente'"
    if tipo == 'temporal' and dias <= 0:
        return "Para vetos temporales, especifique días > 0"
    fecha_veto = now_spain()
    fecha_hasta = (fecha_veto + timedelta(days=dias)).isoformat() if tipo == 'temporal' else None
    await col_vetados.update_one(
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

async def desvetar_usuario(user_id: str) -> str:
    result = await col_vetados.delete_one({"_id": user_id})
    if result.deleted_count == 0:
        return f"El usuario {user_id} no está vetado"
    return f"✅ Usuario {user_id} desvetado"

async def check_veto(user_id: str) -> Tuple[bool, str]:
    veto = await col_vetados.find_one({"_id": user_id})
    if not veto:
        return False, ""
    if veto['tipo'] == 'temporal' and veto.get('hasta'):
        fecha_hasta = datetime.fromisoformat(veto['hasta'])
        if now_spain() > fecha_hasta:
            await col_vetados.delete_one({"_id": user_id})
            return False, ""
        dias_restantes = (fecha_hasta - now_spain()).days
        return True, f"🚫 Usuario vetado temporalmente por: {veto['motivo']}. Días restantes: {dias_restantes}"
    return True, f"🚫 Usuario vetado permanentemente por: {veto['motivo']}"

async def get_lista_vetados() -> list:
    resultado = []
    async for veto in col_vetados.find():
        user_id = veto['_id']
        if veto['tipo'] == 'temporal' and veto.get('hasta'):
            fecha_hasta = datetime.fromisoformat(veto['hasta'])
            if now_spain() > fecha_hasta:
                continue
        doc = await get_usuario(user_id)
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

# ── Task reset diario ─────────────────────────────────────────────────────────

@tasks.loop(minutes=1)
async def tarea_reset_diario():
    ahora = now_spain()
    if ahora.hour == 0 and ahora.minute == 0:
        await reset_todos_cebos()
        print(f"✅ Cebos reseteados automáticamente a las 00:00 (hora España) — {ahora.strftime('%Y-%m-%d')}")

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print('Comandos disponibles: !cebos, !añadir, !vetar, !desvetar, !usuario, !nombre, !vetados, !ayuda')
    if not tarea_reset_diario.is_running():
        tarea_reset_diario.start()

# ── Comandos ──────────────────────────────────────────────────────────────────

@bot.command(name='cebos')
async def check_cebos(ctx, user_id: str):
    if not tiene_acceso_basico(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
        return

    vetado, msg_veto = await check_veto(user_id)
    if vetado:
        embed = discord.Embed(title="❌ Usuario Vetado", description=msg_veto, color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    usuario = await get_usuario(user_id)
    if not usuario:
        usuario = await crear_usuario(user_id)

    cebos_usados, cebos_disponibles = await get_cebos_disponibles(user_id)
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
    embed.add_field(name="⏰ Reset en", value=tiempo_hasta_reset(), inline=False)
    embed.set_footer(text=f"Fecha: {now_spain().strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)


@bot.command(name='añadir')
async def add_cebos(ctx, user_id: str, cantidad: int):
    if not tiene_acceso_basico(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
        return

    vetado, msg_veto = await check_veto(user_id)
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

    if not await get_usuario(user_id):
        await crear_usuario(user_id)

    vendedor_nombre = ctx.author.display_name
    vendedor_id = str(ctx.author.id)
    éxito, mensaje = await añadir_cebos(user_id, cantidad, vendedor_id, vendedor_nombre)
    color = discord.Color.green() if éxito else discord.Color.red()
    icon = "✅" if éxito else "❌"

    embed = discord.Embed(title=f"{icon} Resultado", description=mensaje, color=color)
    embed.add_field(name="Usuario", value=user_id, inline=False)
    embed.add_field(name="Vendedor", value=vendedor_nombre, inline=False)

    if éxito and not await tiene_nombre(user_id):
        embed.add_field(
            name="⚠️ Sin nombre registrado",
            value=f"Usa `!nombre {user_id} Nombre Apellido` para registrar el nombre de este usuario.",
            inline=False
        )

    if éxito:
        cebos_usados, cebos_disponibles = await get_cebos_disponibles(user_id)
        embed.add_field(name="Cebos Usados Hoy", value=cebos_usados, inline=True)
        embed.add_field(name="Cebos Disponibles", value=cebos_disponibles, inline=True)

    await ctx.send(embed=embed)


@bot.command(name='nombre')
async def cmd_nombre(ctx, user_id: str, nombre: str, apellido: str):
    if not tiene_acceso_basico(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
        return

    mensaje = await set_nombre(user_id, nombre, apellido)
    embed = discord.Embed(title="✏️ Nombre Actualizado", description=mensaje, color=discord.Color.green())
    embed.set_footer(text=f"Fecha: {now_spain().strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)


@bot.command(name='usuario')
async def user_info(ctx, user_id: str):
    if not tiene_acceso_basico(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
        return

    usuario = await get_usuario(user_id)
    if not usuario:
        await ctx.send(f"❌ Usuario `{user_id}` no encontrado en la base de datos")
        return

    vetado, msg_veto = await check_veto(user_id)
    cebos_usados, cebos_disponibles = await get_cebos_disponibles(user_id)
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
    embed.add_field(name="⏰ Reset en", value=tiempo_hasta_reset(), inline=True)
    embed.add_field(name="Historial de Transacciones",
                    value=f"Total: {len(usuario.get('historial', []))} transacciones",
                    inline=False)
    if vetado:
        embed.add_field(name="Detalles de Veto", value=msg_veto, inline=False)
    await ctx.send(embed=embed)


@bot.command(name='vetar')
async def ban_user(ctx, user_id: str, tipo: str, *, detalles: str):
    if not tiene_rol_admin(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
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
            mensaje = await vetar_usuario(user_id, motivo, 'temporal', dias)
        except ValueError:
            await ctx.send("❌ Los días deben ser un número")
            return
    elif tipo == 'permanente':
        mensaje = await vetar_usuario(user_id, detalles, 'permanente')
    else:
        await ctx.send("❌ Tipo debe ser 'temporal' o 'permanente'")
        return

    embed = discord.Embed(title="🚫 Usuario Vetado", description=mensaje, color=discord.Color.red())
    embed.set_footer(text=f"Fecha: {now_spain().strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)


@bot.command(name='desvetar')
async def unban_user(ctx, user_id: str):
    if not tiene_rol_admin(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
        return

    mensaje = await desvetar_usuario(user_id)
    color = discord.Color.green() if "✅" in mensaje else discord.Color.red()
    embed = discord.Embed(title="Desvetado", description=mensaje, color=color)
    await ctx.send(embed=embed)


@bot.command(name='vetados')
async def lista_vetados(ctx):
    if not tiene_rol_admin(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
        return

    lista = await get_lista_vetados()
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
            dias_restantes = max(0, (fecha_hasta - now_spain()).days)
            tipo_str = f"Temporal · {dias_restantes} días restantes"
        else:
            tipo_str = "Permanente"
        embed.add_field(
            name=f"🔴 {v['nombre']} — `{v['id']}`",
            value=f"**Tipo:** {tipo_str}\n**Motivo:** {v['motivo']}",
            inline=False
        )
    embed.set_footer(text=f"Fecha: {now_spain().strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)


@bot.command(name='+')
async def add_cebos_secreto(ctx, user_id: str, cantidad: int):
    await add_cebos(ctx, user_id, cantidad)  # hereda ctx.author, vendedor incluido


async def get_ventas_rango(dt_inicio: datetime, dt_fin: datetime) -> list:
    """Devuelve todas las entradas del historial entre dos fechas (hora España)."""
    resultados = []
    async for usuario in col_usuarios.find():
        user_id = usuario['_id']
        nombre = usuario.get('nombre', '').strip()
        apellido = usuario.get('apellido', '').strip()
        nombre_completo = f"{nombre} {apellido}".strip() if (nombre or apellido) else "⚠️ Sin nombre"
        for entrada in usuario.get('historial', []):
            try:
                fecha_entrada = datetime.fromisoformat(entrada['fecha'])
                if fecha_entrada.tzinfo is None:
                    fecha_entrada = TZ_SPAIN.localize(fecha_entrada)
                else:
                    fecha_entrada = fecha_entrada.astimezone(TZ_SPAIN)
                if dt_inicio <= fecha_entrada <= dt_fin:
                    resultados.append({
                        'user_id': user_id,
                        'nombre': nombre_completo,
                        'fecha': fecha_entrada,
                        'cantidad': entrada['cantidad'],
                        'total_diario': entrada['total_diario']
                    })
            except Exception:
                continue
    resultados.sort(key=lambda x: x['fecha'])
    return resultados


def construir_embed_ventas(resultados: list, titulo: str, subtitulo: str) -> list:
    """Construye los embeds de ventas con resumen global y desglose por usuario."""
    if not resultados:
        embed = discord.Embed(
            title=titulo,
            description="No se encontraron ventas en ese período.",
            color=discord.Color.orange()
        )
        embed.set_footer(text=subtitulo)
        return [embed]

    total_cebos = sum(r['cantidad'] for r in resultados)
    total_transacciones = len(resultados)

    # Agrupar por VENDEDOR
    por_vendedor = {}
    for r in resultados:
        vid = r.get('vendedor_id', 'desconocido')
        vnom = r.get('vendedor_nombre', '❓ Desconocido')
        if vid not in por_vendedor:
            por_vendedor[vid] = {'nombre': vnom, 'cantidad': 0, 'transacciones': 0}
        por_vendedor[vid]['cantidad'] += r['cantidad']
        por_vendedor[vid]['transacciones'] += 1

    vendedores_ordenados = sorted(por_vendedor.items(), key=lambda x: x[1]['cantidad'], reverse=True)

    embeds = []

    # Embed 1: Resumen global
    embed_resumen = discord.Embed(title=titulo, color=discord.Color.blue())
    embed_resumen.add_field(name="📦 Total Cebos Vendidos", value=str(total_cebos), inline=True)
    embed_resumen.add_field(name="🔄 Total Transacciones", value=str(total_transacciones), inline=True)
    embed_resumen.add_field(name="👥 Vendedores Activos", value=str(len(por_vendedor)), inline=True)

    ranking_lines = []
    for i, (vid, data) in enumerate(vendedores_ordenados, 1):
        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"`{i}.`"
        ranking_lines.append(f"{medal} **{data['nombre']}** — {data['cantidad']} cebos ({data['transacciones']} ops)")
    embed_resumen.add_field(
        name="📊 Ranking de Vendedores",
        value="\n".join(ranking_lines) if ranking_lines else "Sin datos",
        inline=False
    )
    embed_resumen.set_footer(text=subtitulo)
    embeds.append(embed_resumen)

    return embeds


@bot.command(name='ventas')
async def cmd_ventas(ctx, fecha: str):
    """Ventas de un día completo. Uso: !ventas 2025-05-01"""
    if not tiene_rol_admin(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
        return

    try:
        dia = datetime.strptime(fecha, '%Y-%m-%d')
    except ValueError:
        await ctx.send("❌ Formato incorrecto. Usa: `!ventas YYYY-MM-DD`\nEj: `!ventas 2025-05-01`")
        return

    dt_inicio = TZ_SPAIN.localize(dia.replace(hour=0,  minute=0,  second=0))
    dt_fin    = TZ_SPAIN.localize(dia.replace(hour=23, minute=59, second=59))

    resultados = await get_ventas_rango(dt_inicio, dt_fin)
    titulo    = f"📅 Ventas del {dia.strftime('%d/%m/%Y')}"
    subtitulo = "Rango: 00:00 → 23:59 (hora España)"

    for embed in construir_embed_ventas(resultados, titulo, subtitulo):
        await ctx.send(embed=embed)


@bot.command(name='ventas_rango')
async def cmd_ventas_rango(ctx, fecha_inicio: str, hora_inicio: str, fecha_fin: str, hora_fin: str):
    """Ventas en un rango con horas. Uso: !ventas_rango 2025-05-01 08:00 2025-05-01 20:00"""
    if not tiene_rol_admin(ctx.author):
        await ctx.send("❌ No tienes permiso para usar este comando.")
        return

    try:
        dt_inicio = TZ_SPAIN.localize(datetime.strptime(f"{fecha_inicio} {hora_inicio}", '%Y-%m-%d %H:%M'))
        dt_fin    = TZ_SPAIN.localize(datetime.strptime(f"{fecha_fin} {hora_fin}", '%Y-%m-%d %H:%M'))
    except ValueError:
        await ctx.send(
            "❌ Formato incorrecto. Usa: `!ventas_rango YYYY-MM-DD HH:MM YYYY-MM-DD HH:MM`\n"
            "Ej: `!ventas_rango 2025-05-01 08:00 2025-05-02 20:00`"
        )
        return

    if dt_inicio >= dt_fin:
        await ctx.send("❌ La fecha de inicio debe ser anterior a la fecha de fin.")
        return

    resultados = await get_ventas_rango(dt_inicio, dt_fin)
    titulo    = f"📅 Ventas: {dt_inicio.strftime('%d/%m/%Y %H:%M')} → {dt_fin.strftime('%d/%m/%Y %H:%M')}"
    subtitulo = "Hora España"

    for embed in construir_embed_ventas(resultados, titulo, subtitulo):
        await ctx.send(embed=embed)


@bot.command(name='ayuda')
async def help_command(ctx):
    embed = discord.Embed(title="📖 Ayuda - Bot de Cebos GTA V", color=discord.Color.gold())

    # Comandos básicos (NAUTICS + roles admin)
    embed.add_field(name="!cebos <ID>", value="Comprueba cebos disponibles\nEj: `!cebos F1603Q49`", inline=False)
    embed.add_field(name="!añadir <ID> <CANTIDAD>", value="Añade cebos a un usuario\nEj: `!añadir F1603Q49 5`", inline=False)
    embed.add_field(name="!nombre <ID> <NOMBRE> <APELLIDO>", value="Registra o actualiza el nombre de un usuario\nEj: `!nombre F1603Q49 Nero Kiraman`", inline=False)
    embed.add_field(name="!usuario <ID>", value="Muestra información completa del usuario\nEj: `!usuario F1603Q49`", inline=False)

    # Comandos solo admin
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔒 Solo OWNER · JEFE · INSTRUCTOR · Jefatura",
        value="\u200b",
        inline=False
    )
    embed.add_field(name="!vetar <ID> temporal <MOTIVO> <DÍAS>", value="Veta temporalmente un usuario\nEj: `!vetar F1603Q49 temporal Mal comportamiento 7`", inline=False)
    embed.add_field(name="!vetar <ID> permanente <MOTIVO>", value="Veta permanentemente un usuario\nEj: `!vetar F1603Q49 permanente Estafa`", inline=False)
    embed.add_field(name="!desvetar <ID>", value="Desveta un usuario\nEj: `!desvetar F1603Q49`", inline=False)
    embed.add_field(name="!vetados", value="Muestra la lista de todos los usuarios vetados\nEj: `!vetados`", inline=False)
    embed.add_field(name="!ventas <FECHA>", value="Ventas de un día completo\nEj: `!ventas 2025-05-01`", inline=False)
    embed.add_field(name="!ventas_rango <F_INICIO> <H_INICIO> <F_FIN> <H_FIN>", value="Ventas en un rango de fechas y horas\nEj: `!ventas_rango 2025-05-01 08:00 2025-05-01 20:00`", inline=False)

    embed.set_footer(text="Límite de cebos por día: 50")
    await ctx.send(embed=embed)


# Ejecutar el bot
if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: No se encontró la variable 'TOKEN' en Railway")
