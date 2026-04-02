#!/usr/bin/env python3
"""
submit_invoice.py — FIA Invoice Submission Client

Workflow:
  1. Read MIG 4.1 XML from sample_invoice.xml (or given path)
  2. Validate basic pre-conditions (file exists, non-empty, valid XML)
  3. POST to mock FIA server at http://localhost:8080/api/invoice/submit
  4. Handle responses:
       ACCEPTED → poll for state transitions until ACK or terminal state
       REJECTED → print error details and exit with non-zero code
  5. Demonstrate retry logic when state becomes FAILED

State machine transitions (as simulated by fia_mock_server):
  PENDING → QUEUED → SENT → ACKED | FAILED → RETRYING → DEAD_LETTER

Usage:
  python submit_invoice.py
  python submit_invoice.py --xml my_invoice.xml
  python submit_invoice.py --xml my_invoice.xml --server http://localhost:8080
  python submit_invoice.py --xml bad_invoice.xml  # triggers REJECT demo
"""

import http.client
import json
import sys
import time
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_SERVER = "localhost"
DEFAULT_PORT = 8080
SUBMIT_ENDPOINT = "/api/invoice/submit"
STATUS_ENDPOINT = "/api/invoice/status/{ref}"
POLL_INTERVAL = 1.0        # seconds between status polls
MAX_POLL_ATTEMPTS = 30     # stop polling after this many attempts
TERMINAL_STATES = {"ACKED", "DEAD_LETTER"}


# ─── HTTP Client Helpers ──────────────────────────────────────────────────────

class FIAClient:
    """Lightweight FIA API client for the mock server."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._conn: http.client.HTTPConnection | None = None

    def _connect(self):
        if self._conn:
            self._conn.close()
        self._conn = http.client.HTTPConnection(self.host, self.port, timeout=10)

    def _disconnect(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def submit(self, xml_bytes: bytes) -> tuple[int, dict]:
        """
        POST XML to /api/invoice/submit.
        Returns (HTTP status code, parsed JSON body).
        """
        self._connect()
        try:
            headers = {
                "Content-Type": "application/xml; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": "UltrERP-FIA-Client/1.0",
            }
            self._conn.request("POST", SUBMIT_ENDPOINT, body=xml_bytes, headers=headers)
            resp = self._conn.getresponse()
            body = resp.read()
            try:
                body_json = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body_json = {"raw": body.decode("utf-8", errors="replace")}
            return resp.status, body_json
        finally:
            self._disconnect()

    def get_status(self, ref: str) -> tuple[int, dict]:
        """GET /api/invoice/status/<ref>."""
        self._connect()
        try:
            self._conn.request(
                "GET",
                STATUS_ENDPOINT.format(ref=ref),
                headers={"Accept": "application/json", "User-Agent": "UltrERP-FIA-Client/1.0"}
            )
            resp = self._conn.getresponse()
            body = resp.read()
            try:
                body_json = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body_json = {"raw": body.decode("utf-8", errors="replace")}
            return resp.status, body_json
        finally:
            self._disconnect()


# ─── Submission Logic ────────────────────────────────────────────────────────

def submit_and_track(
    client: FIAClient,
    xml_bytes: bytes,
    invoice_path: str,
    max_retries: int = 3,
) -> bool:
    """
    Submit an invoice XML and poll until a terminal state is reached.
    If FAILED occurs, attempts up to max_retries retries by re-submitting.

    Returns True if invoice reaches ACKED state, False otherwise.
    """

    print(f"\n[submit] Submitting invoice from: {invoice_path}")
    print(f"[submit] Server: http://{client.host}:{client.port}")

    # ── Step 1: Initial submission ────────────────────────────────────────────
    status, body = client.submit(xml_bytes)

    if status == 400 and body.get("status") == "REJECTED":
        print("\n" + "=" * 60)
        print("  REJECTED — Invoice submission rejected by FIA")
        print("=" * 60)
        print(f"  Error Code   : {body.get('error_code', 'N/A')}")
        print(f"  Error Message: {body.get('error_message', 'N/A')}")
        print(f"  Guidance     : {body.get('guidance', 'N/A')}")
        print(f"  Timestamp    : {body.get('timestamp', 'N/A')}")
        print("=" * 60)
        return False

    if status != 200 or body.get("status") != "ACCEPTED":
        print(f"\n[submit] Unexpected response: HTTP {status}")
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return False

    ref = body["reference_number"]
    inv_num = body["invoice_number"]
    current_state = body.get("state", "PENDING")
    ts = body.get("timestamp", "")

    print("\n" + "=" * 60)
    print("  ACCEPTED — Invoice accepted by FIA")
    print("=" * 60)
    print(f"  Reference Number : {ref}")
    print(f"  Invoice Number   : {inv_num}")
    print(f"  Initial State    : {current_state}")
    print(f"  Timestamp        : {ts}")
    print(f"  Status Check URL : {body.get('details', {}).get('next_state_check_url', 'N/A')}")
    print("=" * 60)

    # ── Step 2: Poll state machine ────────────────────────────────────────────
    retry_count = 0
    poll_attempts = 0

    while poll_attempts < MAX_POLL_ATTEMPTS:
        time.sleep(POLL_INTERVAL)
        poll_attempts += 1

        status_s, body_s = client.get_status(ref)

        if status_s == 404:
            print(f"[submit] Ref {ref} not found yet (attempt {poll_attempts})")
            continue

        if status_s != 200:
            print(f"[submit] Status poll HTTP error: {status_s}")
            continue

        state = body_s.get("state", "UNKNOWN")
        error_msg = body_s.get("error_message")
        retry_cnt = body_s.get("retry_count", 0)

        print(
            f"[submit] poll {poll_attempts:2d} | ref={ref} | "
            f"state={state:12s} | retries={retry_cnt} | error={error_msg or 'none'}"
        )

        # Terminal: ACKED
        if state == "ACKED":
            print("\n" + "=" * 60)
            print("  SUCCESS — Invoice ACKed by FIA")
            print("=" * 60)
            print(f"  Reference Number : {ref}")
            print(f"  Invoice Number   : {inv_num}")
            print(f"  Final State     : ACKED")
            print(f"  Timestamp        : {body_s.get('timestamp', 'N/A')}")
            print("=" * 60)
            return True

        # Terminal: DEAD_LETTER
        if state == "DEAD_LETTER":
            print("\n" + "!" * 60)
            print("  FAILURE — Invoice reached DEAD_LETTER (no recovery in mock)")
            print("!" * 60)
            print(f"  Reference Number : {ref}")
            print(f"  Invoice Number   : {inv_num}")
            print(f"  Error            : {error_msg or 'unknown'}")
            print("  Action Required  : Manually inspect and reissue via new submission")
            print("!" * 60)
            return False

        # FAILED: attempt retry by re-submitting
        if state == "FAILED" and retry_count < max_retries:
            retry_count += 1
            print(f"\n[submit] !! FAILED detected — retrying submission ({retry_count}/{max_retries})")

            # Re-submit the same XML (simulates obtaining a new InvoiceNumber
            # in a real retry; here we reuse the same invoice for mock simplicity)
            status_r, body_r = client.submit(xml_bytes)

            if status_r == 400 and body_r.get("status") == "REJECTED":
                print(f"[submit] Retry {retry_count} REJECTED: {body_r.get('error_message')}")
                # Continue polling; maybe a later auto-retry will succeed
            elif status_r == 200 and body_r.get("status") == "ACCEPTED":
                # New ref assigned for retry
                new_ref = body_r.get("reference_number", ref)
                print(f"[submit] Retry {retry_count} accepted, new ref={new_ref}")
                # Update tracking ref
                ref = new_ref

    # Exceeded poll attempts
    print(f"\n[submit] Polling exhausted ({MAX_POLL_ATTEMPTS} attempts)")
    print(f"          Last known state: {current_state}")
    return False


# ─── XML Validation (client-side pre-check) ─────────────────────────────────

def validate_xml_file(path: str) -> tuple[bool, bytes, str]:
    """
    Validate the XML file exists, is readable, and is well-formed.
    Returns (is_valid, xml_bytes, error_message).
    """
    p = Path(path)
    if not p.exists():
        return False, b"", f"File not found: {path}"
    if not p.is_file():
        return False, b"", f"Not a file: {path}"

    try:
        xml_bytes = p.read_bytes()
    except Exception as e:
        return False, b"", f"Cannot read file: {e}"

    if not xml_bytes.strip():
        return False, b"", "File is empty"

    try:
        ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return False, xml_bytes, f"XML not well-formed: {e}"

    return True, xml_bytes, ""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Submit a MIG 4.1 invoice XML to the FIA mock server"
    )
    parser.add_argument(
        "--xml", "-x",
        default="sample_invoice.xml",
        help="Path to MIG 4.1 XML invoice file (default: sample_invoice.xml)"
    )
    parser.add_argument(
        "--server", "-s",
        default=f"http://{DEFAULT_SERVER}:{DEFAULT_PORT}",
        help=f"FIA server URL (default: http://{DEFAULT_SERVER}:{DEFAULT_PORT})"
    )
    parser.add_argument(
        "--retries", "-r",
        type=int, default=3,
        help="Max retry attempts on FAILED state (default: 3)"
    )
    args = parser.parse_args()

    # Parse server URL
    server_url = args.server.rstrip("/")
    if "://" in server_url:
        host_port = server_url.split("://")[1].split("/")[0]
    else:
        host_port = server_url

    if ":" in host_port:
        host, port_s = host_port.split(":")
        port = int(port_s)
    else:
        host, port = host_port, DEFAULT_PORT

    print("=" * 60)
    print("  UltrERP — FIA Invoice Submission Client")
    print(f"  XML File  : {args.xml}")
    print(f"  FIA Server: http://{host}:{port}")
    print("=" * 60)

    # ── Client-side XML validation ────────────────────────────────────────────
    valid, xml_bytes, xml_err = validate_xml_file(args.xml)
    if not valid:
        print(f"\n[submit] FATAL: {xml_err}")
        sys.exit(1)

    # Quick structural pre-check (before sending)
    try:
        root = ET.fromstring(xml_bytes)
        ns = "urn:GEINV:Message:4.1"
        inv_num_el = root.find(f"{{{ns}}}Main/{{{ns}}}InvoiceNumber")
        inv_num = inv_num_el.text if inv_num_el is not None else "UNKNOWN"
        inv_date_el = root.find(f"{{{ns}}}Main/{{{ns}}}InvoiceDate")
        inv_date = inv_date_el.text if inv_date_el is not None else "UNKNOWN"
        seller_el = root.find(f"{{{ns}}}Main/{{{ns}}}Seller/{{{ns}}}Identifier")
        seller_ban = seller_el.text if seller_el is not None else "UNKNOWN"
        print(f"\n[submit] XML pre-check OK")
        print(f"         InvoiceNumber : {inv_num}")
        print(f"         InvoiceDate   : {inv_date}")
        print(f"         Seller BAN   : {seller_ban}")
    except Exception as e:
        print(f"\n[submit] WARNING: XML pre-check failed: {e}")

    # ── Submit ────────────────────────────────────────────────────────────────
    client = FIAClient(host, port)
    success = submit_and_track(client, xml_bytes, args.xml, max_retries=args.retries)

    print()
    if success:
        print("[submit] DONE — Invoice successfully ACKed")
        sys.exit(0)
    else:
        print("[submit] DONE — Invoice submission failed or not ACKed")
        sys.exit(1)


if __name__ == "__main__":
    main()
