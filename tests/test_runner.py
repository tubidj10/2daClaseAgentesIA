"""Tests de las partes de runner.py que no requieren llamar a la API.

Corren sin GEMINI_API_KEY: validan la herramienta de inventario (incluida
la ambigüedad real qa/prod de la Entrega 3) y el schema de salida.
"""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from google.genai import errors as genai_errors  # noqa: E402

from runner import (  # noqa: E402
    TicketSchema,
    _parsear_ticket,
    _retry_delay_del_servidor,
    buscar_en_inventario,
)


def test_inventario_coincidencia_unica():
    resultado = buscar_en_inventario("Notificaciones")
    lineas = resultado.splitlines()
    assert len(lineas) == 1
    assert "prod" in lineas[0]


def test_inventario_ambiguedad_real_qa_prod():
    resultado = buscar_en_inventario("Facturacion")
    lineas = resultado.splitlines()
    assert len(lineas) == 2
    entornos = {linea.split(",")[1] for linea in lineas}
    assert entornos == {"qa", "prod"}


def test_inventario_sin_coincidencias():
    resultado = buscar_en_inventario("componente-inexistente-xyz")
    assert resultado == "sin coincidencias"


def test_schema_acepta_ticket_valido():
    ticket = TicketSchema.model_validate(
        {
            "tipo_solicitud": "Incidente",
            "entorno": "qa",
            "titulo_ticket": "Revisión - Facturación",
            "datos_faltantes": [],
        }
    )
    assert ticket.entorno == "qa"
    assert ticket.datos_faltantes == []


def test_schema_rechaza_clave_faltante():
    with pytest.raises(ValidationError):
        TicketSchema.model_validate(
            {
                "tipo_solicitud": "Incidente",
                "entorno": "qa",
                "titulo_ticket": "Revisión - Facturación",
                # falta datos_faltantes
            }
        )


def test_schema_rechaza_tipo_solicitud_fuera_del_enum():
    with pytest.raises(ValidationError):
        TicketSchema.model_validate(
            {
                "tipo_solicitud": "Otra cosa que el modelo se inventó",
                "entorno": "qa",
                "titulo_ticket": "Revisión - Facturación",
                "datos_faltantes": [],
            }
        )


def test_schema_rechaza_entorno_fuera_del_enum():
    with pytest.raises(ValidationError):
        TicketSchema.model_validate(
            {
                "tipo_solicitud": "Incidente",
                "entorno": "produccion",  # no es uno de los 4 valores exactos
                "titulo_ticket": "Revisión - Facturación",
                "datos_faltantes": [],
            }
        )


def test_retry_delay_lee_el_valor_real_del_error_429():
    # Payload real de un 429 RESOURCE_EXHAUSTED de Gemini (recortado), tal
    # como se recibió corriendo el runner contra la cuota free-tier.
    response_json = {
        "error": {
            "code": 429,
            "message": "You exceeded your current quota...",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "47s"}
            ],
        }
    }
    exc = genai_errors.ClientError(429, response_json)
    assert _retry_delay_del_servidor(exc) == 47.0


def test_retry_delay_none_si_no_hay_retry_info():
    exc = genai_errors.ClientError(500, {"error": {"code": 500, "message": "oops"}})
    assert _retry_delay_del_servidor(exc) is None


def test_retry_delay_none_para_excepciones_no_apierror():
    assert _retry_delay_del_servidor(ValueError("no es un error de la API")) is None


def test_parsear_ticket_json_valido():
    texto = (
        '{"tipo_solicitud": "Incidente", "entorno": "qa", '
        '"titulo_ticket": "Revisión - Facturación", "datos_faltantes": []}'
    )
    ticket = _parsear_ticket(texto)
    assert ticket.tipo_solicitud == "Incidente"
    assert ticket.entorno == "qa"


def test_parsear_ticket_json_truncado_da_error_descriptivo():
    # Reproduce el caso real (Iteración 7): el modelo se queda sin tokens a
    # mitad del string y el JSON queda sin cerrar.
    texto_truncado = '{"tipo_solicitud": "Despliegue", "entorno": "Desconocido", "titulo_tick'
    with pytest.raises(RuntimeError, match="JSON inválido o truncado"):
        _parsear_ticket(texto_truncado)
