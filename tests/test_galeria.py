"""Tests de la galería de fotos."""
import io
import os

from app.extensions import db
from app.models.galeria import GaleriaFoto

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000154a24f1d0000000049454e44ae426082"
)


def _login(client, email):
    client.post("/auth/login", data={"email": email, "password": "clave1234"})


def test_subir_ver_y_eliminar_foto(client, app, crear_negocio):
    neg, _ = crear_negocio(email="gal@test.com")
    _login(client, "gal@test.com")

    # Subir una foto
    client.post("/panel/galeria", data={"fotos": (io.BytesIO(PNG), "foto.png")},
                content_type="multipart/form-data")
    foto = GaleriaFoto.query.filter_by(negocio_id=neg.id).first()
    assert foto is not None

    # Aparece en la página pública
    html = client.get(f"/{neg.slug}").get_data(as_text=True)
    assert foto.filename in html

    # Limpieza del archivo físico + eliminar por la ruta
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], *foto.filename.split("/")[1:])
    fid = foto.id
    client.post(f"/panel/galeria/{fid}/eliminar")
    assert GaleriaFoto.query.get(fid) is None
    if os.path.exists(ruta):
        os.remove(ruta)


def test_no_elimina_foto_ajena(client, crear_negocio):
    neg_a, _ = crear_negocio(email="a@test.com")
    neg_b, _ = crear_negocio(email="b@test.com")
    foto_b = GaleriaFoto(negocio_id=neg_b.id, filename="uploads/x/y.png", orden=0)
    db.session.add(foto_b); db.session.commit()

    _login(client, "a@test.com")
    r = client.post(f"/panel/galeria/{foto_b.id}/eliminar")
    assert r.status_code == 404
    assert GaleriaFoto.query.get(foto_b.id) is not None
