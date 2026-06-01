# PROYECTO SAAS DE RESERVAS MULTI-RUBRO - DESARROLLO COMPLETO

Quiero que actúes como un Arquitecto de Software Senior, Tech Lead y
Desarrollador Full Stack experto en Python, Flask, PostgreSQL,
SQLAlchemy, SaaS Multi-Tenant, Mercado Pago, PWA y sistemas de reservas.

IMPORTANTE:

-   Nunca me des ejemplos simplificados.
-   Nunca me des pseudocódigo.
-   Nunca me des fragmentos incompletos.
-   Siempre entrega archivos completos listos para copiar y pegar.
-   Siempre indica exactamente qué archivo crear o modificar.
-   Siempre explica dónde pegar el código.
-   Siempre respeta la arquitectura existente.
-   Si falta información para implementar algo, primero pregúntame.
-   Antes de generar código analiza el impacto sobre el resto del
    sistema.
-   Cada módulo debe ser escalable y preparado para producción.

# OBJETIVO DEL PRODUCTO

Estamos construyendo un SaaS Multi-Tenant de reservas.

NO es solamente un turnero para manicuras.

Debe servir para:

-   Manicuras
-   Peluquerías
-   Barberías
-   Lashistas
-   Estética
-   Spa
-   Psicólogos
-   Nutricionistas
-   Consultorios
-   Canchas de fútbol
-   Canchas de pádel
-   Tenis
-   Coworking
-   Salas de reuniones
-   Cualquier negocio que reserve recursos

# ARQUITECTURA GENERAL

Backend:

-   Python 3.12
-   Flask
-   SQLAlchemy
-   Flask-Migrate
-   Flask-Login

Base de datos:

-   PostgreSQL

Cache:

-   Redis

Tareas programadas:

-   Celery

Frontend:

-   Bootstrap 5
-   HTMX
-   Alpine.js

Aplicación:

-   Web Responsive
-   PWA instalable

# MULTI-TENANT

Cada negocio es independiente.

Toda consulta debe filtrarse por:

negocio_id

Ningún negocio puede acceder a datos de otro.

# MODELO COMERCIAL

Planes:

Independiente:

-   Básico
-   Pro
-   Premium

Locales:

-   Starter
-   Business
-   Enterprise

Facturación:

-   Mensual
-   Anual con descuento

Prueba gratuita:

-   Solo para Plan Básico
-   14 días

El resto de los planes:

-   Pago inmediato

Sin período de gracia.

Al vencer:

-   Puede iniciar sesión.
-   Puede consultar datos.

No puede:

-   Crear reservas.
-   Crear clientes.
-   Crear recursos.
-   Recibir reservas.

# MARKETPLACE

Existe marketplace público.

Cada negocio decide:

visible_marketplace = true/false

Los clientes pueden buscar por:

-   Ciudad
-   Rubro
-   Servicio
-   Calificación

Solo pueden dejar reseñas:

-   Clientes con reserva finalizada.
-   Pago confirmado.

Los negocios NO pueden ocultar reseñas.

Solo responderlas.

Para ocultar una reseña deben enviar una solicitud al Super Admin.

# RECURSOS

El sistema NO gira alrededor de profesionales.

Gira alrededor de recursos.

Ejemplos:

Persona:

-   Julieta
-   Sofía

Cancha:

-   Cancha 1
-   Cancha 2

Consultorio:

-   Consultorio A

Sala:

-   Sala VIP

Cada negocio puede crear sus propios tipos de recursos.

# RESERVAS

Motor universal.

Una reserva puede asociarse a:

-   Persona
-   Cancha
-   Sala
-   Consultorio
-   Recurso personalizado

Estados:

-   pendiente_pago
-   confirmado
-   en_proceso
-   finalizado
-   cancelado
-   ausente
-   reprogramado

# DISPONIBILIDAD

Debe calcularse dinámicamente.

Considerar:

-   Horarios
-   Bloqueos
-   Vacaciones
-   Excepciones
-   Duración
-   Capacidad

No guardar disponibilidad precalculada.

# CAPACIDAD

Cada recurso tiene:

capacidad

Ejemplos:

Manicura = 1

Cancha = 1

Clase grupal = 20

# PRECIOS

Soportar:

Precio fijo

Precio por recurso

Precio por horario

Precio por temporada

Promociones

Cupones

Señas

# PAGOS

Integración Mercado Pago, Naranja X y Modo.

Funciones:

-   Pago de señas
-   Pago de reservas
-   Suscripciones del SaaS
-   Webhooks

# PERSONALIZACIÓN

Cada negocio tiene:

-   Logo
-   Banner
-   Colores
-   Tipografía
-   Redes sociales

Templates:

-   Minimal
-   Elegante
-   Moderno
-   Premium

# PÁGINAS PÚBLICAS

URL:

/slug-negocio

Perfil del negocio:

-   Banner
-   Servicios
-   Galería
-   Reseñas
-   Reservar

Perfil de recurso:

/slug-negocio/recurso/slug-recurso

# PWA

Preparada desde V1.

Instalable:

-   Android
-   iPhone
-   Windows

# ESTRUCTURA DEL PROYECTO

Usar arquitectura modular:

app/ ├── auth/ ├── admin/ ├── negocios/ ├── recursos/ ├── reservas/ ├──
servicios/ ├── clientes/ ├── marketplace/ ├── pagos/ ├── reportes/ ├──
notificaciones/ ├── models/ ├── templates/ ├── static/

# FORMA DE TRABAJO

Vamos a desarrollar paso a paso.

Quiero que me guíes como Tech Lead.

Para cada paso debes entregar:

1.  Objetivo.
2.  Archivos involucrados.
3.  Código completo.
4.  Explicación.
5.  Comandos a ejecutar.
6.  Cómo probarlo.
7.  Posibles errores.
8.  Siguiente paso recomendado.

NUNCA avances varios módulos a la vez.

Primero construir la base sólida.

Comenzar desde cero revisando la arquitectura completa y luego
implementar el módulo de autenticación, roles, usuarios y multi-tenant
de forma profesional.
