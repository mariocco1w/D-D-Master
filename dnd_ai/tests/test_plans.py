"""Los planes arman un contexto corto y la página responde sin Ollama."""
from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from dnd_ai.llm.bench import BenchHandler
from dnd_ai.llm.ollama_client import model_is_installed
from dnd_ai.llm.plans import PlanBlocked, PlanId, _build, _checks, get_plan, plan_catalog
from dnd_ai.llm.rules_context import retrieve_rules


class PlanContextTests(unittest.TestCase):
    def test_every_plan_is_listed(self) -> None:
        ids = tuple(plan.plan_id for plan in plan_catalog())
        self.assertEqual(ids, tuple(PlanId))

    def test_ready_prompts_fit_this_machine(self) -> None:
        questions = {
            PlanId.PRIMERA_CLASE: "No sé qué clase elegir.",
            PlanId.CLASES: "¿En qué se diferencia un mago de un hechicero?",
            PlanId.REGLAS: "¿Qué es una tirada de salvación?",
            PlanId.FICHA: "Prepara la ficha de nivel 1 de un bárbaro.",
            PlanId.DADO: "El bárbaro golpea con el hacha.",
        }
        for plan_id, question in questions.items():
            messages, _meta = _build(plan_id, question)
            size = sum(len(message["content"]) for message in messages)
            self.assertLess(size, 9000, plan_id.value)
            self.assertEqual(messages[-1]["content"], question)

    def test_saving_throw_retrieves_the_glossary(self) -> None:
        context = retrieve_rules("¿Qué es una tirada de salvación?")
        self.assertIn("Tirada de salvación", context)

    def test_class_answer_checks_follow_the_question(self) -> None:
        checks = _checks(
            PlanId.CLASES,
            "¿En qué se diferencia un mago de un hechicero?",
            "El mago usa Inteligencia y un d6. El hechicero usa Carisma y un d6.",
            {},
        )
        self.assertTrue(all(item.passed for item in checks))

    def test_dice_check_uses_the_program_roll(self) -> None:
        _messages, meta = _build(PlanId.DADO, "El bárbaro golpea con el hacha.")
        roll = int(meta["roll"])
        self.assertIn(str(roll), _messages[0]["content"])
        failed = _checks(PlanId.DADO, "El bárbaro golpea.", "El hacha falla.", meta)
        self.assertFalse(failed[0].passed)
        passed = _checks(PlanId.DADO, "El bárbaro golpea.", f"El d20 muestra {roll}.", meta)
        self.assertTrue(passed[0].passed)

    def test_blocked_plans_do_not_call_the_model(self) -> None:
        for plan_id in (PlanId.INDICE, PlanId.SESION):
            plan = get_plan(plan_id.value)
            self.assertFalse(plan.ready)
            with self.assertRaises(PlanBlocked):
                _build(plan_id, plan.sample_question)

    def test_model_name_ignores_latest_suffix(self) -> None:
        self.assertTrue(model_is_installed(["qwen2.5:3b:latest"], "qwen2.5:3b"))
        self.assertFalse(model_is_installed(["qwen3:4b"], "qwen2.5:3b"))


class BenchPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), BenchHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def test_page_lists_plans_and_machine(self) -> None:
        page = self._get("/")
        self.assertIn("Pruebas de texto", page)
        status = json.loads(self._get("/api/status"))
        self.assertGreater(status["total_ram_gb"], 0)
        self.assertIn("install_steps", status)
        plans = json.loads(self._get("/api/plans"))["plans"]
        self.assertEqual(len(plans), 7)
        self.assertEqual(plans[0]["id"], "primera_clase")

    def test_blocked_plan_returns_a_reason(self) -> None:
        body = self._post("/api/test", {"plan": "sesion", "question": "Empieza una campaña."})
        payload = json.loads(body)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["blocked"])
        self.assertIn("sesión", payload["error"])

    def _get(self, path: str) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
            return response.read().decode("utf-8")

    def _post(self, path: str, payload: dict[str, str]) -> str:
        raw = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8")


if __name__ == "__main__":
    unittest.main()
