import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

import mtg_sim
from components import drafthelper as dh
from components.report import render_great
from tests.fixtures import CARDS, args_for
from tests.test_drafthelper import load


def deck_data(deck, parts, cats, role):
    entry = {"name": "Vorschlag", "deck": dict(deck), "parts": parts, "cats": cats, "role": role}
    return mtg_sim.build_deck(entry, CARDS, args_for(["deck.txt"]))


class ProposeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cards, basics, sig = load()
        cls.calls = []

        def fake_simulate(entries, args, progress):
            cls.calls.append((entries, args))
            return "<html>Bericht</html>"

        cls.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                   "simulate": fake_simulate, "save": lambda html, args: None, "job": dh.Job(),
                   "options": [1000], "file": "pool.txt"}
        cls._stderr = mock.patch("sys.stderr", io.StringIO())
        cls._stderr.start()
        cls.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(cls.app))
        cls.app["server"] = cls.server
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._stderr.stop()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def body(self, **extra):
        pool = self.app["pool"]
        body = {"marks": [["off"] * c["qty"] for c in pool], "basics": {},
                "cats": {"Test Big": "mustplay", "Test Hasty": "mustplay", "Test Defender": "filler",
                         "Test Bear": "filler", "Test Gold": "filler", "Test Spell": "neverplay"},
                "colors": ["W"], "target": 10, "sort": "mv"}
        body.update(extra)
        return body

    def test_pool_cards_carry_the_mana_cost(self):
        big = next(c for c in self.app["pool"] if c["name"] == "Test Big")
        self.assertEqual(big["cost"], "{3}{W}{W}")

    def test_propose_returns_deck_and_summary(self):
        status, answer = self.post("/api/propose", self.body())
        self.assertEqual(status, 200)
        deck = answer["deck"]
        self.assertEqual(sum(deck.values()), 10)
        self.assertEqual(deck["Test Big"], 1)
        self.assertNotIn("Test Hasty", deck)       # rot, nicht gewaehlt
        self.assertNotIn("Test Gold", deck)        # WB braucht auch Schwarz
        self.assertNotIn("Test Spell", deck)       # NeverPlay
        self.assertIn("lands", answer["summary"])
        self.assertEqual(self.app["job"].status()["state"], "idle")

    def test_basic_lands_are_part_of_the_returned_deck(self):
        deck = self.post("/api/propose", self.body())[1]["deck"]
        self.assertGreater(deck.get("Plains", 0), 0)

    def test_invalid_color_is_rejected(self):
        self.assertEqual(self.post("/api/propose", self.body(colors=["X"]))[0], 400)

    def test_target_out_of_range_is_rejected(self):
        self.assertEqual(self.post("/api/propose", self.body(target=5))[0], 400)

    def test_unknown_sort_is_rejected(self):
        self.assertEqual(self.post("/api/propose", self.body(sort="zufall"))[0], 400)

    def test_simulation_with_proposal_adds_a_third_deck(self):
        body = self.body(sims=500, proposal={"colors": ["W"], "target": 10})
        body["marks"] = [["core"] * c["qty"] for c in self.app["pool"]]
        body["marks"][[c["name"] for c in self.app["pool"]].index("Test Spell")] = ["splash"]
        status, answer = self.post("/api/simulate", body)
        self.assertEqual((status, answer), (200, {"ok": True}))
        for _ in range(200):
            if self.app["job"].status()["state"] != "running":
                break
        entries, _args = self.calls[-1]
        self.assertEqual([e["name"] for e in entries], ["Splash", "NoSplash", "Vorschlag"])
        proposal = entries[2]
        self.assertEqual(proposal["role"], "proposal")
        self.assertEqual(proposal["parts"], [("Vorschlag", proposal["deck"])])
        self.assertEqual(sum(proposal["deck"].values()), 10)
        self.assertEqual(proposal["cats"], entries[0]["cats"])

    def test_simulation_without_proposal_has_two_decks(self):
        body = self.body(sims=500)
        body["marks"] = [["core"] * c["qty"] for c in self.app["pool"]]
        body["marks"][[c["name"] for c in self.app["pool"]].index("Test Spell")] = ["splash"]
        self.assertEqual(self.post("/api/simulate", body)[0], 200)
        for _ in range(200):
            if self.app["job"].status()["state"] != "running":
                break
        self.assertEqual(len(self.calls[-1][0]), 2)

    def test_proposal_that_is_far_too_small_is_rejected(self):
        body = self.body(sims=500, proposal={"colors": [], "target": 40}, cats={})
        body["marks"] = [["core"] * c["qty"] for c in self.app["pool"]]
        status, answer = self.post("/api/simulate", body)
        self.assertEqual(status, 400)
        self.assertIn("Deckvorschlag", answer["error"])


class ReportForProposalTests(unittest.TestCase):
    def test_missing_cards_are_not_reported_for_the_proposal_deck(self):
        cats = {"Test Defender": "mustplay", "Test Big": "mustplay"}
        deck = {"Plains": 17, "Test Big": 3, "Test Bear": 20}
        html = render_great(deck_data(deck, [("Vorschlag", deck)], cats, "proposal"))
        self.assertIn("Test Big", html)
        self.assertNotIn("Fehlt in diesem Deck", html)

    def test_other_roles_still_report_missing_mustplay_cards(self):
        cats = {"Test Defender": "mustplay"}
        deck = {"Plains": 17, "Test Bear": 20}
        html = render_great(deck_data(deck, [("Core", deck)], cats, "splash"))
        self.assertIn("Fehlt in diesem Deck", html)


if __name__ == "__main__":
    unittest.main()
