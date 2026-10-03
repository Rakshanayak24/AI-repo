"""A small, auditable invoice-processing worker with explicit tools and state."""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).parent
INBOX = ROOT / "data" / "inbox"
LEDGER = ROOT / "data" / "ledger.json"


@dataclass
class Event:
    stage: str
    message: str
    detail: str = ""
    status: str = "done"
    timestamp: str = field(default_factory=lambda: datetime.now().astimezone().strftime("%H:%M:%S"))


@dataclass
class Invoice:
    vendor: str
    invoice_number: str
    amount: float
    currency: str
    due_date: str
    source_file: str


class ToolError(Exception):
    pass


class InvoiceTools:
    """Local file and simulated AP tools. All writes are idempotent by invoice key."""
    def __init__(self, fail_once: bool = False):
        self.fail_once = fail_once
        self._failed = False

    def list_invoices(self) -> list[Path]:
        return sorted(INBOX.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)

    def read_invoice(self, path: Path) -> Invoice:
        text = "\n".join(page.get_text() for page in fitz.open(path))
        def find(pattern: str, label: str) -> str:
            match = re.search(pattern, text, re.I | re.M)
            if not match:
                raise ToolError(f"Could not extract {label} from {path.name}")
            return match.group(1).strip()
        vendor = find(r"^Vendor:\s*(.+)$", "vendor")
        number = find(r"^Invoice\s*(?:No\.?|Number):\s*(.+)$", "invoice number")
        amount = find(r"^Total:\s*((?:INR|USD|EUR|GBP|[₹$€£])?\s*[\d,]+(?:\.\d{2})?)\s*$", "total")
        due = find(r"^Due Date:\s*(\d{4}-\d{2}-\d{2})$", "due date")
        currency = next((code for code in ("INR", "USD", "EUR", "GBP") if code in amount.upper()), None)
        currency = currency or ("INR" if "₹" in amount else "USD" if "$" in amount else "EUR" if "€" in amount else "GBP" if "£" in amount else "INR")
        numeric = float(re.sub(r"[^\d.]", "", amount))
        date.fromisoformat(due)
        return Invoice(vendor, number, numeric, currency, due, path.name)

    def read_ledger(self) -> list[dict[str, Any]]:
        if not LEDGER.exists():
            return []
        return json.loads(LEDGER.read_text(encoding="utf-8"))

    def lookup_invoice(self, number: str) -> dict[str, Any] | None:
        return next((row for row in self.read_ledger() if row["invoice_number"].casefold() == number.casefold()), None)

    def create_bill(self, invoice: Invoice) -> dict[str, Any]:
        # Simulates one transient connector failure so the recovery path is visible.
        if self.fail_once and not self._failed:
            self._failed = True
            raise ToolError("Finance connector timed out (simulated transient error)")
        existing = self.lookup_invoice(invoice.invoice_number)
        if existing:
            return existing
        rows = self.read_ledger()
        row = {**asdict(invoice), "record_id": f"BILL-{len(rows)+1:04d}", "status": "Ready for payment", "created_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        rows.append(row)
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        return row


def _candidate_from_goal(goal: str, files: list[Path]) -> Path:
    normalized_goal = re.sub(r"[^a-z0-9]+", " ", goal.casefold()).strip()
    matches = [p for p in files if re.sub(r"[^a-z0-9]+", " ", p.stem.casefold()).strip() in normalized_goal]
    candidates = matches or files
    # "latest" and unspecified both resolve to newest matching invoice.
    return candidates[0]


def run_task(goal: str, *, fail_once: bool = False, approve: bool = False) -> dict[str, Any]:
    events: list[Event] = []
    tools = InvoiceTools(fail_once=fail_once)
    def log(stage: str, msg: str, detail: str = "", status: str = "done") -> None:
        events.append(Event(stage, msg, detail, status))
    log("Understand", "Interpreted the requested outcome", goal)
    log("Plan", "Read the newest matching invoice → check for duplicates → apply approval policy → save → verify", "Invoice intake · local PDF + AP ledger")
    files = tools.list_invoices()
    if not files:
        log("Observe", "No invoice files are available", str(INBOX), "error")
        return {"status": "blocked", "events": events, "invoice": None, "record": None, "summary": "No invoice found in the local inbox."}
    try:
        path = _candidate_from_goal(goal, files)
        log("Select tool", "Selected the most relevant invoice", path.name)
        invoice = tools.read_invoice(path)
        log("Observe", "Extracted invoice fields from PDF", f"{invoice.vendor} · {invoice.invoice_number} · {invoice.currency} {invoice.amount:,.2f} · due {invoice.due_date}")
        existing = tools.lookup_invoice(invoice.invoice_number)
        if existing:
            log("Recover", "This invoice is already recorded; skipping duplicate write", existing["record_id"], "warning")
            record = existing
        elif invoice.amount >= 100000 and not approve:
            log("Human approval", "Approval required before recording invoices ≥ ₹100,000", f"{invoice.currency} {invoice.amount:,.2f}", "approval")
            return {"status": "needs_approval", "events": events, "invoice": invoice, "record": None, "summary": f"Approval is required before recording invoice {invoice.invoice_number}."}
        else:
            for attempt in range(2):
                try:
                    record = tools.create_bill(invoice)
                    log("Execute", "Recorded invoice in the AP ledger", f"{record['record_id']} · {record['status']}")
                    break
                except ToolError as exc:
                    if attempt:
                        raise
                    log("Recover", "Connector failed; retrying once with the same idempotency key", str(exc), "warning")
                    time.sleep(0.15)
            verified = tools.lookup_invoice(invoice.invoice_number)
            if not verified or verified["record_id"] != record["record_id"]:
                raise ToolError("Post-write verification failed: the ledger record could not be read back")
            log("Verify", "Read-after-write check passed", f"{verified['record_id']} · {verified['invoice_number']} · {verified['currency']} {verified['amount']:,.2f}")
        summary = f"{invoice.vendor} invoice {invoice.invoice_number} recorded as {record['record_id']} for {invoice.currency} {invoice.amount:,.2f}, due {invoice.due_date}."
        return {"status": "complete", "events": events, "invoice": invoice, "record": record, "summary": summary}
    except (ToolError, ValueError, OSError) as exc:
        log("Recover", "Could not safely complete this task", str(exc), "error")
        return {"status": "failed", "events": events, "invoice": None, "record": None, "summary": f"Stopped safely: {exc}"}
