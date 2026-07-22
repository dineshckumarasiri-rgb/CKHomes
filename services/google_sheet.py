from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

import gspread
from google.oauth2.service_account import Credentials


class StorageError(RuntimeError):
    pass


class GoogleSheetService:
    HEADERS = {
        "Users": ["user_id","username","role","status","created_at"],
        "Invitations": ["invitation_id","token","student_name","mobile","email","expires_at","status","created_by","created_at","used_at","application_id"],
        "Applications": ["application_id","invitation_id","submitted_at","status","student_id","full_name","name_with_initials","nic","date_of_birth","gender","nationality","mobile","whatsapp","email","address","guardian_name","guardian_relationship","guardian_mobile","guardian_address","university","faculty","degree","university_reg_no","academic_year","expected_graduation_year","expected_checkin","preferred_block","preferred_room_type","monthly_fee","deposit_required","profile_photo_url","nic_front_url","nic_back_url","university_id_url","boarding_agreement_url","guardian_nic_url","declaration_accepted"],
        "Students": ["student_id","application_id","full_name","name_with_initials","nic","date_of_birth","gender","nationality","mobile","whatsapp","email","address","guardian_name","guardian_relationship","guardian_mobile","guardian_address","university","faculty","degree","university_reg_no","academic_year","expected_graduation_year","joining_date","hostel_block","block_id","room_no","room_id","bed_no","bed_id","monthly_fee","student_status","approved_at","withdrawal_date","withdrawal_reason","profile_photo_url","nic_front_url","nic_back_url","university_id_url","boarding_agreement_url","guardian_nic_url"],
        "HostelBlocks": ["block_id","block_name","address","floors","status","created_at"],
        "Rooms": ["room_id","block_id","block_name","room_no","room_type","capacity","monthly_charge","status","created_at"],
        "RoomPriceHistory": ["price_id","room_id","block_id","block_name","room_no","monthly_charge","effective_from","apply_scope","status","created_by","created_at"],
        "MonthlyFees": ["fee_id","student_id","student_name","room_id","room_no","fee_month","amount_due","amount_paid","balance","status","generated_at"],
        "Beds": ["bed_id","room_id","block_id","block_name","room_no","bed_no","status","student_id","student_name","created_at","updated_at"],
        "RoomAssignments": ["assignment_id","student_id","student_name","block_id","block_name","room_id","room_no","bed_id","bed_no","start_date","end_date","status","created_at"],
        "Payments": ["payment_id","student_id","student_name","revenue_category","month","amount","payment_date","method","reference_no","receipt_no","block_name","remarks","status","created_by","created_at","updated_by","updated_at","edit_reason","void_reason","voided_by","voided_at","delete_reason","deleted_by","deleted_at","restored_by","restored_at"],
        "Costs": ["cost_id","cost_date","category","description","supplier","block_name","room_no","amount","method","reference_no","bill_no","remarks","status","created_by","created_at"],
        "StudentDeposits": ["deposit_id","student_id","student_name","required_amount","received_amount","payment_date","payment_method","payment_reference","status","withdrawal_date","total_deductions","refundable_amount","refunded_amount","balance_to_refund","last_refund_date","remarks","updated_by","updated_at"],
        "DepositRefunds": ["refund_id","deposit_id","student_id","student_name","refund_date","amount","method","reference_no","remarks","created_by","created_at"],
        "DepositDeductions": ["deduction_id","deposit_id","student_id","student_name","deduction_date","amount","reason","approved_by","created_at"],
        "Assets": ["asset_id","asset_name","category","quantity","block_name","room_no","condition","purchase_value","status","updated_at"],
        "Withdrawals": ["withdrawal_id","student_id","student_name","withdrawal_date","reason","deposit_status","created_by","created_at"],
        "Settings": ["key","value","updated_at"],
        "Logs": ["log_id","action","entity_type","entity_id","details","performed_by","created_at"],
    }

    def __init__(self, spreadsheet_name: str, credentials_info: dict[str, Any], cache_ttl: int = 90):
        self.spreadsheet_name = spreadsheet_name
        self.credentials_info = dict(credentials_info)
        self.cache_ttl = max(10, int(cache_ttl))
        self._book = None
        self._worksheets: dict[str, Any] = {}
        self._headers: dict[str, list[str]] = {}
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = threading.RLock()

    def _retry(self, operation, label: str):
        delay = 1
        for attempt in range(5):
            try:
                return operation()
            except Exception as exc:
                text = str(exc)
                retryable = any(x in text for x in ("429", "Quota exceeded", "RESOURCE_EXHAUSTED", "503"))
                if not retryable or attempt == 4:
                    raise StorageError(f"{label}: {exc}") from exc
                time.sleep(delay)
                delay *= 2

    def _spreadsheet(self):
        with self._lock:
            if self._book is not None:
                return self._book
            def connect():
                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
                creds = Credentials.from_service_account_info(self.credentials_info, scopes=scopes)
                return gspread.authorize(creds).open(self.spreadsheet_name)
            self._book = self._retry(connect, f"Could not connect to Google Sheet '{self.spreadsheet_name}'")
            return self._book

    def _worksheet(self, table: str):
        if table not in self.HEADERS:
            raise KeyError(table)
        with self._lock:
            if table in self._worksheets:
                return self._worksheets[table]
            headers = self.HEADERS[table]
            book = self._spreadsheet()
            def open_or_create():
                try:
                    ws = book.worksheet(table)
                except gspread.WorksheetNotFound:
                    ws = book.add_worksheet(title=table, rows=2000, cols=max(30, len(headers) + 2))
                    ws.append_row(headers, value_input_option="USER_ENTERED")
                existing = ws.row_values(1)
                if not existing:
                    ws.append_row(headers, value_input_option="USER_ENTERED")
                    existing = headers[:]
                missing = [h for h in headers if h not in existing]
                if missing:
                    existing += missing
                    ws.update(values=[existing], range_name="A1")
                self._headers[table] = existing
                return ws
            ws = self._retry(open_or_create, f"Could not open worksheet '{table}'")
            self._worksheets[table] = ws
            return ws

    def initialize(self) -> None:
        self._spreadsheet()
        for table in self.HEADERS:
            self._worksheet(table)

    def invalidate(self, table: str | None = None) -> None:
        with self._lock:
            self._cache.clear() if table is None else self._cache.pop(table, None)

    def get_table(self, table: str, force_refresh: bool = False) -> list[dict[str, Any]]:
        now_ts = time.monotonic()
        cached = self._cache.get(table)
        if not force_refresh and cached and now_ts - cached[0] < self.cache_ttl:
            return [dict(r) for r in cached[1]]
        ws = self._worksheet(table)
        rows = self._retry(lambda: ws.get_all_records(default_blank=""), f"Could not read worksheet '{table}'")
        self._cache[table] = (time.monotonic(), rows)
        return [dict(r) for r in rows]

    def add_record(self, table: str, record: dict[str, Any]) -> None:
        headers = self.HEADERS[table]
        ws = self._worksheet(table)
        self._retry(lambda: ws.append_row([record.get(h, "") for h in headers], value_input_option="USER_ENTERED"), f"Could not add record to '{table}'")
        self.invalidate(table)

    def update_record(self, table: str, id_field: str, record_id: str, changes: dict[str, Any]) -> bool:
        ws = self._worksheet(table)
        headers = self._headers.get(table) or self.HEADERS[table]
        if id_field not in headers:
            return False
        try:
            cell = ws.find(str(record_id), in_column=headers.index(id_field) + 1)
        except gspread.CellNotFound:
            return False
        updates = []
        for key, value in changes.items():
            if key in headers:
                updates.append({"range": ws.cell(cell.row, headers.index(key)+1).address, "values": [[value]]})
        if updates:
            self._retry(lambda: ws.batch_update(updates), f"Could not update record in '{table}'")
            self.invalidate(table)
        return True

    def delete_record(self, table: str, id_field: str, record_id: str) -> bool:
        ws = self._worksheet(table)
        headers = self._headers.get(table) or self.HEADERS[table]
        try:
            cell = ws.find(str(record_id), in_column=headers.index(id_field)+1)
        except gspread.CellNotFound:
            return False
        self._retry(lambda: ws.delete_rows(cell.row), f"Could not delete record from '{table}'")
        self.invalidate(table)
        return True

    def find_one(self, table: str, field: str, value: str) -> dict[str, Any] | None:
        return next((r for r in self.get_table(table) if str(r.get(field, "")) == str(value)), None)

    def next_student_id(self) -> str:
        year = datetime.now().year
        existing = {str(r.get("student_id", "")) for r in self.get_table("Students")}
        n = 1
        while f"CKH-{year}-{n:04d}" in existing:
            n += 1
        return f"CKH-{year}-{n:04d}"
