"""Capacidad de este equipo y pasos para instalar Ollama."""
from __future__ import annotations

import ctypes
import shutil
from dataclasses import dataclass

from ..config import OLLAMA_MODEL, OLLAMA_SMALL_MODEL


@dataclass(frozen=True)
class MachineProfile:
    total_ram_gb: float
    free_ram_gb: float
    free_disk_gb: float
    recommended_model: str
    warning: str
    install_steps: tuple[str, ...]


def machine_profile() -> MachineProfile:
    total_ram, free_ram = _ram_gb()
    free_disk = round(shutil.disk_usage("C:\\").free / (1024**3), 1)
    if free_ram < 3.5:
        recommended = OLLAMA_SMALL_MODEL
        warning = (
            f"Ahora hay {free_ram} GB de RAM libres, de {total_ram} GB en total. "
            f"Cierra el navegador y otros programas antes de probar. "
            f"Con poca memoria libre usa {OLLAMA_SMALL_MODEL}; "
            f"si liberas unos 4 GB, {OLLAMA_MODEL} responde mejor en español."
        )
    else:
        recommended = OLLAMA_MODEL
        warning = (
            f"Hay {free_ram} GB libres de {total_ram} GB. "
            f"Puedes cargar {OLLAMA_MODEL}. La gráfica de este portátil no acelera el modelo: "
            "la respuesta sale por CPU y puede tardar cerca de un minuto."
        )
    if free_disk < 8:
        warning += f" Quedan {free_disk} GB en C:. Libera espacio antes de descargar el modelo."
    steps = (
        "winget install -e --id Ollama.Ollama",
        "Abre Ollama desde el menú Inicio y espera a que quede en la bandeja.",
        f"ollama pull {recommended}",
        "python -m dnd_ai.llm.bench",
    )
    return MachineProfile(
        total_ram_gb=total_ram,
        free_ram_gb=free_ram,
        free_disk_gb=free_disk,
        recommended_model=recommended,
        warning=warning,
        install_steps=steps,
    )


def _ram_gb() -> tuple[float, float]:
    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return (0.0, 0.0)
    total = round(status.ullTotalPhys / (1024**3), 1)
    free = round(status.ullAvailPhys / (1024**3), 1)
    return (total, free)


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = (
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    )
