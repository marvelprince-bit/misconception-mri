"""The web interface's backend (mri/scan.py) runs the real engine and reports it faithfully."""
import unittest

from mri import scan


class ScanBackend(unittest.TestCase):
    def test_correct_answer_trap_case(self):
        r = scan.scan("int_always_positive")
        self.assertTrue(r["trap"]["possible"])                      # 5/5 right on the worksheet
        self.assertTrue(all(w["ok"] for w in r["worksheet"]))
        self.assertEqual(r["result"]["state"], "diagnosed")
        self.assertEqual(r["answer_key"]["verdict"], "right")
        self.assertTrue(any(s["kind"] == "prediction" and s["matched"] for s in r["steps"]))

    def test_replayed_claude_case_matches_live_run(self):
        r = scan.scan("sub_parts_separately", hide=True, writer="replay")
        self.assertEqual(r["answer_key"]["verdict"], "right")
        self.assertTrue(r["ai"])

    def test_cheating_ai_is_refused(self):
        r = scan.scan("int_sign_of_first", hide=True, writer="cheat")
        self.assertNotEqual(r["result"]["state"], "diagnosed")
        self.assertEqual(r["answer_key"]["verdict"], "declined")

    def test_be_the_student(self):
        s = scan.start("fractions")
        sid = s["sid"]
        for _ in range(30):
            if "question" not in s:
                break
            a, b = s["question"]["q"].split(" + ")
            (n1, d1), (n2, d2) = (map(int, a.split("/"))), (map(int, b.split("/")))
            s = scan.answer(sid, f"{n1 + n2}/{d1 + d2}")
        self.assertEqual(s["result"]["state"], "diagnosed")
        self.assertIn("adds the bottoms", s["result"]["rule"])

    def test_bad_answer_is_explained(self):
        s = scan.start("fractions")
        self.assertIn("error", scan.answer(s["sid"], "three quarters"))
