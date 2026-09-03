"""Tests de las partes de runner.py que no requieren llamar a la API.

Corren sin GEMINI_API_KEY: validan la herramienta de inventario (incluida
la ambigüedad real qa/prod de la Entrega 3) y el schema de salida.
"""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runner import TicketSchema, buscar_en_inventario  # noqa: E402


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
