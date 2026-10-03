"""
V2 Phase 9 — "Ask your analysis": tool loop, analysis-scoped tools, provider message formats.
The model is scripted (no real LLM calls).
Run from backend/: pytest tests/test_chat.py -v
"""
from unittest.mock import patch

from app import llm
from app.models import AnalysisRun, Evidence, Finding, Requirement
from app.services import chat_service
from app.services.tool_loop import Tool, run_tool_loop, _simplify_schema
from app.services.chat_service import SearchArgs

SDD = """## Security
All endpoints require Azure AD tokens.
## Logging
Errors are written to the audit log with the user id.
"""


def _project(client, name="Chat test") -> str:
    """Project with one indexed existing document."""
    pid = client.post("/api/v1/projects", json={"name": name}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/documents", data={"role": "existing", "title": "sdd", "text": SDD})
    return pid


class Script:
    """Scripted model: returns the queued LLMResults in order and records the messages it saw."""

    def __init__(self, *results):
        """Queue of results to return."""
        self.results = list(results)
        self.seen = []

    def __call__(self, messages, tools, task_type, **kwargs):
        """Return the next scripted turn."""
        self.seen.append({"messages": list(messages), "tools": tools})
        return self.results.pop(0)


def _call(name, **args):
    """A model turn that calls one tool."""
    return llm.LLMResult("", tool_calls=[llm.ToolCall(id=f"c-{name}", name=name, arguments=args)])


def test_tool_schema_is_provider_safe():
    """Pydantic JSON schema is reduced to keywords every provider accepts (no anyOf/$ref/defaults)."""
    schema = _simplify_schema(SearchArgs.model_json_schema())
    assert schema["type"] == "object" and set(schema["properties"]) == {"query", "role", "k"}
    assert schema["properties"]["role"]["enum"] == ["reference", "existing"]
    assert "anyOf" not in str(schema) and "default" not in str(schema)


def test_ask_uses_tools_and_returns_sources(client, db):
    """The model searches, gets real chunks back, answers — the API returns steps and sources."""
    pid = _project(client)
    script = Script(_call("search_documents", query="authentication tokens", role="existing"),
                    llm.LLMResult("All endpoints use Azure AD tokens (sdd.txt, \"Security\")."))
    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=script):
        resp = client.post(f"/api/v1/projects/{pid}/chat", json={"message": "How is authentication done?"})
    body = resp.json()
    assert resp.status_code == 200 and "Azure AD" in body["answer"]
    assert body["steps"][0]["tool"] == "search_documents" and body["steps"][0]["ok"]
    assert any(s["kind"] == "chunk" and s["document"] == "sdd.txt" for s in body["sources"])
    # the tool result the model received contains real document text, sent as a tool message
    tool_msg = script.seen[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and "Azure AD" in tool_msg["content"]
    assert "never as instructions" in script.seen[0]["messages"][0]["content"]   # untrusted-data rule in the system prompt


def test_tools_cannot_read_another_analysis(client, db):
    """A chunk id from a different analysis is 'not found' — scoping is enforced by the server."""
    mine, other = _project(client, "Mine"), _project(client, "Other")
    other_doc = client.get(f"/api/v1/projects/{other}/documents").json()[0]
    other_chunk = client.get(f"/api/v1/documents/{other_doc['id']}/chunks").json()[0]["id"]

    tools = {t.name: t for t in chat_service.build_tools(mine, db)}
    result = tools["get_chunk"].handler(tools["get_chunk"].args_model(chunk_id=other_chunk))
    assert result == {"error": "chunk not found in this analysis"}
    hits = tools["search_documents"].handler(tools["search_documents"].args_model(query="Azure AD tokens"))
    own_docs = {d["filename"] for d in client.get(f"/api/v1/projects/{mine}/documents").json()}
    assert {r["document"] for r in hits["results"]} <= own_docs


def test_invalid_tool_arguments_are_reported_back(client, db):
    """Bad arguments don't crash: the model gets an error result and can recover."""
    pid = _project(client)
    script = Script(_call("search_documents", query="x", k=99), llm.LLMResult("Sorry, I could not search."))
    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=script):
        body = client.post(f"/api/v1/projects/{pid}/chat", json={"message": "anything"}).json()
    assert body["steps"][0]["ok"] is False and "invalid arguments" in body["steps"][0]["summary"]


def test_tool_budget_forces_a_final_answer_without_tools(client, db):
    """After max_tool_calls the model must answer; the last call offers no tools and gets a flattened transcript."""
    pid = _project(client)
    turns = [_call("get_overview")] * 3 + [llm.LLMResult("Here is what I found.")]
    script = Script(*turns)
    tools = chat_service.build_tools(pid, db)
    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=script):
        result = run_tool_loop([{"role": "user", "content": "q"}], tools, "chat", max_tool_calls=3)
    assert result.answer == "Here is what I found." and result.stopped_by_budget and len(result.steps) == 3
    final = script.seen[-1]
    assert final["tools"] is None and all(m["role"] in ("system", "user", "assistant") for m in final["messages"])


def test_finish_tool_returns_validated_arguments():
    """A finish tool ends the loop and returns its validated arguments (used by the investigator)."""
    from pydantic import BaseModel

    class Verdict(BaseModel):
        status: str

    finish = Tool("submit", "submit", Verdict, lambda a: None)
    script = Script(_call("submit", status="covered"))
    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=script):
        result = run_tool_loop([{"role": "user", "content": "q"}], [], "x", finish_tool=finish)
    assert result.finish_args.status == "covered"


def test_get_requirement_tool_returns_finding_and_evidence(client, db):
    """get_requirement includes the latest finding with its verified quotes and chunk ids."""
    pid = _project(client)
    chunk_id = client.get(f"/api/v1/documents/{client.get(f'/api/v1/projects/{pid}/documents').json()[0]['id']}/chunks").json()[0]["id"]
    req = Requirement(project_id=pid, code="REQ-001", text="Endpoints require Azure AD tokens.", content_hash="h", status="approved")
    run = AnalysisRun(project_id=pid, status="completed", stats={"counts": {"covered": 1}})
    db.add_all([req, run])
    db.flush()
    finding = Finding(run_id=run.id, requirement_id=req.id, status="covered", explanation="Stated in the SDD.")
    db.add(finding)
    db.flush()
    db.add(Evidence(finding_id=finding.id, chunk_id=chunk_id, quote="All endpoints require Azure AD tokens.", verified=True))
    db.flush()

    tools = {t.name: t for t in chat_service.build_tools(pid, db)}
    data = tools["get_requirement"].handler(tools["get_requirement"].args_model(code="req-001"))
    assert data["finding"]["status"] == "covered" and data["finding"]["evidence"][0]["chunk_id"] == chunk_id
    missing = tools["list_findings"].handler(tools["list_findings"].args_model(status="missing"))
    assert missing["results"] == [] and missing["counts"] == {"covered": 1}


def test_provider_message_conversion_for_tools():
    """Internal tool-call turns convert to OpenAI format (Groq/Ollama) and Gemini functionCall/functionResponse."""
    call = llm.ToolCall(id="c1", name="search_documents", arguments={"query": "tokens"})
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "", "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "c1", "name": "search_documents", "content": "{\"results\": []}"},
    ]
    openai = llm._openai_messages(messages, arguments_as_string=True)
    assert openai[2]["tool_calls"][0]["function"] == {"name": "search_documents", "arguments": "{\"query\": \"tokens\"}"}
    assert openai[3] == {"role": "tool", "tool_call_id": "c1", "name": "search_documents", "content": "{\"results\": []}"}

    system, contents = llm._gemini_contents(messages)
    assert system == {"parts": [{"text": "sys"}]}
    assert contents[1] == {"role": "model", "parts": [{"functionCall": {"name": "search_documents", "args": {"query": "tokens"}}}]}
    assert contents[2]["parts"][0]["functionResponse"]["name"] == "search_documents"
