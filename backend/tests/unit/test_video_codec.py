"""Elección del stream que el navegador puede reproducir.

El caso real: la iDS-2CD7A46G0/P-IZHSY entrega main y sub en H.265 —que el navegador no
decodifica— y sus streams H.264 viven en canales que la plataforma no ofrecía. RTSP daba verde y
MediaMTX publicaba la ruta igual: el video no se veía y nada avisaba por qué.
"""

import pytest

from app.domain.video import PerfilDisponible, StreamElegido, elegir_para_navegador, es_navegable

POR_DEFECTO = "/Streaming/Channels/102"


def perfil(tipo: str, codec: str, canal: str, ancho: int) -> PerfilDisponible:
    return PerfilDisponible(tipo, codec, f"/Streaming/Channels/{canal}", ancho)


# Los cinco perfiles reales de la cámara de parking.
PARKING = [
    perfil("main", "H.265", "101", 2560),
    perfil("sub", "H.265", "102", 704),
    perfil("other", "H.264", "103", 1280),
    perfil("other", "H.264", "104", 704),
    perfil("other", "H.264", "105", 704),
]

# Una cámara normal: los dos streams principales en H.264.
NORMAL = [perfil("main", "H.264", "101", 1920), perfil("sub", "H.264", "102", 640)]


@pytest.mark.parametrize("codec", ["H.264", "H264", "h264", "AVC"])
def test_los_codecs_que_el_navegador_reproduce(codec):
    assert es_navegable(codec)


@pytest.mark.parametrize("codec", ["H.265", "HEVC", "MJPEG", None, ""])
def test_los_que_no(codec):
    assert not es_navegable(codec)


def test_si_el_stream_pedido_sirve_se_usa_tal_cual():
    elegido = elegir_para_navegador(NORMAL, "sub", POR_DEFECTO)
    assert elegido == StreamElegido("/Streaming/Channels/102", "H.264", None)


def test_si_el_pedido_es_h265_se_cambia_por_uno_h264():
    elegido = elegir_para_navegador(PARKING, "sub", POR_DEFECTO)
    assert elegido.codec == "H.264"
    assert elegido.rtsp_path != "/Streaming/Channels/102"
    assert "H.265" in elegido.nota and "navegador no reproduce" in elegido.nota


def test_para_el_sub_se_elige_el_h264_mas_liviano():
    elegido = elegir_para_navegador(PARKING, "sub", POR_DEFECTO)
    assert elegido.rtsp_path in ("/Streaming/Channels/104", "/Streaming/Channels/105")


def test_para_el_main_se_elige_el_h264_de_mas_resolucion():
    elegido = elegir_para_navegador(PARKING, "main", "/Streaming/Channels/101")
    assert elegido.rtsp_path == "/Streaming/Channels/103"


def test_si_ningun_stream_es_navegable_se_avisa_y_no_se_inventa_otro():
    solo_h265 = [perfil("main", "H.265", "101", 2560), perfil("sub", "H.265", "102", 704)]
    elegido = elegir_para_navegador(solo_h265, "sub", POR_DEFECTO)
    assert elegido.rtsp_path == "/Streaming/Channels/102"  # el pedido, sin cambiarlo
    assert "H.265" in elegido.nota
    assert "VLC" in elegido.nota  # se ofrece una salida, no solo el problema


def test_sin_perfiles_leidos_se_usa_la_ruta_de_siempre():
    """Una cámara recién dada de alta todavía no tiene perfiles: no se rompe el comportamiento."""
    elegido = elegir_para_navegador([], "sub", POR_DEFECTO)
    assert elegido == StreamElegido(POR_DEFECTO, None, None)


def test_una_camara_normal_no_recibe_ninguna_nota():
    for pedido in ("main", "sub"):
        assert elegir_para_navegador(NORMAL, pedido, POR_DEFECTO).nota is None
