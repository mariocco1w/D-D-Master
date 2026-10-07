"""Página local para probar los planes de texto contra Ollama."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_NUM_CTX
from .machine import machine_profile
from .ollama_client import OllamaUnavailable, list_models, model_is_installed
from .plans import PlanBlocked, plan_catalog, run_text_test

HOST = "127.0.0.1"
START_PORT = 8765


def status_payload() -> dict[str, object]:
    profile = machine_profile()
    models = list_models()
    online = models is not None
    return {
        "ok": online,
        "base_url": OLLAMA_BASE_URL,
        "configured_model": OLLAMA_MODEL,
        "num_ctx": OLLAMA_NUM_CTX,
        "models": models or [],
        "model_ready": online and model_is_installed(models or [], OLLAMA_MODEL),
        "recommended_model": profile.recommended_model,
        "total_ram_gb": profile.total_ram_gb,
        "free_ram_gb": profile.free_ram_gb,
        "free_disk_gb": profile.free_disk_gb,
        "warning": profile.warning,
        "install_steps": list(profile.install_steps),
    }


def plans_payload() -> dict[str, object]:
    return {
        "plans": [
            {
                "id": plan.plan_id.value,
                "title": plan.title,
                "summary": plan.summary,
                "sample_question": plan.sample_question,
                "ready": plan.ready,
                "blocked_reason": plan.blocked_reason,
            }
            for plan in plan_catalog()
        ]
    }


class BenchHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            page = _page_path().read_bytes()
            self._bytes(200, page, "text/html; charset=utf-8")
            return
        if path == "/api/status":
            self._json(status_payload())
            return
        if path == "/api/plans":
            self._json(plans_payload())
            return
        self._json({"ok": False, "error": "No existe esa ruta."}, 404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/test":
            self._json({"ok": False, "error": "No existe esa ruta."}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 20_000:
            self._json({"ok": False, "error": "La pregunta no tiene un tamaño válido."}, 400)
            return
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "El cuerpo no es JSON."}, 400)
            return
        if not isinstance(data, dict):
            self._json({"ok": False, "error": "El cuerpo no es un objeto."}, 400)
            return
        plan = data.get("plan")
        question = data.get("question")
        if not isinstance(plan, str) or not isinstance(question, str):
            self._json({"ok": False, "error": "Faltan plan y pregunta."}, 400)
            return
        try:
            self._json(run_text_test(plan, question))
        except PlanBlocked as exc:
            self._json({"ok": False, "blocked": True, "error": str(exc)})
        except OllamaUnavailable as exc:
            self._json({"ok": False, "error": str(exc), "install": status_payload()["install_steps"]})
        except (KeyError, ValueError) as exc:
            self._json({"ok": False, "error": str(exc)}, 400)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, payload: dict[str, object], status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._bytes(status, raw, "application/json; charset=utf-8")

    def _bytes(self, status: int, raw: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    for port in range(START_PORT, START_PORT + 5):
        try:
            server = ThreadingHTTPServer((HOST, port), BenchHandler)
        except OSError:
            continue
        print(f"Banco de pruebas: http://{HOST}:{port}", flush=True)
        print("Cierra la ventana o pulsa Ctrl+C para detenerlo.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nBanco detenido.")
        finally:
            server.server_close()
        return
    raise SystemExit("No hay un puerto libre entre 8765 y 8769.")


def _page_path() -> Path:
    return Path(__file__).with_name("bench.html")


if __name__ == "__main__":
    main()
