"""Pruebas del modelo del caso y de los extractores.

Cubren lo que hace posible encadenar herramientas: que los resultados de cada
módulo se traduzcan a hallazgos tipados, que no se dupliquen, que conserven su
procedencia y que el catálogo sepa qué herramienta acepta cada tipo.
"""

import pytest

from core import extractors
from core.case import Caso, Entidad, Hallazgo, es_pivotable
from core.registry import TOOLS, ToolRegistry


@pytest.fixture
def caso() -> Caso:
    return Caso()


@pytest.fixture(scope="module")
def registry() -> ToolRegistry:
    return ToolRegistry()


# ------------------------------------------------------------------ Caso


def test_el_caso_nace_vacio(caso: Caso) -> None:
    assert len(caso) == 0
    assert caso.todos() == []


def test_no_duplica_hallazgos(caso: Caso) -> None:
    primero = Hallazgo(Entidad.IP, "1.2.3.4", origen="WHOIS", desde="a.com")
    repetido = Hallazgo(Entidad.IP, "1.2.3.4", origen="PortScanner", desde="b.com")

    assert caso.añadir(primero) is True
    assert caso.añadir(repetido) is False
    assert len(caso) == 1


def test_conserva_la_primera_procedencia(caso: Caso) -> None:
    """Interesa cómo se descubrió algo, no la última vez que se volvió a ver."""
    caso.añadir(Hallazgo(Entidad.IP, "1.2.3.4", origen="WHOIS", desde="a.com"))
    caso.añadir(Hallazgo(Entidad.IP, "1.2.3.4", origen="PortScanner", desde="b.com"))

    guardado = caso.de_tipo(Entidad.IP)[0]
    assert guardado.origen == "WHOIS"
    assert guardado.desde == "a.com"


def test_el_mismo_valor_con_distinto_tipo_son_hallazgos_distintos(caso: Caso) -> None:
    caso.añadir(Hallazgo(Entidad.DOMINIO, "example.com"))
    caso.añadir(Hallazgo(Entidad.SERVICIO, "example.com"))
    assert len(caso) == 2


def test_ignora_valores_vacios(caso: Caso) -> None:
    assert caso.añadir(Hallazgo(Entidad.DOMINIO, "")) is False
    assert caso.añadir(Hallazgo(Entidad.DOMINIO, "   ")) is False
    assert len(caso) == 0


def test_incorporar_devuelve_solo_los_nuevos(caso: Caso) -> None:
    caso.añadir(Hallazgo(Entidad.DOMINIO, "a.com"))
    nuevos = caso.incorporar(
        [Hallazgo(Entidad.DOMINIO, "a.com"), Hallazgo(Entidad.DOMINIO, "b.com")]
    )
    assert [h.valor for h in nuevos] == ["b.com"]


def test_el_indice_prefiere_el_tipo_pivotable(caso: Caso) -> None:
    """Si un valor es a la vez servicio y dominio, gana el que ofrece acciones."""
    caso.añadir(Hallazgo(Entidad.SERVICIO, "example.com"))
    caso.añadir(Hallazgo(Entidad.DOMINIO, "example.com"))
    assert caso.indice_por_valor()["example.com"] == Entidad.DOMINIO


def test_resumen_cuenta_por_tipo(caso: Caso) -> None:
    caso.incorporar(
        [
            Hallazgo(Entidad.DOMINIO, "a.com"),
            Hallazgo(Entidad.DOMINIO, "b.com"),
            Hallazgo(Entidad.IP, "1.2.3.4"),
        ]
    )
    assert caso.resumen() == {Entidad.DOMINIO: 2, Entidad.IP: 1}


def test_distingue_pivotables_de_terminales() -> None:
    assert es_pivotable(Entidad.DOMINIO)
    assert es_pivotable(Entidad.IP)
    assert not es_pivotable(Entidad.PUERTO)
    assert not es_pivotable(Entidad.BRECHA)
    assert not es_pivotable(Entidad.SERVICIO)


# ------------------------------------------------------------ Extractores


def test_extractor_subdominios() -> None:
    salida = extractors.subdominios({"subdomains": ["a.example.com", "b.example.com"]})
    assert [v for _, v, _ in salida] == ["a.example.com", "b.example.com"]
    assert all(t == Entidad.DOMINIO for t, _, _ in salida)


def test_extractor_whois_separa_ips_de_name_servers() -> None:
    salida = extractors.whois_dns(
        {
            "dns": {"A": ["93.184.216.34"], "MX": ["10 mail.example.com."]},
            "whois": {"name_servers": ["NS1.EXAMPLE.COM.", "ns2.example.com"]},
        }
    )
    tipos = {(t, v) for t, v, _ in salida}
    assert (Entidad.IP, "93.184.216.34") in tipos
    # Los name servers se normalizan a minúsculas y sin punto final.
    assert (Entidad.DOMINIO, "ns1.example.com") in tipos
    assert (Entidad.DOMINIO, "ns2.example.com") in tipos
    # Los MX no se extraen: llevan prioridad delante y no son un host limpio.
    assert not any(v.startswith("10 ") for _, v, _ in salida)


def test_extractor_whois_descarta_registros_a_invalidos() -> None:
    salida = extractors.whois_dns({"dns": {"A": ["no-es-una-ip"]}, "whois": {}})
    assert salida == []


def test_extractor_puertos() -> None:
    salida = extractors.escaner_puertos(
        {"target": "example.com", "ip": "93.184.216.34", "ports": [80, 443]}
    )
    assert (Entidad.IP, "93.184.216.34") in {(t, v) for t, v, _ in salida}
    puertos = [v for t, v, _ in salida if t == Entidad.PUERTO]
    assert puertos == ["example.com:80", "example.com:443"]


def test_extractor_wayback() -> None:
    salida = extractors.wayback(
        {
            "snapshot": {
                "url": "https://web.archive.org/web/1998/x",
                "fecha": "1998-12-12",
            }
        }
    )
    assert salida[0][0] == Entidad.URL
    assert "1998-12-12" in salida[0][2]


def test_extractor_wayback_sin_captura() -> None:
    assert extractors.wayback({"snapshot": {}}) == []


def test_extractor_holehe() -> None:
    salida = extractors.holehe(
        {
            "sitios_detectados": ["spotify.com"],
            "brechas_seguridad": ["Adobe", "LinkedIn"],
            "identidad_google": {"avatar_url": "https://x.test/a.jpg"},
        }
    )
    tipos = {(t, v) for t, v, _ in salida}
    assert (Entidad.SERVICIO, "spotify.com") in tipos
    assert (Entidad.BRECHA, "Adobe") in tipos
    assert (Entidad.URL, "https://x.test/a.jpg") in tipos


def test_extractor_metadatos_solo_con_gps() -> None:
    assert extractors.metadatos({"metadata": {"Make": "Canon"}}) == []
    salida = extractors.metadatos(
        {
            "metadata": {
                "GPSInfo": {"GPSLatitude": (40, 25, 0), "GPSLongitude": (3, 42, 0)}
            }
        }
    )
    assert salida and salida[0][0] == Entidad.COORDENADA


def test_extractor_neutro_no_produce_nada() -> None:
    assert (
        extractors.sin_hallazgos({"status": "success", "stats": {"malicious": 3}}) == []
    )


@pytest.mark.parametrize("spec", TOOLS, ids=lambda s: s.key)
def test_los_extractores_toleran_resultados_de_error(spec) -> None:
    """Un módulo que falla devuelve un dict mínimo; extraerlo no debe romper."""
    assert spec.extractor({"status": "error", "error": "boom"}) == []


# -------------------------------------------------------------- Pivotado


def test_el_catalogo_resuelve_las_acciones_por_tipo(registry: ToolRegistry) -> None:
    assert [s.key for s in registry.herramientas_para(Entidad.IP)] == [
        "VirusTotal",
        "PortScanner",
    ]
    assert [s.key for s in registry.herramientas_para(Entidad.EMAIL)] == ["Holehe"]


def test_los_hallazgos_terminales_no_ofrecen_acciones(registry: ToolRegistry) -> None:
    for tipo in (Entidad.PUERTO, Entidad.BRECHA, Entidad.SERVICIO, Entidad.COORDENADA):
        assert registry.herramientas_para(tipo) == [], tipo


def test_toda_herramienta_declara_lo_que_consume() -> None:
    for spec in TOOLS:
        assert spec.consume, f"{spec.key} no declara ningún tipo de entrada"


def test_lo_que_se_produce_es_alcanzable() -> None:
    """Todo tipo declarado en `produce` debe salir realmente del extractor.

    Detecta el desajuste de declarar un tipo y olvidar extraerlo.
    """
    for spec in TOOLS:
        if spec.produce:
            assert spec.extractor is not extractors.sin_hallazgos, (
                f"{spec.key} declara producir {spec.produce} pero no tiene extractor"
            )
