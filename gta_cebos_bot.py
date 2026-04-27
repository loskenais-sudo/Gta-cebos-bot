import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Archivo de base de datos JSON
DATABASE_FILE = 'cebos_data.json'

# Límite de cebos por día
CEBOS_LIMIT = 50

class CebosDatabase:
    """Gestiona la base de datos de cebos"""
    
    def __init__(self):
        self.data = self.load_data()
    
    def load_data(self) -> dict:
        """Carga los datos desde el archivo JSON"""
        if os.path.exists(DATABASE_FILE):
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'usuarios': {},  # {ID: {'nombre': str, 'apellido': str, 'cebos_hoy': int, 'fecha_actual': str, 'vetados': []}}
            'vetados': {}    # {ID: {'motivo': str, 'tipo': 'temporal/permanente', 'hasta': str, 'fecha_veto': str}}
        }
    
    def save_data(self):
        """Guarda los datos en el archivo JSON"""
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
    
    def get_usuario_info(self, user_id: str) -> Optional[dict]:
        """Obtiene la información de un usuario"""
        return self.data['usuarios'].get(user_id)
    
    def crear_usuario(self, user_id: str, nombre: str, apellido: str) -> dict:
        """Crea o actualiza un usuario"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if user_id not in self.data['usuarios']:
            self.data['usuarios'][user_id] = {
                'nombre': nombre,
                'apellido': apellido,
                'cebos_hoy': 0,
                'fecha_actual': today,
                'historial': []
            }
        else:
            # Resetear cebos si es un nuevo día
            fecha_guardada = self.data['usuarios'][user_id].get('fecha_actual', today)
            if fecha_guardada != today:
                self.data['usuarios'][user_id]['cebos_hoy'] = 0
                self.data['usuarios'][user_id]['fecha_actual'] = today
            
            # Actualizar nombre y apellido si cambiaron
            self.data['usuarios'][user_id]['nombre'] = nombre
            self.data['usuarios'][user_id]['apellido'] = apellido
        
        self.save_data()
        return self.data['usuarios'][user_id]
    
    def get_cebos_disponibles(self, user_id: str) -> Tuple[int, int]:
        """Retorna (cebos_usados_hoy, cebos_disponibles)"""
        usuario = self.get_usuario_info(user_id)
        if not usuario:
            return 0, CEBOS_LIMIT
        
        today = datetime.now().strftime('%Y-%m-%d')
        fecha_guardada = usuario.get('fecha_actual', today)
        
        # Si es un nuevo día, resetear
        if fecha_guardada != today:
            usuario['cebos_hoy'] = 0
            usuario['fecha_actual'] = today
            self.save_data()
        
        cebos_usados = usuario['cebos_hoy']
        cebos_disponibles = max(0, CEBOS_LIMIT - cebos_usados)
        return cebos_usados, cebos_disponibles
    
    def añadir_cebos(self, user_id: str, cantidad: int) -> Tuple[bool, str]:
        """Intenta añadir cebos. Retorna (éxito, mensaje)"""
        usuario = self.get_usuario_info(user_id)
        if not usuario:
            return False, "Usuario no encontrado"
        
        cebos_usados, cebos_disponibles = self.get_cebos_disponibles(user_id)
        
        if cantidad > cebos_disponibles:
            return False, f"No puedes coger {cantidad} cebos. Solo tienes {cebos_disponibles} disponibles hoy."
        
        usuario['cebos_hoy'] += cantidad
        usuario['historial'].append({
            'fecha': datetime.now().isoformat(),
            'cantidad': cantidad,
            'total_diario': usuario['cebos_hoy']
        })
        self.save_data()
        
        return True, f"✅ Se han añadido {cantidad} cebos. Total hoy: {usuario['cebos_hoy']}/{CEBOS_LIMIT}"
    
    def vetar_usuario(self, user_id: str, motivo: str, tipo: str = 'permanente', dias: int = 0) -> str:
        """Veta un usuario (temporal o permanente)"""
        if tipo not in ['temporal', 'permanente']:
            return "Tipo de veto inválido. Use 'temporal' o 'permanente'"
        
        if tipo == 'temporal' and dias <= 0:
            return "Para vetos temporales, especifique días > 0"
        
        fecha_veto = datetime.now()
        fecha_hasta = fecha_veto + timedelta(days=dias) if tipo == 'temporal' else None
        
        self.data['vetados'][user_id] = {
            'motivo': motivo,
            'tipo': tipo,
            'hasta': fecha_hasta.isoformat() if fecha_hasta else None,
            'fecha_veto': fecha_veto.isoformat()
        }
        self.save_data()
        
        tipo_texto = f"temporal ({dias} días)" if tipo == 'temporal' else "permanente"
        return f"✅ Usuario {user_id} vetado {tipo_texto}. Motivo: {motivo}"
    
    def desvetar_usuario(self, user_id: str) -> str:
        """Desveta un usuario"""
        if user_id not in self.data['vetados']:
            return f"El usuario {user_id} no está vetado"
        
        del self.data['vetados'][user_id]
        self.save_data()
        return f"✅ Usuario {user_id} devetado"
    
    def check_veto(self, user_id: str) -> Tuple[bool, str]:
        """Comprueba si un usuario está vetado. Retorna (está_vetado, mensaje)"""
        if user_id not in self.data['vetados']:
            return False, ""
        
        veto = self.data['vetados'][user_id]
        
        # Si es temporal, comprobar si ha expirado
        if veto['tipo'] == 'temporal' and veto['hasta']:
            fecha_hasta = datetime.fromisoformat(veto['hasta'])
            if datetime.now() > fecha_hasta:
                # Veto expirado, desvetar
                del self.data['vetados'][user_id]
                self.save_data()
                return False, ""
        
        motivo = veto['motivo']
        tipo = veto['tipo']
        if tipo == 'temporal':
            fecha_hasta = datetime.fromisoformat(veto['hasta'])
            dias_restantes = (fecha_hasta - datetime.now()).days
            return True, f"🚫 Usuario vetado {tipo} por: {motivo}. Días restantes: {dias_restantes}"
        else:
            return True, f"🚫 Usuario vetado permanentemente por: {motivo}"

# Instancia de la base de datos
db = CebosDatabase()

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print('Comandos disponibles: !cebos, !añadir, !vetar, !desvetar, !info, !ayuda')

@bot.command(name='cebos')
async def check_cebos(ctx, user_id: str):
    """
    Comprueba los cebos disponibles de un usuario
    Uso: !cebos ID
    Ejemplo: !cebos F1603Q49
    """
    
    # Comprobar veto
    vetado, msg_veto = db.check_veto(user_id)
    if vetado:
        embed = discord.Embed(
            title="❌ Usuario Vetado",
            description=msg_veto,
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Crear o actualizar usuario
    usuario = db.crear_usuario(user_id, "", "")
    cebos_usados, cebos_disponibles = db.get_cebos_disponibles(user_id)
    
    embed = discord.Embed(
        title=f"📊 Estado de Cebos",
        color=discord.Color.blue()
    )
    embed.add_field(name="ID Usuario", value=user_id, inline=False)
    embed.add_field(name="Cebos Usados Hoy", value=f"🟢 {cebos_usados}", inline=True)
    embed.add_field(name="Cebos Disponibles", value=f"🔵 {cebos_disponibles}", inline=True)
    embed.add_field(name="Límite Diario", value=f"⚫ {CEBOS_LIMIT}", inline=True)
    embed.set_footer(text=f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command(name='añadir')
async def add_cebos(ctx, user_id: str, cantidad: int):
    """
    Añade cebos a un usuario
    Uso: !añadir ID CANTIDAD
    Ejemplo: !añadir F1603Q49 5
    """
    
    # Comprobar veto
    vetado, msg_veto = db.check_veto(user_id)
    if vetado:
        embed = discord.Embed(
            title="❌ Usuario Vetado",
            description=msg_veto,
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Validar cantidad
    if cantidad <= 0:
        await ctx.send("❌ La cantidad debe ser mayor a 0")
        return
    
    # Crear o actualizar usuario
    db.crear_usuario(user_id, "", "")
    
    # Intentar añadir cebos
    éxito, mensaje = db.añadir_cebos(user_id, cantidad)
    
    color = discord.Color.green() if éxito else discord.Color.red()
    icon = "✅" if éxito else "❌"
    
    embed = discord.Embed(
        title=f"{icon} Resultado",
        description=mensaje,
        color=color
    )
    embed.add_field(name="Usuario", value=user_id, inline=False)
    
    if éxito:
        cebos_usados, cebos_disponibles = db.get_cebos_disponibles(user_id)
        embed.add_field(name="Cebos Usados Hoy", value=cebos_usados, inline=True)
        embed.add_field(name="Cebos Disponibles", value=cebos_disponibles, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='vetar')
async def ban_user(ctx, user_id: str, tipo: str, *, detalles: str):
    """
    Veta un usuario (temporal o permanente)
    Uso: !vetar ID temporal MOTIVO DÍAS
         !vetar ID permanente MOTIVO
    Ejemplo: !vetar F1603Q49 temporal Comportamiento inapropiado 7
    """
    
    # Permisos de administrador
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
    
    embed = discord.Embed(
        title="🚫 Usuario Vetado",
        description=mensaje,
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command(name='desvetar')
async def unban_user(ctx, user_id: str):
    """
    Desveta un usuario
    Uso: !desvetar ID
    """
    
    # Permisos de administrador
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Solo administradores pueden desvetar usuarios")
        return
    
    mensaje = db.desvetar_usuario(user_id)
    
    color = discord.Color.green() if "✅" in mensaje else discord.Color.red()
    embed = discord.Embed(
        title="Desvetado",
        description=mensaje,
        color=color
    )
    
    await ctx.send(embed=embed)

@bot.command(name='info')
async def user_info(ctx, user_id: str):
    """
    Muestra información completa de un usuario
    Uso: !info ID
    """
    
    usuario = db.get_usuario_info(user_id)
    
    if not usuario:
        await ctx.send(f"❌ Usuario {user_id} no encontrado en la base de datos")
        return
    
    vetado, msg_veto = db.check_veto(user_id)
    cebos_usados, cebos_disponibles = db.get_cebos_disponibles(user_id)
    
    embed = discord.Embed(
        title=f"👤 Información del Usuario",
        color=discord.Color.purple()
    )
    embed.add_field(name="ID", value=user_id, inline=False)
    embed.add_field(name="Nombre Completo", value=f"{usuario['nombre']} {usuario['apellido']}", inline=False)
    embed.add_field(name="Estado", value="🚫 Vetado" if vetado else "✅ Activo", inline=True)
    embed.add_field(name="Cebos Hoy", value=f"{cebos_usados}/{CEBOS_LIMIT}", inline=True)
    embed.add_field(name="Historial de Transacciones", 
                   value=f"Total: {len(usuario.get('historial', []))} transacciones", 
                   inline=False)
    
    if vetado:
        embed.add_field(name="Detalles de Veto", value=msg_veto, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='ayuda')
async def help_command(ctx):
    """Muestra la ayuda de los comandos"""
    
    embed = discord.Embed(
        title="📖 Ayuda - Bot de Cebos GTA V",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="!cebos <ID>",
        value="Comprueba cebos disponibles\nEj: !cebos XXXXXXXX",
        inline=False
    )
    
    embed.add_field(
        name="!añadir <ID> <CANTIDAD>",
        value="Añade cebos a un usuario\nEj: !añadir XXXXXXXX 5",
        inline=False
    )
    
    embed.add_field(
        name="!vetar <ID> temporal <MOTIVO> <DÍAS>",
        value="Veta temporalmente un usuario\nEj: !vetar XXXXXXXX temporal Mal comportamiento 7",
        inline=False
    )
    
    embed.add_field(
        name="!vetar <ID> permanente <MOTIVO>",
        value="Veta permanentemente un usuario\nEj: !vetar XXXXXXXX permanente Estafa",
        inline=False
    )
    
    embed.add_field(
        name="!desvetar <ID>",
        value="Desveta un usuario\nEj: !desvetar XXXXXXXX",
        inline=False
    )
    
    embed.add_field(
        name="!info <ID>",
        value="Muestra información del usuario\nEj: !info XXXXXXXX",
        inline=False
    )
    
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
