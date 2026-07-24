from fastapi.testclient import TestClient

import customer.customers as customer_customers
import product_chat
import repair_chat
import ticket.tickets as ticket_main
from app import app

client = TestClient(app)


def fake_chat(*responses):
    it = iter(responses)
    return lambda **kwargs: next(it)


def capture_tickets(monkeypatch):
    tickets = []
    monkeypatch.setattr(ticket_main, "insert_ticket", tickets.append)
    return tickets


def test_minor_path_writes_no_ticket(monkeypatch):
    tickets = capture_tickets(monkeypatch)
    monkeypatch.setattr(
        repair_chat.llm, "chat",
        fake_chat({"message": {"role": "assistant", "content": "Here are the repair steps."}}),
    )
    res = client.post("/chat", json={"message": "my wheelchair has a flat tire"},
                      headers={"X-Session-Id": "minor-session"})
    assert res.status_code == 200
    assert res.json()["reply"] == "Here are the repair steps."
    assert not tickets


def test_major_path_writes_ticket_with_server_severity(monkeypatch):
    tickets = capture_tickets(monkeypatch)
    monkeypatch.setattr(
        customer_customers, "find_customer",
        lambda name=None, client_number=None: [{
            "client_number": "TEST-002",
            "name": "Alex",
            "contact_info": "alex@example.com",
            "address": "1 Main St",
        }],
    )
    lookup_call = {"function": {"name": "lookup_customer", "arguments": {"name": "Alex"}}}
    tool_call = {
        "function": {
            "name": "create_replacement_request",
            "arguments": {
                "product": "Rolstoel",
                "issue": "scheur in frame",
                "contact_name": "Alex",
                "contact_info": "alex@example.com",
                "address": "1 Main St",
                "notes": "serial WC-42",
                "client_number": "TEST-002",
            },
        }
    }
    monkeypatch.setattr(
        repair_chat.llm, "chat",
        fake_chat(
            {"message": {"role": "assistant", "content": "", "tool_calls": [lookup_call]}},
            {"message": {"role": "assistant", "content": "Found you, Alex."}},
            {"message": {"role": "assistant", "content": "", "tool_calls": [tool_call]}},
            {"message": {"role": "assistant", "content": "Ticket logged, replacement on the way."}},
        ),
    )
    session_id = "major-session"
    res1 = client.post(
        "/chat",
        json={"message": "I'm Alex, the frame is cracked"},
        headers={"X-Session-Id": session_id},
    )
    assert res1.status_code == 200

    res2 = client.post(
        "/chat",
        json={"message": "Confirmed: email alex@example.com, pickup at 1 Main St"},
        headers={"X-Session-Id": session_id},
    )
    assert res2.status_code == 200
    assert res2.json()["reply"] == "Ticket logged, replacement on the way."

    assert len(tickets) == 1
    ticket = tickets[0]
    assert ticket["severity"] == "major"  # resolved server-side from protocols.json
    assert ticket["product"] == "Rolstoel"
    assert ticket["contact_name"] == "Alex"
    assert ticket["ticket_id"]


def test_unregistered_customer_ticket_rejected(monkeypatch):
    tickets = capture_tickets(monkeypatch)
    tool_call = {
        "function": {
            "name": "create_replacement_request",
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
        repair_chat.llm, "chat",
        fake_chat(
            {"message": {"role": "assistant", "content": "", "tool_calls": [tool_call]}},
            {"message": {"role": "assistant", "content": "Could you give me your name and address?"}},
        ),
    )
    res = client.post("/chat", json={"message": "the frame is cracked"},
                      headers={"X-Session-Id": "unregistered-session"})
    assert res.status_code == 200
    assert not tickets  # no verified customer record, ticket rejected regardless of details given


def test_lookup_customer_then_ticket_uses_stored_details(monkeypatch):
    tickets = capture_tickets(monkeypatch)
    monkeypatch.setattr(
        customer_customers, "find_customer",
        lambda name=None, client_number=None: [{
            "client_number": "TEST-001",
            "name": "Jan Jansen",
            "contact_info": "jan@example.test",
            "address": "Teststraat 1, Amsterdam",
        }],
    )
    lookup_call = {"function": {"name": "lookup_customer", "arguments": {"name": "Jan Jansen"}}}
    ticket_call = {
        "function": {
            "name": "create_replacement_request",
            "arguments": {
                "product": "rolstoel",
                "issue": "scheur in frame",
                "contact_name": "onbekend",
                "contact_info": "onbekend",
                "address": "onbekend",
                "client_number": "TEST-001",
            },
        }
    }
    monkeypatch.setattr(
        repair_chat.llm, "chat",
        fake_chat(
            {"message": {"role": "assistant", "content": "", "tool_calls": [lookup_call]}},
            {"message": {"role": "assistant", "content": "Ik heb je gevonden, Jan."}},
            {"message": {"role": "assistant", "content": "", "tool_calls": [ticket_call]}},
            {"message": {"role": "assistant", "content": "Ticket aangemaakt."}},
        ),
    )
    session_id = "customer-session"
    res1 = client.post("/chat", json={"message": "Ik ben Jan Jansen"},
                       headers={"X-Session-Id": session_id})
    assert res1.status_code == 200

    res2 = client.post("/chat", json={"message": "ja, klopt"},
                       headers={"X-Session-Id": session_id})
    assert res2.status_code == 200

    assert len(tickets) == 1
    ticket = tickets[0]
    assert ticket["contact_name"] == "Jan Jansen"  # from the DB, not the model's "onbekend"
    assert ticket["contact_info"] == "jan@example.test"
    assert ticket["address"] == "Teststraat 1, Amsterdam"
    assert ticket["client_number"] == "TEST-001"


def test_client_number_without_lookup_still_rejected(monkeypatch):
    tickets = capture_tickets(monkeypatch)
    tool_call = {
        "function": {
            "name": "create_replacement_request",
            "arguments": {
                "product": "rolstoel",
                "issue": "scheur in frame",
                "contact_name": "John Doe",
                "contact_info": "john.doe@example.com",
                "address": "123 Main St, Anytown USA",
                "client_number": "TEST-001",
            },
        }
    }
    monkeypatch.setattr(
        repair_chat.llm, "chat",
        fake_chat(
            {"message": {"role": "assistant", "content": "", "tool_calls": [tool_call]}},
            {"message": {"role": "assistant", "content": "Kun je je gegevens geven?"}},
        ),
    )
    res = client.post("/chat", json={"message": "het frame is gescheurd"},
                      headers={"X-Session-Id": "unverified-client-number-session"})
    assert res.status_code == 200
    assert not tickets


def test_product_chat_calls_wheelchair_matcher(monkeypatch):
    tool_call = {
        "function": {
            "name": "find_suitable_wheelchairs",
            "arguments": {"weight_kg": 90, "self_propelled": True},
        }
    }
    monkeypatch.setattr(
        product_chat.llm, "chat",
        fake_chat(
            {"message": {"role": "assistant", "content": "", "tool_calls": [tool_call]}},
            {"message": {"role": "assistant", "content": "Deze rolstoelen passen bij u."}},
        ),
    )
    res = client.post(
        "/chat/product",
        json={"message": "Ik weeg ongeveer 90 kg en rijd zelf"},
        headers={"X-Session-Id": "product-session"},
    )
    assert res.status_code == 200
    assert res.json()["reply"] == "Deze rolstoelen passen bij u."
