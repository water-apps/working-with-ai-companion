"""Automated checks for the reader companion. Run: python3 -m unittest -v test_labs

These validate the supplied fixtures. They do not evaluate an AI model's output
and they do not prove anything about live systems.
"""
import datetime as dt
import json
import shutil
import tempfile
import threading
import unittest
from decimal import Decimal
from pathlib import Path

import labs

DATA = labs.DATA


class CostsTest(unittest.TestCase):
    def test_aggregates_before_comparing(self):
        s = labs.cost_summary(labs.load_costs())
        self.assertEqual(s["rows_read"], 8)
        by = {r["service"]: r for r in s["services"]}
        self.assertEqual((by["compute"]["2026-10"], by["compute"]["2026-11"]), (Decimal(100), Decimal(160)))
        self.assertEqual(by["storage"]["change"], Decimal(5))
        self.assertEqual(by["network"]["change"], Decimal(5))
        self.assertEqual(s["total"]["change"], Decimal(70))
        self.assertEqual(s["total"]["pct"].quantize(Decimal("0.01")), Decimal("46.67"))
        self.assertEqual(sum(r["change"] for r in s["services"]), s["total"]["change"])


class StateTest(unittest.TestCase):
    def test_one_missing_link_and_no_cloud_changes(self):
        plan = labs.state_plan(json.loads((DATA / "state_simulation.json").read_text()))
        self.assertEqual(plan["status"], "plan")
        self.assertEqual(plan["actions"], [{"action": "link_existing", "address": "database.a", "resource": "demo/account-a"}])
        self.assertEqual(plan["cloud_changes"], 0)

    def test_conflict_stops_for_review(self):
        plan = labs.state_plan(json.loads((DATA / "state_conflict.json").read_text()))
        self.assertEqual(plan["status"], "stop_for_review")
        self.assertEqual(plan["conflicts"][0]["address"], "database.b")

    def test_inputs_are_not_modified(self):
        before = (DATA / "state_simulation.json").read_bytes()
        labs.main(["state"])
        self.assertEqual(before, (DATA / "state_simulation.json").read_bytes())


class CoverageTest(unittest.TestCase):
    expected = ["demo-a", "demo-b", "demo-c"]

    def test_incomplete_ledger_fails(self):
        r = labs.coverage_check(self.expected, json.loads((DATA / "coverage_ledger_incomplete.json").read_text()))
        self.assertFalse(r["pass"]); self.assertEqual(r["missing"], ["demo-b", "demo-c"])

    def test_fixed_ledger_passes(self):
        r = labs.coverage_check(self.expected, json.loads((DATA / "coverage_ledger_fixed.json").read_text()))
        self.assertTrue(r["pass"]); self.assertEqual(r["recorded"], 3)

    def test_duplicates_and_unexpected_are_rejected(self):
        ledger = [{"item": "demo-a", "status": "completed"}, {"item": "demo-a", "status": "completed"},
                  {"item": "demo-b", "status": "completed"}, {"item": "demo-c", "status": "completed"},
                  {"item": "demo-z", "status": "completed"}]
        r = labs.coverage_check(self.expected, ledger)
        self.assertFalse(r["pass"]); self.assertEqual(r["duplicates"], ["demo-a"]); self.assertEqual(r["unexpected"], ["demo-z"])

    def test_skip_without_reason_is_rejected(self):
        ledger = [{"item": i, "status": "completed"} for i in self.expected[:2]] + [{"item": "demo-c", "status": "skipped"}]
        self.assertFalse(labs.coverage_check(self.expected, ledger)["pass"])


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.work = self.tmp / "work"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_creates_then_already_created(self):
        r1 = labs.run_report(self.work); self.assertEqual(r1["status"], "created")
        text = Path(r1["path"]).read_text()
        self.assertIn("Completed this period: 1", text); self.assertIn("T-1", text)
        self.assertIn("Currently open: 2", text); self.assertIn("T-2", text); self.assertIn("T-3", text)
        r2 = labs.run_report(self.work); self.assertEqual(r2["status"], "already_created")

    def test_edited_draft_stops(self):
        r1 = labs.run_report(self.work)
        p = Path(r1["path"]); p.write_text(p.read_text() + "\nedited by a person\n")
        self.assertEqual(labs.run_report(self.work)["status"], "stopped_checksum_mismatch")

    def test_incomplete_input_stops(self):
        m = json.loads((DATA / "manifest.json").read_text()); m["export_complete"] = False
        mp = self.tmp / "manifest.json"; mp.write_text(json.dumps(m))
        self.assertEqual(labs.run_report(self.work, manifest_path=mp)["status"], "stopped_incomplete_input")
        self.assertFalse((self.work / "report-2026-10-26.md").exists())

    def test_concurrent_runs_create_once(self):
        results = []
        ts = [threading.Thread(target=lambda: results.append(labs.run_report(self.work)["status"])) for _ in range(4)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual(results.count("created"), 1)
        self.assertEqual(set(results) - {"created"}, {"already_created"})

    def test_interruption_after_draft_stops_on_rerun(self):
        r1 = labs.run_report(self.work, interrupt_after_draft=True)
        self.assertEqual(r1["status"], "interrupted_for_test")
        self.assertEqual(labs.run_report(self.work)["status"], "stopped_interrupted")


class SearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((DATA / "catalog.json").read_text())
        cls.users = {k: v for k, v in json.loads((DATA / "demo_users.json").read_text()).items() if k != "note"}
        cls.on = dt.date(2026, 11, 1)

    def q(self, query, user="reader", on=None, users=None):
        return labs.search(query, user, on or self.on, self.catalog, users or self.users)

    def test_current_leave_is_v2_not_draft(self):
        r = self.q("annual leave allowance")
        self.assertEqual(r["status"], "answer"); self.assertEqual(r["sources"][0]["id"], "leave-v2"); self.assertIn("22 days", r["sources"][0]["quote"])

    def test_leave_on_past_date_is_v1(self):
        r = self.q("annual leave allowance", on=dt.date(2026, 9, 1))
        self.assertEqual(r["sources"][0]["id"], "leave-v1"); self.assertIn("20 days", r["sources"][0]["quote"])

    def test_owner_of_current_leave_policy(self):
        self.assertEqual(self.q("annual leave allowance")["sources"][0]["owner"], "People team")

    def test_expense_approval(self):
        r = self.q("expense above AUD 200 approval"); self.assertEqual(r["sources"][0]["id"], "expense-v1"); self.assertIn("manager approval", r["sources"][0]["quote"].lower())

    def test_parking_has_no_answer(self):
        self.assertEqual(self.q("parking allowance")["status"], "no_supported_answer")

    def test_reader_cannot_see_salary(self):
        r = self.q("salary"); self.assertEqual(r["status"], "no_supported_answer"); self.assertNotIn("salary", json.dumps(r).lower().replace('"salary"', ""))

    def test_hr_can_see_salary(self):
        self.assertEqual(self.q("salary", user="hr")["sources"][0]["id"], "salary-record")

    def test_travel_conflict_is_surfaced(self):
        r = self.q("travel approval"); self.assertEqual(r["status"], "conflict"); self.assertEqual({s["id"] for s in r["sources"]}, {"travel-a", "travel-b"})

    def test_draft_is_never_authority(self):
        self.assertNotIn("25 days", json.dumps(self.q("annual leave allowance 25 days")))

    def test_revoked_group_returns_nothing(self):
        self.assertEqual(self.q("annual leave allowance", users={"reader": []})["status"], "no_supported_answer")


class RoiTest(unittest.TestCase):
    def test_two_rows_including_a_negative(self):
        rows = {r["task"]: r for r in labs.roi_rows()}
        q = lambda x: x.quantize(Decimal("0.01"))
        self.assertEqual(q(rows["weekly report"]["hours_saved"]), Decimal("1.67"))
        self.assertEqual(q(rows["weekly report"]["net_value"]), Decimal("73.33"))
        self.assertEqual(q(rows["familiar bug fix"]["hours_saved"]), Decimal("-1.00"))
        self.assertEqual(q(rows["familiar bug fix"]["net_value"]), Decimal("-55.00"))


if __name__ == "__main__":
    unittest.main()
