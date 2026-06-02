"""
app/pagos/gateways.py
---------------------
Selector de pasarela de pago. Mapea el método elegido por el negocio
(Negocio.metodo_pago) al módulo adaptador correspondiente. Todos exponen la
misma interfaz: esta_configurado(), crear_preferencia(), obtener_pago().
"""

from app.models.negocio import MetodoPagoEnum
from app.models.pago import ProveedorPagoEnum
from app.pagos import mercadopago, naranja_x, modo

# Mapa método del negocio -> (módulo adaptador, proveedor para el registro Pago)
_GATEWAYS = {
    MetodoPagoEnum.MERCADOPAGO: (mercadopago, ProveedorPagoEnum.MERCADOPAGO),
    MetodoPagoEnum.NARANJA_X: (naranja_x, ProveedorPagoEnum.NARANJA_X),
    MetodoPagoEnum.MODO: (modo, ProveedorPagoEnum.MODO),
}


def gateway_para(negocio):
    """Devuelve (modulo_gateway, proveedor_enum) según el método del negocio."""
    return _GATEWAYS.get(
        negocio.metodo_pago, (mercadopago, ProveedorPagoEnum.MERCADOPAGO)
    )
