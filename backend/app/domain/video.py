"""Qué stream de la cámara puede reproducir realmente un navegador.

Verificado contra una iDS-2CD7A46G0/P-IZHSY: la prueba de conexión RTSP daba verde, MediaMTX
publicaba la ruta y la marcaba `ready`, y el navegador igual no mostraba nada. El motivo es que
esa cámara entrega sus dos streams principales en **H.265**, que ni WebRTC ni HLS reproducen
fuera de Safari. Sus streams H.264 existen, pero en canales que la plataforma no ofrecía.

"El protocolo responde" y "el usuario ve el video" son dos afirmaciones distintas: esta es la
capa donde se separan.
"""

from dataclasses import dataclass

# Lo que los navegadores decodifican por WebRTC/HLS en la práctica. H.265 queda afuera a
# propósito: Safari lo reproduce por HLS, pero no se puede asumir el navegador del usuario.
CODECS_NAVEGABLES = {"H264", "H.264", "AVC", "AVC1"}


@dataclass(frozen=True)
class PerfilDisponible:
    """Lo mínimo de un perfil de video para decidir si sirve para el navegador."""

    stream_type: str  # main | sub | other
    codec: str | None
    rtsp_path: str
    width: int | None = None


@dataclass(frozen=True)
class StreamElegido:
    rtsp_path: str
    codec: str | None
    # Por qué no se usó el stream pedido, para poder decírselo al usuario en vez de dejarlo
    # mirando un reproductor negro.
    nota: str | None = None


def es_navegable(codec: str | None) -> bool:
    if not codec:
        return False
    return codec.upper().replace("-", "") in {c.upper().replace("-", "") for c in CODECS_NAVEGABLES}


def elegir_para_navegador(
    perfiles: list[PerfilDisponible], pedido: str, ruta_por_defecto: str
) -> StreamElegido:
    """Devuelve el stream a publicar: el pedido si sirve, o el mejor H.264 disponible.

    `ruta_por_defecto` es la ruta que usaría la plataforma sin mirar los perfiles; se usa cuando
    todavía no se leyeron los perfiles de esta cámara.
    """
    if not perfiles:
        return StreamElegido(ruta_por_defecto, None)

    del_pedido = next((p for p in perfiles if p.stream_type == pedido), None)
    if del_pedido is not None and es_navegable(del_pedido.codec):
        return StreamElegido(del_pedido.rtsp_path, del_pedido.codec)

    # El pedido no sirve: se busca el mejor H.264. Para "main" se prefiere el de más resolución;
    # para el resto, el más liviano.
    navegables = [p for p in perfiles if es_navegable(p.codec)]
    if not navegables:
        codec = del_pedido.codec if del_pedido else None
        ruta = del_pedido.rtsp_path if del_pedido else ruta_por_defecto
        return StreamElegido(
            ruta,
            codec,
            nota=(
                f"Esta cámara entrega {codec or 'un códec'} en todos sus streams y el navegador "
                "no lo reproduce. El video sí se está recibiendo: se puede grabar o verlo con un "
                "reproductor externo (VLC)."
            ),
        )

    navegables.sort(key=lambda p: p.width or 0, reverse=pedido == "main")
    elegido = navegables[0]
    codec_pedido = del_pedido.codec if del_pedido else None
    return StreamElegido(
        elegido.rtsp_path,
        elegido.codec,
        nota=(
            f"El stream {pedido} de esta cámara es {codec_pedido or 'de un códec'}, que el "
            f"navegador no reproduce. Se está mostrando otro stream de la misma cámara en "
            f"{elegido.codec}."
        ),
    )
