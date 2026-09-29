"""Percentiles y exportación del corredor de experimentos: funciones puras, sin base de datos."""

from app.services.experiments import (
    Estadistica,
    Experimento,
    ResultadoCamara,
    _percentil,
    exportar_csv,
    exportar_markdown,
)


def test_percentil_lista_vacia():
    assert _percentil([], 50) == 0.0


def test_percentil_un_solo_valor():
    assert _percentil([42.0], 95) == 42.0


def test_percentil_50_es_la_mediana():
    # Con 5 valores ordenados, p50 cae justo en el del medio.
    assert _percentil([10.0, 20.0, 30.0, 40.0, 50.0], 50) == 30.0


def test_percentil_interpola_entre_dos_valores():
    # Con 4 valores, p50 (posición 1.5) interpola entre el segundo y el tercero.
    assert _percentil([10.0, 20.0, 30.0, 40.0], 50) == 25.0


def test_percentil_95_pesa_hacia_el_maximo():
    valores = [float(x) for x in range(1, 21)]  # 1..20
    p95 = _percentil(valores, 95)
    assert 19.0 <= p95 <= 20.0


def _estadistica(**cambios) -> Estadistica:
    base = dict(
        camera_name="PTZ simulada",
        capability_code="device.info",
        protocol="isapi",
        n=30,
        exitos=30,
        tasa_exito=1.0,
        latencia_p50_ms=12.3,
        latencia_p95_ms=25.0,
        latencia_media_ms=13.1,
        latencia_min_ms=8.0,
        latencia_max_ms=40.0,
    )
    return Estadistica(**{**base, **cambios})


def test_exportar_csv_tiene_encabezado_y_una_fila_por_estadistica(tmp_path):
    ruta = exportar_csv([_estadistica(), _estadistica(protocol="onvif")], tmp_path / "r.csv")
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    assert lineas[0].startswith("camara,funcion,protocolo")
    assert len(lineas) == 3
    assert '"isapi"' in lineas[1]
    assert '"onvif"' in lineas[2]


def test_exportar_csv_lista_vacia_deja_solo_encabezado(tmp_path):
    ruta = exportar_csv([], tmp_path / "r.csv")
    assert len(ruta.read_text(encoding="utf-8").splitlines()) == 1


def test_exportar_markdown_incluye_metadatos_y_tabla(tmp_path):
    experimento = Experimento(
        experiment_id=__import__("uuid").UUID(int=1),
        iniciado_en="2026-09-27T10:00:00",
        repeticiones=30,
        resultados=[
            ResultadoCamara(
                __import__("uuid").UUID(int=1), "PTZ simulada", True, False, None, "unreachable: x"
            )
        ],
    )
    ruta = exportar_markdown(experimento, [_estadistica()], tmp_path / "informe.md")
    texto = ruta.read_text(encoding="utf-8")
    assert "PTZ simulada" in texto
    assert "device.info" in texto
    assert "alcanzable" in texto
    assert "30" in texto  # repeticiones


def test_exportar_markdown_sin_mediciones_lo_dice(tmp_path):
    experimento = Experimento(
        experiment_id=__import__("uuid").UUID(int=2),
        iniciado_en="2026-09-27T10:00:00",
        repeticiones=5,
        resultados=[
            ResultadoCamara(
                __import__("uuid").UUID(int=2),
                "Cámara muerta",
                False,
                False,
                "unreachable",
                "unreachable",
            )
        ],
    )
    ruta = exportar_markdown(experimento, [], tmp_path / "informe.md")
    assert "Sin mediciones" in ruta.read_text(encoding="utf-8")
