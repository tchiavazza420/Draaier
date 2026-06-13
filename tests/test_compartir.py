"""
tests/test_compartir.py
-----------------------
Material de difusión: la página de placas para compartir.
"""


def test_compartir_renderiza(client, crear_negocio, crear_recurso, crear_servicio, login):
    neg, dueno = crear_negocio()
    rec = crear_recurso(neg)
    crear_servicio(neg, [rec])
    login(dueno.email)

    r = client.get("/panel/compartir")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    # El link de reservas y el contenedor de placas tienen que estar.
    assert "Material para compartir" in html
    assert neg.slug in html
    assert "html-to-image" in html  # la librería de exportación


def test_compartir_requiere_login(client):
    r = client.get("/panel/compartir", follow_redirects=False)
    assert r.status_code in (301, 302)
    assert "/auth/login" in r.headers["Location"]
