import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
TMP = tempfile.mkdtemp()
os.environ.update(DATA_DIR=TMP, DISABLE_SCHEDULER="1", OPENAI_API_KEY="", ANTHROPIC_API_KEY="")

from make_sample_pdf import build  # noqa: E402

from app import pdf_parser, planner, scraper  # noqa: E402
from app.main import app  # noqa: E402

PDF = os.path.join(TMP, "sample.pdf")
build(PDF)


class ParserTest(unittest.TestCase):
    def test_calendar_pdf(self):
        r = pdf_parser.parse(open(PDF, "rb").read(), "VILLA OCTUBRE 2026 - BASAL.pdf")
        self.assertEqual((r["year"], r["month"]), (2026, 10))
        d = r["days"]["2026-10-01"]
        self.assertEqual(d["dishes"][0], "Lentejas estofadas con verduras")
        self.assertEqual(d["dinner_hint"], "Pescado y verdura")
        self.assertEqual(r["days"]["2026-10-12"]["note"], "FESTIVO")
        self.assertEqual(sum(1 for v in r["days"].values() if v["dishes"]), 21)


class ScraperTest(unittest.TestCase):
    def test_finds_drive_pdf(self):
        html = """<div>Menús de comidas octubre 2026</div>
        <div data-embed-doc-id="1AbCdEfGhIjKlMnOpQrStUvWxYz012345">VILLA OCTUBRE 2026 - BASAL.pdf</div>
        <iframe src="https://drive.google.com/file/d/1ZZZzzzZZZzzzZZZzzzZZZzzzZZZzzzZ/preview"></iframe> ALERGIAS septiembre.pdf"""
        best = scraper.find_best(2026, 10, html)
        self.assertEqual(best.ident, "1AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        self.assertGreaterEqual(best.score, 4)


class PlannerTest(unittest.TestCase):
    def test_hint_detection(self):
        self.assertFalse(planner.hint_is_dish("Pescado y verdura"))
        self.assertFalse(planner.hint_is_dish("Carne blanca y puré de verduras"))
        self.assertTrue(planner.hint_is_dish("Tortilla francesa con calabacín"))

    def test_sum_qty(self):
        self.assertEqual(planner.sum_qty(["500 g", "1 kg", "2 latas", "1 lata"]), "1,5 kg + 3 latas")


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = app.test_client()
        r = cls.c.post("/api/upload", data={"pdf": (open(PDF, "rb"), "VILLA OCTUBRE 2026 - BASAL.pdf")})
        assert r.status_code == 200, r.json

    def test_week_and_shopping(self):
        w = self.c.get("/api/week?date=2026-10-05").json
        self.assertEqual(len(w["days"]), 7)
        for d in w["days"][:5]:
            self.assertGreaterEqual(len(d["cena"]["options"]), 3)
        for d in w["days"][5:]:
            self.assertIsNotNone(d["comida"]["choice"])
            self.assertIsNotNone(d["cena"]["choice"])
        shop = self.c.get("/api/shopping?date=2026-10-05").json
        self.assertTrue(shop["items"])

    def test_edit_and_custom(self):
        r = self.c.post("/api/plan/2026-10-06/cena/choose", json={"name": "Sopa casera", "ingredients": [{"name": "Fideos", "qty": "100 g"}]})
        self.assertEqual(r.status_code, 200)
        day = [d for d in r.json["days"] if d["date"] == "2026-10-06"][0]
        self.assertEqual(day["cena"]["choice"]["name"], "Sopa casera")
        r = self.c.put("/api/school/2026-10-07", json={"dishes": ["Paella"], "dinner_hint": "Huevo y verdura", "note": ""})
        day = [d for d in r.json["days"] if d["date"] == "2026-10-07"][0]
        self.assertEqual(day["school"]["dishes"], ["Paella"])
        self.assertTrue(any("huevo" in o["groups"] for o in day["cena"]["options"]))

    def test_holiday_has_home_lunch(self):
        w = self.c.get("/api/week?date=2026-10-12").json
        self.assertIsNotNone(w["days"][0]["comida"])


if __name__ == "__main__":
    unittest.main()
