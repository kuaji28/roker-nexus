"""
ROKER NEXUS — Horarios y días hábiles
Detecta si el negocio está abierto, calcula días hábiles, etc.
"""
from datetime import datetime, date, time, timedelta
from typing import Optional
import pytz

from config import (
    TIMEZONE, HORARIO_SEMANA, HORARIO_SABADO, FERIADOS_2026
)


def ahora() -> datetime:
    """Retorna el datetime actual en zona horaria de Argentina."""
    return datetime.now(tz=TIMEZONE)


def hoy() -> date:
    return ahora().date()


def es_feriado(d: Optional[date] = None) -> bool:
    d = d or hoy()
    return d.isoformat() in FERIADOS_2026


def es_dia_laboral(d: Optional[date] = None) -> bool:
    d = d or hoy()
    if es_feriado(d):
        return False
    return d.weekday() in HORARIO_SEMANA["dias"] + HORARIO_SABADO["dias"]


def horario_actual() -> dict:
    """Retorna info del horario actual del negocio."""
    ahora_dt = ahora()
    d = ahora_dt.date()
    t = ahora_dt.time()
    dow = d.weekday()

    if es_feriado(d):
        return {"abierto": False, "motivo": "feriado", "icono": "🔴"}

    if dow in HORARIO_SEMANA["dias"]:
        h = HORARIO_SEMANA
        turno = "semana"
    elif dow in HORARIO_SABADO["dias"]:
        h = HORARIO_SABADO
        turno = "sabado"
    else:
        return {"abierto": False, "motivo": "domingo", "icono": "🔴"}

    abierto = h["apertura"] <= t <= h["cierre"]
    return {
        "abierto": abierto,
        "motivo": "abierto" if abierto else "fuera_horario",
        "turno": turno,
        "apertura": h["apertura"].strftime("%H:%M"),
        "cierre": h["cierre"].strftime("%H:%M"),
        "icono": "🟢" if abierto else "🟡",
    }


def proxima_apertura() -> Optional[str]:
    """Retorna cuándo es la próxima apertura."""
    dt = ahora()
    for i in range(1, 8):
        d = (dt + timedelta(days=i)).date()
        dow = d.weekday()
        if es_feriado(d):
            continue
        if dow in HORARIO_SEMANA["dias"]:
            h = HORARIO_SEMANA
        elif dow in HORARIO_SABADO["dias"]:
            h = HORARIO_SABADO
        else:
            continue
        return f"{d.strftime('%A %d/%m')} a las {h['apertura'].strftime('%H:%M')}"
    return None


def dias_sin_stock(fecha_inicio: str) -> int:
    """Calcula cuántos días laborales pasaron desde fecha_inicio."""
    try:
        d_inicio = date.fromisoformat(fecha_inicio)
    except ValueError:
        return 0
    d_hoy = hoy()
    count = 0
    d = d_inicio
    while d < d_hoy:
        if es_dia_laboral(d):
            count += 1
        d += timedelta(days=1)
    return count


def label_horario() -> str:
    """Label corto para mostrar en la UI."""
    h = horario_actual()
    if h["abierto"]:
        return f"🟢 Abierto hasta {h['cierre']}"
    elif h["motivo"] == "feriado":
        return "🔴 Feriado"
    elif h["motivo"] == "domingo":
        prox = proxima_apertura()
        return f"🔴 Cerrado — Reabre {prox or 'pronto'}"
    else:
        prox = proxima_apertura()
        return f"🟡 Fuera de horario — Reabre {prox or 'mañana'}"
