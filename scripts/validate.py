#!/usr/bin/env python3
"""Структурный валидатор n8n-воркфлоу витрины.

Проверяет: JSON читается, есть name/nodes/connections, имена нод уникальны,
каждое ребро connections указывает на существующую ноду, нет «висячих» нод
без входящих связей (кроме триггеров), выражения {{ }} сбалансированы.

Запуск: python scripts/validate.py [каталог с workflow-*.json]
Код возврата 0 — всё чисто, 1 — найдены проблемы.
"""
import json
import sys
from pathlib import Path

TRIGGER_TYPES = ("webhook", "scheduleTrigger", "emailReadImap", "telegramTrigger",
                 "formTrigger", "errorTrigger", "manualTrigger", "cron")
NO_INLET_OK = ("stickyNote", "sticky_note")  # UI-аннотации без связей


def check_workflow(path: Path) -> list[str]:
    problems = []
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{path.name}: битый JSON: {e}"]

    for field in ("name", "nodes", "connections"):
        if field not in wf:
            problems.append(f"{path.name}: нет поля {field}")
    nodes = wf.get("nodes", [])
    if not nodes:
        problems.append(f"{path.name}: пустой список нод")
        return problems

    names = [n.get("name") for n in nodes]
    if len(names) != len(set(names)):
        dupes = {x for x in names if names.count(x) > 1}
        problems.append(f"{path.name}: дубли имён нод: {dupes}")

    by_name = {n["name"]: n for n in nodes if n.get("name")}

    # Рёбра connections
    incoming = set()
    for src, kinds in wf.get("connections", {}).items():
        if src not in by_name:
            problems.append(f"{path.name}: connection из несуществующей ноды '{src}'")
            continue
        for kind, branches in kinds.items():
            if kind != "main":
                continue
            for branch in branches:
                for edge in (branch or []):
                    dst = edge.get("node")
                    if dst not in by_name:
                        problems.append(f"{path.name}: '{src}' -> несуществующая '{dst}'")
                    else:
                        incoming.add(dst)

    # Висячие ноды (кроме триггеров и sticky-note)
    for n in nodes:
        ntype = n.get("type", "")
        if any(t in ntype for t in TRIGGER_TYPES) or any(t in ntype for t in NO_INLET_OK):
            continue
        if n["name"] not in incoming:
            problems.append(f"{path.name}: нода '{n['name']}' без входящих связей")

    # Триггер есть?
    if not any(any(t in n.get("type", "") for t in TRIGGER_TYPES) for n in nodes):
        problems.append(f"{path.name}: нет триггерной ноды")

    # Баланс n8n-выражений: только в строках-значениях, начинающихся с '='
    def walk(v):
        if isinstance(v, str):
            yield v
        elif isinstance(v, dict):
            for x in v.values():
                yield from walk(x)
        elif isinstance(v, list):
            for x in v:
                yield from walk(x)

    for n in nodes:
        for s in walk(n.get("parameters", {})):
            if s.startswith("=") and s.count("{{") != s.count("}}"):
                problems.append(f"{path.name}: несбалансированные {{{{ }}}} в ноде '{n['name']}'")
                break

    return problems


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "workflows")
    files = sorted(root.glob("*.json"))
    if not files:
        print(f"нет JSON в {root}")
        return 1
    bad = 0
    for f in files:
        problems = check_workflow(f)
        status = "OK " if not problems else "FAIL"
        print(f"[{status}] {f.name}: {len(json.loads(f.read_text(encoding='utf-8'))['nodes'])} нод")
        for p in problems:
            print("   !", p)
            bad += 1
    print("\nИтог:", "все воркфлоу чистые" if bad == 0 else f"проблем: {bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
