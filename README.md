# Reservas SaaS — Sistema de reservas multi-rubro (multi-tenant)

SaaS de reservas para cualquier negocio que reserve recursos: peluquerías,
barberías, manicuras, spa, consultorios, canchas, coworking, etc. Multi-tenant
(cada negocio aislado por `negocio_id`), con motor de disponibilidad dinámico,
pagos, notificaciones, marketplace, personalización y PWA.

## Stack

- **Backend:** Python 3.12, Flask 3, SQLAlchemy 2 / Flask-SQLAlchemy, Flask-Migrate, Flask-Login
- **Base de datos:** PostgreSQL 18 (driver psycopg 3)
- **Frontend:** Bootstrap 5 + HTMX (dinámico sin recargar) + PWA instalable
- **Pagos:** Mercado Pago (Checkout Pro) con modo simulación para desarrollo
- **Email:** Flask-Mail (bandeja de desarrollo si no hay SMTP)

## Puesta en marcha

```bash
# 1) Entorno virtual + dependencias
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

# 2) Configuración
copy .env.example .env           # completar DATABASE_URL y SECRET_KEY

# 3) Base de datos
createdb reservas_saas           # o desde pgAdmin
flask db upgrade                 # crea las tablas
flask seed-roles                 # roles del sistema (super_admin, dueno, staff)

# 4) (Opcional) Super Admin de la plataforma
flask crear-super-admin admin@tudominio.com unaClaveSegura

# 5) Levantar
python run.py                    # http://127.0.0.1:5000
```

`FLASK_APP=run.py` para los comandos `flask`.

## Módulos (paso a paso)

| # | Módulo | Descripción |
|---|--------|-------------|
| 1 | Esqueleto | App factory, config por entorno, health check |
| 2 | Multi-tenant | Modelos Negocio (tenant), Usuario, Rol + mixins |
| 3 | Autenticación | Registro de negocio, login/logout, decoradores de rol, tenant por path |
| 4 | Recursos | TipoRecurso + Recurso (capacidad), aislamiento anti-IDOR |
| 5 | Servicios | Duración, precio, N:N con recursos |
| 6 | Disponibilidad | Horarios + bloqueos, motor de slots dinámico, preview HTMX |
| 7 | Reservas | 7 estados, anti doble-reserva (advisory lock), booking público HTMX |
| 8 | Pagos | Señas con Mercado Pago + modo simulación, webhook |
| 9 | Notificaciones | Email de confirmación + recordatorios (CLI) |
| 10 | Clientes/Reseñas | CRM básico; reseñas (solo reservas finalizadas) |
| 11 | Marketplace | Directorio público por ciudad/rubro/servicio/rating |
| 12 | Personalización | Logo, banner, colores, tipografía, plantillas |
| 13 | PWA | Manifest + service worker, instalable |
| 14 | Super Admin | Negocios, suscripciones, moderación de reseñas |
| 15 | Reportes | Métricas por rango + export CSV |
| 16 | Suscripciones | Vencimiento (solo lectura), páginas de error |

## Comandos CLI

```bash
flask seed-roles                 # asegura los roles del sistema
flask crear-super-admin EMAIL PASSWORD [--nombre NOMBRE]
flask enviar-recordatorios [--dias N]    # recordatorios (cron diario)
flask vencer-suscripciones               # marca vencidas (cron diario)
```

## Arquitectura

- **Multi-tenant por discriminador:** todo modelo de dominio hereda `TenantMixin`
  (`negocio_id`). Las consultas usan `query_tenant()` y `obtener_tenant_o_404()`
  (defensa anti-IDOR: 404 ante ids de otro negocio).
- **Resolución de tenant por path:** páginas públicas en `/<slug-negocio>`.
- **Disponibilidad:** nunca precalculada; se deriva en tiempo real de horarios −
  bloqueos − reservas, respetando capacidad.
- **Concurrencia:** `pg_advisory_xact_lock(recurso_id)` evita doble-reserva.

## Servicios externos (opcionales en dev)

- **Mercado Pago:** sin `MERCADOPAGO_ACCESS_TOKEN`, el checkout es simulado.
- **SMTP:** sin `MAIL_SERVER`, los emails van a una bandeja de desarrollo.
- **Redis/Celery:** pendiente; hoy notificaciones y vencimientos corren por CLI/cron.
