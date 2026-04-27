# 📚 EJEMPLOS DE USO - Bot de Cebos GTA V (Versión Simplificada)

## 🎯 Caso de Uso 1: Cliente Normal Comprando Cebos

```
Usuario: !cebos F1603Q49
Bot:
┌─────────────────────────────────────┐
│ 📊 Estado de Cebos                  │
├─────────────────────────────────────┤
│ ID Usuario: F1603Q49                │
│ Cebos Usados Hoy: 🟢 0              │
│ Cebos Disponibles: 🔵 50            │
│ Límite Diario: ⚫ 50                │
└─────────────────────────────────────┘

Usuario: !añadir F1603Q49 20
Bot:
┌─────────────────────────────────────┐
│ ✅ Resultado                        │
├─────────────────────────────────────┤
│ Se han añadido 20 cebos.            │
│ Total hoy: 20/50                    │
└─────────────────────────────────────┘

Usuario: !añadir F1603Q49 30
Bot:
┌─────────────────────────────────────┐
│ ✅ Resultado                        │
├─────────────────────────────────────┤
│ Se han añadido 30 cebos.            │
│ Total hoy: 50/50                    │
└─────────────────────────────────────┘

Usuario: !añadir F1603Q49 5
Bot:
┌─────────────────────────────────────┐
│ ❌ Resultado                        │
├─────────────────────────────────────┤
│ No puedes coger 5 cebos.            │
│ Solo tienes 0 disponibles hoy.      │
└─────────────────────────────────────┘
```

---

## 🚫 Caso de Uso 2: Vetar un Usuario (Temporal)

```
Admin: !vetar F1603Q49 temporal Vendiendo sin licencia 3
Bot:
┌─────────────────────────────────────┐
│ 🚫 Usuario Vetado                   │
├─────────────────────────────────────┤
│ ✅ Usuario F1603Q49 vetado          │
│ temporal (3 días).                  │
│ Motivo: Vendiendo sin licencia      │
└─────────────────────────────────────┘

Usuario: !cebos F1603Q49
Bot:
┌─────────────────────────────────────┐
│ ❌ Usuario Vetado                   │
├─────────────────────────────────────┤
│ 🚫 Usuario vetado temporal por:     │
│ Vendiendo sin licencia              │
│ Días restantes: 3                   │
└─────────────────────────────────────┘
```

---

## 💀 Caso de Uso 3: Vetar Permanentemente

```
Admin: !vetar A1234B56 permanente Estafa a otros vendedores
Bot:
┌─────────────────────────────────────┐
│ 🚫 Usuario Vetado                   │
├─────────────────────────────────────┤
│ ✅ Usuario A1234B56 vetado          │
│ permanentemente por:                 │
│ Estafa a otros vendedores           │
└─────────────────────────────────────┘

Usuario: !cebos A1234B56
Bot:
┌─────────────────────────────────────┐
│ ❌ Usuario Vetado                   │
├─────────────────────────────────────┤
│ 🚫 Usuario vetado permanentemente   │
│ por: Estafa a otros vendedores      │
└─────────────────────────────────────┘
```

---

## ♻️ Caso de Uso 4: Desvetar un Usuario

```
Admin: !desvetar F1603Q49
Bot:
┌─────────────────────────────────────┐
│ Desvetado                           │
├─────────────────────────────────────┤
│ ✅ Usuario F1603Q49 devetado        │
└─────────────────────────────────────┘

Usuario: !cebos F1603Q49
Bot:
✅ Ahora puede comprar cebos nuevamente
```

---

## 📊 Caso de Uso 5: Ver Información Completa

```
Admin: !info F1603Q49
Bot:
┌─────────────────────────────────────┐
│ 👤 Información del Usuario          │
├─────────────────────────────────────┤
│ ID: F1603Q49                        │
│ Estado: ✅ Activo                   │
│ Cebos Hoy: 35/50                    │
│ Historial: Total: 5 transacciones   │
└─────────────────────────────────────┘
```

---

## ⏰ Caso de Uso 6: Reseteo Automático a Medianoche

```
Día 1 - 15:30 UTC
Usuario: !cebos F1603Q49
Bot: Cebos Disponibles: 30/50

Día 1 - 23:59 UTC
Usuario: !añadir F1603Q49 20
Bot: ✅ Se han añadido 20 cebos. Total hoy: 50/50

Día 2 - 00:01 UTC (después de medianoche)
Usuario: !cebos F1603Q49
Bot: Cebos Disponibles: 50/50 (✅ RESETEO AUTOMÁTICO)
```

---

## 👥 Caso de Uso 7: Múltiples Usuarios con Mismo Nombre (Si es necesario)

```
Usuario 1: !cebos F1603Q49
Bot: ✅ Usuario registrado - F1603Q49

Usuario 2: !cebos X9876Y12
Bot: ✅ Usuario registrado - X9876Y12

Nota: Cada ID es único, independientemente del nombre/apellido
```

---

## 📋 Flujo Completo de un Rol Diario

```
INICIO DEL DÍA (0:00 UTC)
└─ Base de datos resetea cebos automáticamente

DURANTE EL DÍA
├─ Vendedor A: !cebos F1603Q49
├─ Bot: Mostrar disponibles (50)
├─ Vendedor B: !cebos X9876Y12
├─ Bot: Mostrar disponibles (50)
├─ Vendedor A: !añadir F1603Q49 25
├─ Bot: ✅ Total: 25/50
├─ Vendedor B: !añadir X9876Y12 50
├─ Bot: ✅ Total: 50/50
└─ Vendedor B: !añadir X9876Y12 1
   Bot: ❌ No tienes disponibles

ADMIN DETECTA ABUSO
├─ Admin: !info F1603Q49
├─ Admin: !vetar F1603Q49 temporal Abuso del sistema 7
├─ Bot: ✅ Usuario vetado 7 días

VENDEDOR INTENTA COMPRAR ESTANDO VETADO
├─ Vendedor A: !cebos F1603Q49
└─ Bot: 🚫 Usuario vetado. 7 días restantes

FIN DEL DÍA
└─ Cebos se resetearán mañana a medianoche
```

---

## 🎯 Recomendaciones de Uso

1. **Designar Admins**: Asigna administrador de Discord a los moderadores
2. **Auditar Regularmente**: Revisa `cebos_data.json` semanalmente
3. **Comunicar Reglas**: Explica a los vendedores el límite de 50 cebos
4. **Vetar Sabiamente**: Usa temporal para advertencias, permanente para abusos severos
5. **Mantener Logs**: Guarda capturas de pantalla de vetados importantes
6. **Respaldar Datos**: Copia `cebos_data.json` regularmente como backup

---

## 🆘 Errores Comunes

### Error: "Solo administradores pueden vetar usuarios"
```
Solución: Asigna rol de administrador en Discord al usuario
```

### Error: "Usuario no encontrado en la base de datos"
```
Solución: Primero usa !cebos para registrar al usuario
```

### Error: "Tipo debe ser 'temporal' o 'permanente'"
```
Uso correcto: !vetar ID temporal MOTIVO 7
             !vetar ID permanente MOTIVO
```

### Error: "Los días deben ser un número"
```
Uso correcto: !vetar ID temporal MOTIVO 7 (no "siete")
```
