import json

from fastapi.testclient import TestClient

import app as app_module
import ticket.main as ticket_main
from app import app

client = TestClient(app)


def fake_chat(*responses):
    it = iter(responses)
    return lambda **kwargs: next(it)


def test_minor_path_writes_no_ticket(monkeypatch, tmp_path):
    tickets = tmp_path / "tickets.jsonl"
    monkeypatch.setattr(ticket_main, "TICKETS", tickets)
    monkeypatch.setattr(
        app_module.ollama, "chat",
        fake_chat({"message": {"role": "assistant", "content": "Here are the repair steps."}}),
    )
    res = client.post("/chat", json={"message": "my wheelchair has a flat tire"},
                      headers={"X-Session-Id": "minor-session"})
    assert res.status_code == 200
    assert res.json()["reply"] == "Here are the repair steps."
    assert not tickets.exists()


def test_major_path_writes_ticket_with_server_severity(monkeypatch, tmp_path):
    tickets = tmp_path / "tickets.jsonl"
    monkeypatch.setattr(ticket_main, "TICKETS", tickets)
    tool_call = {
        "function": {
            "name": "log_replacement_request",
            "arguments": {
                "product": "Rolstoel",
                "issue": "scheur in frame",
                "contact_name": "Alex",
                "contact_info": "alex@example.com",
                "address": "1 Main St",
                "notes": "serial WC-42",
            },
        }
    }
    monkeypatch.setattr(
        app_module.ollama, "chat",
        fake_chat(
            {"message": {"role": "assistant", "content": "", "tool_calls": [tool_call]}},
            {"message": {"role": "assistant", "content": "Ticket logged, replacement on the way."}},
        ),
    )
    res = client.post(
        "/chat",
        json={"message": "Confirmed: I'm Alex, email alex@example.com, pickup at 1 Main St"},
        headers={"X-Session-Id": "major-session"},
    )
    assert res.status_code == 200
    assert res.json()["reply"] == "Ticket logged, replacement on the way."

    lines = tickets.read_text().splitlines()
    assert len(lines) == 1
    ticket = json.loads(lines[0])
    assert ticket["severity"] == "major"  # resolved server-side from protocols.json
    assert ticket["product"] == "Rolstoel"
    assert ticket["contact_name"] == "Alex"
    assert ticket["ticket_id"]


def test_fabricated_contact_details_rejected(monkeypatch, tmp_path):
    tickets = tmp_path / "tickets.jsonl"
    monkeypatch.setattr(ticket_main, "TICKETS", tickets)
    tool_call = {
        "function": {
            "name": "log_replacement_request",
            "arguments": {
                "product": "rolstoel",
                "issue": "scheur in frame",
                "contact_name": "John Doe",
                "contact_info": "john.doe@example.com",
                "address": "123 Main St, Anytown USA",
            },
        }
    }
    monkeypatch.setattr(
        app_module.ollama, "chat",
        fake_chat(
            {"message": {"role": "assistant", "content": "", "tool_calls": [tool_call]}},
            {"message": {"role": "assistant", "content": "Could you give me your name and address?"}},
        ),
    )
    res = client.post("/chat", json={"message": "the frame is cracked"},
                      headers={"X-Session-Id": "fabricated-session"})
    assert res.status_code == 200
    assert not tickets.exists()  # no ticket with invented details
