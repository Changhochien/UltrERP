#!/usr/bin/env python3
"""
FIA Mock Server — simulates the Fiscal Information Agency (FIA) eInvoice API.

Runs on localhost:8080 and simulates:
  POST /api/invoice/submit  — receives A0101 XML, returns ACK or REJECT
  GET  /api/invoice/status/<ref>  — returns current state of a submission
  GET  /health                — health check endpoint

State machine simulation:
  PENDING → QUEUED → SENT → ACKED | FAILED → RETRYING → DEAD_LETTER

Mock behavior:
  - Valid XML with seller BAN check passes → ACK with reference number
  - Invalid XML (malformed, missing fields, bad check digit) → REJECT
  - Random 20% chance of FAILED on first attempt (to demo retry logic)
  - 48-hour check is bypassed in mock (any timestamp accepted)
  - After 3 retry failures → DEAD_LETTER

No real FIA credentials are used; this is a standalone mock for PoC only.
"""

import http.server
import socketserver
import json
import threading
import time
import re
import random
import uuid
from datetime import datetime, date, timedelta
from typing import Literal, Optional
from xml.etree import ElementTree as ET

# ─── Configuration ───────────────────────────────────────────────────────────

PORT = 8080
HOST = "localhost"

# FIA namespace (MIG 4.1)
MIG_NS = "urn:GEINV:Message:4.1"
NSMAP = {"mig": MIG_NS}


# ─── In-memory store (thread-safe) ──────────────────────────────────────────

class InvoiceStore:
    """
    Thread-safe in-memory store for invoice submissions.
    Simulates FIA platform's state machine.
    """

    def __init__(self):
        self._lock = threading.RLock()
        # ref → {
        #   "xml": raw bytes,
        #   "state": PENDING|QUEUED|SENT|ACKED|FAILED|RETRYING|DEAD_LETTER,
        #   "invoice_number": str,
        #   "invoice_date": str,
        #   "created_at": datetime,
        #   "retry_count": int,
        #   "error_message": str|None,
        # }
        self._store: dict[str, dict] = {}

    def submit(self, ref: str, xml: bytes, inv_num: str, inv_date: str) -> None:
        with self._lock:
            self._store[ref] = {
                "xml": xml,
                "state": "PENDING",
                "invoice_number": inv_num,
                "invoice_date": inv_date,
                "created_at": datetime.now(),
                "retry_count": 0,
                "error_message": None,
            }

    def get(self, ref: str) -> Optional[dict]:
        with self._lock:
            return self._store.get(ref)

    def update_state(
        self, ref: str, state: str, error: str | None = None
    ) -> bool:
        with self._lock:
            if ref not in self._store:
                return False
            self._store[ref]["state"] = state
            if error:
                self._store[ref]["error_message"] = error
            return True

    def increment_retry(self, ref: str) -> int:
        with self._lock:
            if ref in self._store:
                self._store[ref]["retry_count"] += 1
                return self._store[ref]["retry_count"]
            return 0

    def list_all(self) -> list[dict]:
        with self._lock:
            return list(self._store.values())


_store = InvoiceStore()


# ─── State machine simulator ─────────────────────────────────────────────────

class StateMachine:
    """
    Simulates FIA platform-side state transitions.
    In production, these transitions happen server-side.
    Here we run a background thread to advance submitted invoices.
    """

    def __init__(self, store: InvoiceStore):
        self._store = store
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[fia_mock] State machine started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self):
        while self._running:
            try:
                self._advance_all()
            except Exception as e:
                print(f"[fia_mock] StateMachine error: {e}")
            time.sleep(1.5)

    def _advance_all(self):
        """Advance PENDING→QUEUED→SENT→ACKED|FAILED for each submission."""
        now = datetime.now()
        for ref, record in list(self._store._store.items()):
            state = record["state"]
            created = record["created_at"]
            retries = record["retry_count"]

            if state == "PENDING":
                if (now - created).total_seconds() > 0.5:
                    self._store.update_state(ref, "QUEUED")

            elif state == "QUEUED":
                if (now - created).total_seconds() > 1.5:
                    # Simulate 20% failure rate on first send
                    if random.random() < 0.20:
                        self._store.update_state(
                            ref, "FAILED",
                            error="MIG_XML_CORRUPT: simulated transmission error"
                        )
                    else:
                        self._store.update_state(ref, "SENT")

            elif state == "SENT":
                # Short delay then ACK
                if (now - created).total_seconds() > 2.5:
                    self._store.update_state(ref, "ACKED")

            elif state == "FAILED":
                # Auto-retry up to 3 times
                if retries < 3:
                    if (now - created).total_seconds() > 3 + retries * 2:
                        self._store.increment_retry(ref)
                        # Retry succeeds on 2nd+ attempt
                        self._store.update_state(ref, "RETRYING")

            elif state == "RETRYING":
                if (now - created).total_seconds() > 5:
                    if random.random() < 0.7:   # 70% chance retry succeeds
                        self._store.update_state(ref, "SENT")
                    else:
                        if retries >= 3:
                            self._store.update_state(
                                ref, "DEAD_LETTER",
                                error="MAX_RETRIES_EXCEEDED"
                            )
                        else:
                            self._store.update_state(ref, "FAILED")


_sm = StateMachine(_store)


# ─── XML Validation (minimal structural check) ──────────────────────────────

def _elt_text(el: ET.Element | None) -> str:
    """Return trimmed text of element, or '' if None/has no text."""
    if el is None:
        return ""
    return (el.text or "").strip()


def _has_children(el: ET.Element | None) -> bool:
    """Return True if element has at least one child element."""
    if el is None:
        return False
    return any(c.tag.startswith("{") for c in el)


def validate_mig41_xml(xml_bytes: bytes) -> tuple[bool, str]:
    """
    Minimal MIG 4.1 A0101 structural validation.
    Returns (is_valid, error_message).
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return False, f"XML parse error: {e}"

    # Must be Invoice element
    if root.tag != f"{{{MIG_NS}}}Invoice":
        return False, f"Root element must be {{urn:GEINV:Message:4.1}}Invoice, got: {root.tag}"

    # Main block required
    main = root.find(f"{{{MIG_NS}}}Main")
    if main is None:
        return False, "Missing Main block"

    # Required leaf fields in Main (check text content)
    required_leaf_tags = [
        "InvoiceNumber", "InvoiceDate", "InvoiceTime",
        "RelateNumber", "InvoiceType", "GroupMark", "DonateMark",
    ]

    for tag in required_leaf_tags:
        el = main.find(f"{{{MIG_NS}}}{tag}")
        if not _elt_text(el):
            return False, f"Missing or empty required field: Main/{tag}"

    # Required container fields in Main (check children exist)
    required_container_tags = ["Seller", "Buyer", "Details", "Amount"]

    for tag in required_container_tags:
        el = main.find(f"{{{MIG_NS}}}{tag}")
        if not _has_children(el):
            return False, f"Missing or empty required field: Main/{tag}"

    # Seller.Identifier
    seller = main.find(f"{{{MIG_NS}}}Seller")
    sid = seller.find(f"{{{MIG_NS}}}Identifier") if seller is not None else None
    if not _elt_text(sid):
        return False, "Missing Seller/Identifier"

    # Buyer.Identifier
    buyer = main.find(f"{{{MIG_NS}}}Buyer")
    bid = buyer.find(f"{{{MIG_NS}}}Identifier") if buyer is not None else None
    if not _elt_text(bid):
        return False, "Missing Buyer/Identifier"

    # Details must have at least one ProductItem
    details = main.find(f"{{{MIG_NS}}}Details")
    if not _has_children(details):
        return False, "Missing Details/ProductItem block"
    items = details.findall(f"{{{MIG_NS}}}ProductItem") if details else []
    if not items:
        return False, "At least one ProductItem is required in Details"

    # Amount block required fields
    amount = main.find(f"{{{MIG_NS}}}Amount")
    if amount is not None:
        for amt_tag in ("SalesAmount", "TaxType", "TaxRate", "TaxAmount", "TotalAmount"):
            el = amount.find(f"{{{MIG_NS}}}{amt_tag}")
            if not _elt_text(el):
                return False, f"Missing required Amount/{amt_tag}"

    return True, ""


def check_ban_check_digit(ban: str) -> bool:
    """Verify BAN check digit using mod-10 weighting (9-char: 8 digits + check)."""
    if not re.fullmatch(r"\d{9}", ban):
        return False
    digits = [int(d) for d in ban]
    weighted = sum(d * w for d, w in zip(digits[:8], [1, 2] * 4))
    check = (10 - (weighted % 10)) % 10
    return check == digits[8]


def extract_fields(xml_bytes: bytes) -> dict:
    """Extract key fields from submitted XML for logging/ACK."""
    fields = {}
    try:
        root = ET.fromstring(xml_bytes)
        main = root.find(f"{{{MIG_NS}}}Main")
        if main is not None:
            inv_num = main.find(f"{{{MIG_NS}}}InvoiceNumber")
            if inv_num is not None:
                fields["invoice_number"] = inv_num.text
            inv_date = main.find(f"{{{MIG_NS}}}InvoiceDate")
            if inv_date is not None:
                fields["invoice_date"] = inv_date.text
            seller = main.find(f"{{{MIG_NS}}}Seller")
            if seller is not None:
                sid = seller.find(f"{{{MIG_NS}}}Identifier")
                if sid is not None:
                    fields["seller_ban"] = sid.text
            buyer = main.find(f"{{{MIG_NS}}}Buyer")
            if buyer is not None:
                bid = buyer.find(f"{{{MIG_NS}}}Identifier")
                if bid is not None:
                    fields["buyer_ban"] = bid.text
    except ET.ParseError:
        pass
    return fields


# ─── 48-hour check (mock: always passes) ────────────────────────────────────

def check_48hour_window(invoice_date_str: str, invoice_time_str: str) -> tuple[bool, str]:
    """
    Verify invoice was issued within the 48-hour window.
    In production: compare InvoiceDate+InvoiceTime vs server receive timestamp.
    In mock: always return True.
    """
    # Mock always passes
    return True, ""


# ─── ACK / REJECT Response builders ─────────────────────────────────────────

def build_ack_response(
    ref: str, invoice_number: str, state: str, timestamp: str
) -> dict:
    """Build a FIA-style ACK (accepted) response."""
    return {
        "reference_number": ref,
        "invoice_number": invoice_number,
        "status": "ACCEPTED",
        "state": state,
        "timestamp": timestamp,
        "message": "Invoice submitted successfully",
        "details": {
            "next_state_check_url": f"http://{HOST}:{PORT}/api/invoice/status/{ref}",
            "retry_deadline": (
                datetime.now() + timedelta(hours=48)
            ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        },
    }


def build_reject_response(
    error_code: str, error_message: str, timestamp: str
) -> dict:
    """Build a FIA-style REJECT response."""
    return {
        "status": "REJECTED",
        "error_code": error_code,
        "error_message": error_message,
        "timestamp": timestamp,
        "guidance": "Fix the indicated errors and resubmit as a new submission",
    }


def build_status_response(ref: str, record: dict) -> dict:
    """Build a state-check response."""
    return {
        "reference_number": ref,
        "invoice_number": record["invoice_number"],
        "state": record["state"],
        "retry_count": record["retry_count"],
        "error_message": record["error_message"],
        "submitted_at": record["created_at"].strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    }


# ─── HTTP Request Handler ─────────────────────────────────────────────────────

class FIAHandler(http.server.BaseHTTPRequestHandler):
    """Handles FIA API mock endpoints."""

    # Suppress default logging
    def log_message(self, format, *args):
        print(f"[fia_mock] {args[0]}")

    def _send_json(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("X-Request-ID", str(uuid.uuid4())[:8])
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8"))

    def _read_body(self) -> bytes:
        content_len = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_len)

    # ── GET /health ───────────────────────────────────────────────────────────

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {
                "status": "ok",
                "service": "FIA Mock Server",
                "version": "4.1-mock",
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            })
            return

        # GET /api/invoice/status/<ref>
        m = re.match(r"^/api/invoice/status/([A-Za-z0-9\-]+)$", self.path)
        if m:
            ref = m.group(1)
            record = _store.get(ref)
            if record is None:
                self._send_json(404, {
                    "error": "Submission reference not found",
                    "reference_number": ref,
                })
                return
            self._send_json(200, build_status_response(ref, record))
            return

        self._send_json(404, {"error": "Not found", "path": self.path})

    # ── POST /api/invoice/submit ─────────────────────────────────────────────

    def do_POST(self):
        # Only accept the submit endpoint
        if self.path != "/api/invoice/submit":
            self._send_json(404, {"error": "Not found", "path": self.path})
            return

        body = self._read_body()
        if not body:
            self._send_json(400, build_reject_response(
                "EMPTY_BODY", "Request body cannot be empty",
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
            ))
            return

        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

        # ── Validate XML ──────────────────────────────────────────────────────
        is_valid, val_err = validate_mig41_xml(body)
        if not is_valid:
            print(f"[fia_mock] REJECT: {val_err}")
            self._send_json(400, build_reject_response(
                "MIG_XML_INVALID", val_err, ts
            ))
            return

        # ── Extract fields ────────────────────────────────────────────────────
        fields = extract_fields(body)

        # ── Validate seller BAN check digit ──────────────────────────────────
        seller_ban = fields.get("seller_ban", "")
        if seller_ban and not check_ban_check_digit(seller_ban):
            self._send_json(400, build_reject_response(
                "BAN_CHECK_DIGIT_INVALID",
                f"Seller BAN check digit invalid: {seller_ban}",
                ts
            ))
            return

        # ── 48-hour window check (mock: always pass) ───────────────────────────
        inv_date_str = fields.get("invoice_date", "")
        inv_time_str = "00:00:00"
        ok_48, err_48 = check_48hour_window(inv_date_str, inv_time_str)
        if not ok_48:
            self._send_json(400, build_reject_response(
                "SUBMISSION_LATE", f"48-hour window violated: {err_48}", ts
            ))
            return

        # ── Accept submission ─────────────────────────────────────────────────
        ref = f"MIG41-{uuid.uuid4().hex[:12].upper()}"
        inv_num = fields.get("invoice_number", "UNKNOWN")
        _store.submit(ref, body, inv_num, inv_date_str)

        print(f"[fia_mock] ACK: ref={ref} inv={inv_num} date={inv_date_str}")

        self._send_json(200, build_ack_response(
            ref=ref,
            invoice_number=inv_num,
            state="PENDING",
            timestamp=ts,
        ))


# ─── Launch ──────────────────────────────────────────────────────────────────

def run_server(port: int = PORT):
    print("=" * 60)
    print("  FIA Mock Server — MIG 4.1 PoC")
    print(f"  Listening on http://{HOST}:{port}")
    print("  Endpoints:")
    print(f"    POST /api/invoice/submit")
    print(f"    GET  /api/invoice/status/<ref>")
    print(f"    GET  /health")
    print("=" * 60)

    _sm.start()

    with socketserver.TCPServer((HOST, port), FIAHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[fia_mock] Shutting down...")
            _sm.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FIA Mock Server")
    parser.add_argument("--port", "-p", type=int, default=PORT, help="Port to listen on")
    args = parser.parse_args()
    run_server(port=args.port)
