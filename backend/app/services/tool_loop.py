"""
A small, bounded tool-calling loop shared by "Ask your analysis" (Phase 9) and the
investigator agent (Phase 10).

    model turn → tool calls? → validate args (Pydantic) → run the read-only handler
               → append results → next model turn … until an answer, a finish tool,
                 or the step/tool budget runs out (then the model must answer without tools).

Handlers receive validated arguments only; the caller binds any server-side context
(e.g. the analysis id) into the handler, so the model can never choose what data it may read.
"""
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from app import llm

logger = logging.getLogger(__name__)

MAX_RESULT_CHARS = 6000   # default cap for one tool result sent back to the model
OLD_RESULT_CHARS = 400    # older tool results are shrunk to this (context management)


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[BaseModel], Any]   # returns JSON-serializable data

    def spec(self) -> dict:
        """Provider-neutral function declaration (JSON schema from the Pydantic args model)."""
        schema = self.args_model.model_json_schema()
        return {"name": self.name, "description": self.description, "parameters": _simplify_schema(schema)}


def _simplify_schema(schema: dict) -> dict:
    """Keep only the JSON-schema keywords every provider accepts (Gemini supports a subset)."""
    allowed = {"type", "description", "enum", "properties", "required", "items"}
    defs = schema.get("$defs", {})

    def clean(node: dict) -> dict:
        """Recursively inline $ref / anyOf(null) and drop unsupported keywords."""
        if "$ref" in node:
            node = defs[node["$ref"].split("/")[-1]]
        if "anyOf" in node:   # Optional[X] → X
            node = next(n for n in node["anyOf"] if n.get("type") != "null")
        out = {k: v for k, v in node.items() if k in allowed}
        if "properties" in out:
            out["properties"] = {k: clean(v) for k, v in out["properties"].items()}
        if "items" in out:
            out["items"] = clean(out["items"])
        return out

    result = clean(schema)
    result.setdefault("type", "object")
    result.setdefault("properties", {})
    return result


@dataclass
class Step:
    tool: str
    arguments: dict
    ok: bool
    summary: str
    data: Any = None


@dataclass
class LoopResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    finish_args: BaseModel | None = None     # set when the model called the finish tool
    stopped_by_budget: bool = False
    duration_s: float = 0.0


def _summarize(data: Any) -> str:
    """One-line human summary of a tool result for traces and the UI."""
    if isinstance(data, dict) and "error" in data:
        return f"error: {data['error']}"
    if isinstance(data, dict) and "results" in data:
        return f"{len(data['results'])} result(s)"
    if isinstance(data, list):
        return f"{len(data)} item(s)"
    return "ok"


def _flatten(messages: list[dict]) -> list[dict]:
    """Rewrite tool-call turns as plain text, for a final call made without tools."""
    flat = []
    for m in messages:
        if m["role"] == "assistant" and m.get("tool_calls"):
            calls = ", ".join(f"{c.name}({json.dumps(c.arguments)})" for c in m["tool_calls"])
            flat.append({"role": "assistant", "content": (m.get("content") or "") + f"\n[called tools: {calls}]"})
        elif m["role"] == "tool":
            flat.append({"role": "user", "content": f"[result of {m['name']}]\n{m['content']}"})
        else:
            flat.append({"role": m["role"], "content": m["content"]})
    return flat


def _trim_old_results(messages: list[dict], keep_full: int) -> list[dict]:
    """Shrink all but the last `keep_full` tool results.

    Every model turn re-sends the whole conversation, so without this the prompt grows with each
    step (and free tiers with per-minute token limits fail). Recent results stay intact; older ones
    keep their first few hundred characters so the model still knows what it already looked at.
    """
    tool_idx = [i for i, m in enumerate(messages) if m["role"] == "tool"]
    old = set(tool_idx[:-keep_full]) if keep_full else set(tool_idx)
    out = []
    for i, m in enumerate(messages):
        if i in old and len(m["content"]) > OLD_RESULT_CHARS:
            m = {**m, "content": m["content"][:OLD_RESULT_CHARS] + " …[trimmed: older result]"}
        out.append(m)
    return out


def run_tool_loop(
    messages: list[dict],
    tools: list[Tool],
    task_type: str,
    max_tool_calls: int = 6,
    finish_tool: Tool | None = None,
    retry_budget_s: float | None = None,
    max_result_chars: int = MAX_RESULT_CHARS,
    keep_full_results: int = 2,
) -> LoopResult:
    """Run the model with tools until it answers (or calls finish_tool). Never exceeds max_tool_calls."""
    started = time.perf_counter()
    by_name = {t.name: t for t in tools}
    all_tools = tools + ([finish_tool] if finish_tool else [])
    specs = [t.spec() for t in all_tools]
    steps: list[Step] = []
    messages = list(messages)

    while True:
        budget_left = max_tool_calls - len(steps)
        if budget_left > 0:
            result = llm.chat_with_tools(_trim_old_results(messages, keep_full_results), specs, task_type,
                                         retry_budget_s=retry_budget_s)
        else:   # final answer: no tools offered, so send the transcript as plain text (works on every provider)
            result = llm.chat_with_tools(_flatten(_trim_old_results(messages, keep_full_results)), None, task_type,
                                         retry_budget_s=retry_budget_s)
        if not result.tool_calls or budget_left <= 0:
            return LoopResult(answer=result.text.strip(), steps=steps, stopped_by_budget=budget_left <= 0,
                              duration_s=round(time.perf_counter() - started, 1))

        messages.append(llm.assistant_message(result))
        for call in result.tool_calls:
            if finish_tool and call.name == finish_tool.name:
                try:
                    final = finish_tool.args_model.model_validate(call.arguments)
                except ValidationError as exc:
                    content = json.dumps({"error": f"invalid arguments: {exc.errors()[0]['msg']} at {exc.errors()[0]['loc']}"})
                    messages.append({"role": "tool", "tool_call_id": call.id, "name": call.name, "content": content})
                    steps.append(Step(call.name, call.arguments, False, "invalid final answer — asked to fix"))
                    continue
                steps.append(Step(call.name, call.arguments, True, "final answer submitted"))
                return LoopResult(answer=result.text.strip(), steps=steps, finish_args=final,
                                  duration_s=round(time.perf_counter() - started, 1))

            tool = by_name.get(call.name)
            if tool is None:
                data = {"error": f"unknown tool '{call.name}'"}
            else:
                try:
                    data = tool.handler(tool.args_model.model_validate(call.arguments))
                except ValidationError as exc:
                    first = exc.errors()[0]
                    data = {"error": f"invalid arguments: {first['msg']} at {'.'.join(map(str, first['loc']))}"}
                except Exception as exc:   # a tool bug must not kill the conversation
                    logger.exception("Tool %s failed", call.name)
                    data = {"error": f"tool failed: {type(exc).__name__}"}
            steps.append(Step(call.name, call.arguments, "error" not in (data if isinstance(data, dict) else {}),
                              _summarize(data), data))
            content = json.dumps(data, default=str, separators=(",", ":"), ensure_ascii=False)[:max_result_chars]
            messages.append({"role": "tool", "tool_call_id": call.id, "name": call.name, "content": content})

        if len(steps) >= max_tool_calls:
            messages.append({"role": "user", "content": (
                "Tool budget used up. Answer now using only the information already retrieved. "
                "If it is not enough, say what is missing.")})
