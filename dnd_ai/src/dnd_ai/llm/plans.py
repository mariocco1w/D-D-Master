"""Planes de prueba de texto. Cada uno arma un mensaje para Ollama."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import assert_never

from ..classes.beginner import class_for_wish, render_class_card, render_first_class_guide
from ..classes.catalog import SRD_CLASS_NAMES, load_catalog
from ..config import CHROMA_DIR, OLLAMA_MODEL, OLLAMA_NUM_CTX
from .class_teacher import build_messages
from .ollama_client import OllamaUnavailable, chat, list_models, model_is_installed
from .rules_context import build_rules_messages

PROMPT_CHAR_BUDGET = 9_000


class PlanId(Enum):
    PRIMERA_CLASE = "primera_clase"
    CLASES = "clases"
    REGLAS = "reglas"
    FICHA = "ficha"
    DADO = "dado"
    INDICE = "indice"
    SESION = "sesion"


@dataclass(frozen=True)
class CheckResult:
    label: str
    passed: bool


@dataclass(frozen=True)
class TextPlan:
    plan_id: PlanId
    title: str
    summary: str
    sample_question: str
    ready: bool = True
    blocked_reason: str = ""


class PlanBlocked(RuntimeError):
    """El plan todavía no puede consultar al modelo."""


PLANS: tuple[TextPlan, ...] = (
    TextPlan(
        plan_id=PlanId.PRIMERA_CLASE,
        title="Primera clase",
        summary="Guía a quien no sabe qué clase elegir. Tiene que proponer al bárbaro y dejar la subclase para el nivel 3.",
        sample_question="No sé qué clase elegir. Es mi primera partida.",
    ),
    TextPlan(
        plan_id=PlanId.CLASES,
        title="Clases del SRD",
        summary="Compara clases solo con el resumen corto del catálogo.",
        sample_question="¿En qué se diferencia un mago de un hechicero?",
    ),
    TextPlan(
        plan_id=PlanId.REGLAS,
        title="Reglas y glosario",
        summary="Responde con fragmentos de Cómo jugar y del glosario, no con memoria suelta.",
        sample_question="¿Qué es una tirada de salvación?",
    ),
    TextPlan(
        plan_id=PlanId.FICHA,
        title="Ficha de nivel 1",
        summary="Redacta la ficha de hoy de una clase, sin rasgos de niveles posteriores.",
        sample_question="Prepara la ficha de nivel 1 de un bárbaro, solo con lo que se usa hoy.",
    ),
    TextPlan(
        plan_id=PlanId.DADO,
        title="Tirada narrada",
        summary="El programa tira el d20. El modelo solo narra el número que recibe.",
        sample_question="El bárbaro golpea con el hacha.",
    ),
    TextPlan(
        plan_id=PlanId.INDICE,
        title="Índice del SRD",
        summary="Cuando exista el índice, Ollama recibirá los pasajes recuperados y no el PDF entero.",
        sample_question="¿Cómo funciona la cobertura?",
        ready=False,
        blocked_reason=(
            "El índice en data/chroma todavía no está creado. "
            "En este equipo conviene construirlo con el modelo de Ollama cerrado, "
            "porque embeddings y el chat no caben bien a la vez en 8 GB de RAM."
        ),
    ),
    TextPlan(
        plan_id=PlanId.SESION,
        title="Sesión, mesa y monedas",
        summary="Campañas, bots, chat y economía todavía no tienen estado que el modelo pueda leer.",
        sample_question="Empieza una campaña corta para mi bárbaro de nivel 1.",
        ready=False,
        blocked_reason=(
            "No hay partida, bots ni monedas guardadas. "
            "Ollama no debe inventar esa sesión: este plan se abre cuando exista ese estado."
        ),
    ),
)


def plan_catalog() -> tuple[TextPlan, ...]:
    return PLANS


def get_plan(plan_id: str) -> TextPlan:
    for plan in PLANS:
        if plan.plan_id.value == plan_id:
            return plan
    known = ", ".join(plan.plan_id.value for plan in PLANS)
    raise KeyError(f"No existe el plan {plan_id!r}. Planes: {known}")


def run_text_test(plan_id: str, question: str) -> dict[str, object]:
    plan = get_plan(plan_id)
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("La pregunta está vacía")
    if not plan.ready:
        raise PlanBlocked(plan.blocked_reason)
    installed = list_models()
    if installed is None:
        raise OllamaUnavailable(
            "Ollama no responde en este equipo. Instálalo y descarga el modelo antes de probar."
        )
    if not model_is_installed(installed, OLLAMA_MODEL):
        raise OllamaUnavailable(
            f"Ollama está en marcha, pero falta el modelo {OLLAMA_MODEL}. "
            f"Ejecuta: ollama pull {OLLAMA_MODEL}"
        )
    messages, meta = _build(plan.plan_id, cleaned)
    size = sum(len(message["content"]) for message in messages)
    if size > PROMPT_CHAR_BUDGET:
        raise PlanBlocked(
            f"El contexto mide {size} caracteres y no cabe en num_ctx={OLLAMA_NUM_CTX} de este equipo."
        )
    answer = chat(messages)
    checks = _checks(plan.plan_id, cleaned, answer, meta)
    return {
        "ok": True,
        "plan": plan.plan_id.value,
        "title": plan.title,
        "model": OLLAMA_MODEL,
        "answer": answer,
        "checks": [{"label": item.label, "passed": item.passed} for item in checks],
        "context_chars": size,
        "meta": meta,
    }


def _build(plan_id: PlanId, question: str) -> tuple[list[dict[str, str]], dict[str, object]]:
    match plan_id:
        case PlanId.PRIMERA_CLASE:
            guide = render_first_class_guide(load_catalog())
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Eres la guía Primera clase de D&D Master. "
                        "Hablas en español, con calma, y solo usas esta guía.\n\n"
                        + guide
                    ),
                },
                {"role": "user", "content": question},
            ]
            return messages, {}
        case PlanId.CLASES:
            return build_messages(question), {}
        case PlanId.REGLAS:
            return build_rules_messages(question), {}
        case PlanId.FICHA:
            catalog = load_catalog()
            picked = catalog.mentioned_in(question)
            character_class = picked[0] if picked else catalog.get("Bárbaro")
            card = render_class_card(character_class)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Redactas la ficha de nivel 1 en español. "
                        "Usa solo esta ficha. No añadas rasgos de otros niveles.\n\n"
                        + card
                    ),
                },
                {"role": "user", "content": question},
            ]
            attributes = character_class.attributes()
            return messages, {
                "class_name": character_class.name,
                "primary": attributes.primary_ability,
                "hit_die": _die_token(attributes.hit_die),
            }
        case PlanId.DADO:
            roll = random.SystemRandom().randint(1, 20)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Narras en español una tirada que el programa ya resolvió. "
                        f"El d20 muestra {roll}. Repite ese número. No tires otro dado y no cambies el resultado."
                    ),
                },
                {"role": "user", "content": question},
            ]
            return messages, {"roll": roll}
        case PlanId.INDICE:
            if not CHROMA_DIR.exists():
                raise PlanBlocked(get_plan(PlanId.INDICE.value).blocked_reason)
            raise PlanBlocked(
                "El índice existe, pero esta prueba no lo abre mientras el modelo de chat esté cargado."
            )
        case PlanId.SESION:
            raise PlanBlocked(get_plan(PlanId.SESION.value).blocked_reason)
        case _:
            assert_never(plan_id)


def _checks(
    plan_id: PlanId,
    question: str,
    answer: str,
    meta: dict[str, object],
) -> tuple[CheckResult, ...]:
    folded = answer.casefold()
    match plan_id:
        case PlanId.PRIMERA_CLASE:
            expected = class_for_wish(question)
            return (
                CheckResult(f"Recomienda {expected}", expected.casefold() in folded),
                CheckResult("No ofrece al artífice", "artífice" not in folded),
            )
        case PlanId.CLASES:
            return _class_answer_checks(question, folded)
        case PlanId.REGLAS:
            return (
                CheckResult("Responde con un párrafo", len(answer.strip()) >= 40),
                CheckResult(
                    "Usa la palabra salvación si la pregunta la trae",
                    "salvaci" not in question.casefold() or "salvaci" in folded,
                ),
            )
        case PlanId.FICHA:
            class_name = str(meta.get("class_name", ""))
            primary = str(meta.get("primary", ""))
            hit_die = str(meta.get("hit_die", ""))
            return (
                CheckResult(f"Nombra a {class_name}", class_name.casefold() in folded),
                CheckResult(f"Cita {primary}", _mentions_any(primary, folded)),
                CheckResult(f"Cita el {hit_die}", hit_die in folded),
            )
        case PlanId.DADO:
            roll = str(meta.get("roll", ""))
            return (CheckResult(f"Repite el {roll} que tiró el programa", roll in answer),)
        case PlanId.INDICE | PlanId.SESION:
            return ()
        case _:
            assert_never(plan_id)


def _class_answer_checks(question: str, folded: str) -> tuple[CheckResult, ...]:
    picked = load_catalog().mentioned_in(question)
    if not picked:
        present = [name for name in SRD_CLASS_NAMES if name.casefold() in folded]
        return (CheckResult("Nombra al menos cuatro clases", len(present) >= 4),)
    results: list[CheckResult] = []
    for character_class in picked:
        attributes = character_class.attributes()
        die = _die_token(attributes.hit_die)
        results.append(
            CheckResult(
                f"Nombra a {character_class.name}",
                character_class.name.casefold() in folded,
            )
        )
        results.append(CheckResult(f"Cita el {die}", die in folded))
        results.append(
            CheckResult(
                f"Cita {attributes.primary_ability}",
                _mentions_any(attributes.primary_ability, folded),
            )
        )
    return tuple(results)


def _mentions_any(label: str, folded: str) -> bool:
    words = [word for word in label.casefold().split() if len(word) > 3]
    return any(word in folded for word in words)


def _die_token(hit_die: str) -> str:
    marker = hit_die.casefold().find("d")
    if marker == -1:
        return hit_die.casefold()
    return hit_die.casefold()[marker:].split()[0]

