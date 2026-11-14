"""Im Spiel: Tricks bei offenem Mana. Aus dem Spielzustand die ungetappten Laender des Gegners lesen und alle
Instants und Karten mit Flash des Sets zeigen, die er damit wirken koennte; dazu, was im naechsten Zug des Gegners
(alle Laender ungetappt und ein weiteres Land) zusaetzlich moeglich wird. Gegnerfarben aus gezeigten Zaubern: sind
mindestens zwei Farben bekannt, kommen Tricks nur in diesen Farben (und den Farben seiner Standardlaender) in Frage."""
import json
import pathlib
import tempfile
import unittest

from components import gamestate as gs
from components import livedraft as ld
from components import overlay
from components import tricks
from tests.test_gamestate import ALL, NAMES, START, feed, gre, obj, state, zone


def sc(name, type_line, cost, colors, text="", keywords=()):
    mv = sum(int(p) if p.isdigit() else 1 for p in cost.strip("{}").split("}{")) if cost else 0
    return {"name": name, "type_line": type_line, "mana_cost": cost, "cmc": mv, "colors": list(colors),
            "oracle_text": text, "keywords": list(keywords)}


SET = [sc("Trick W", "Instant", "{W}", "W", "Target creature gets +2/+2 until end of turn."),
       sc("Trick 1W", "Instant", "{1}{W}", "W", "Prevent all combat damage that would be dealt this turn."),
       sc("Flash Bear", "Creature — Bear", "{2}{G}", "G", "Flash", ["Flash"]),
       sc("Sorcery R", "Sorcery", "{R}", "R", "Draw a card."),
       sc("Bolt R", "Instant", "{R}", "R", "Bolt R deals 3 damage to target creature."),
       sc("Quick U", "Instant", "{U}", "U", "Draw a card."),
       sc("Big U", "Instant", "{3}{U}{U}", "U", "Counter target spell."),
       sc("Flash Relic", "Artifact", "{2}", "", "Flash", ["Flash"]),
       sc("Trick 3W", "Instant", "{3}{W}", "W", "Destroy target attacking creature."),
       sc("Test Grove", "Land", "", "", "{T}: Add {G}.")]

# Gegner (Platz 1): Plains ungetappt, Mountain getappt, Forest ungetappt; eigene Laender zaehlen nicht
LANDS = {501: ("SubType_Plains", False), 502: ("SubType_Mountain", True), 503: ("SubType_Forest", False)}


def land(iid, grp, subtype, tapped, owner=1, zid=28):
    o = obj(iid, grp, zid, owner=owner)
    o.update({"controllerSeatId": owner, "cardTypes": ["CardType_Land"], "superTypes": ["SuperType_Basic"],
              "subtypes": [subtype]})
    if tapped:
        o["isTapped"] = True
    return o


def spell(iid, grp, colors, zid=40, owner=1):
    colors = [colors] if isinstance(colors, str) else colors
    o = obj(iid, grp, zid, owner=owner)
    o.update({"cardTypes": ["CardType_Creature"], "color": [f"CardColor_{c}" for c in colors]})
    return o


BOARD = gre(state(zones=[zone(28, "ZoneType_Battlefield", None, [61, 62, 63, 64])],
                  objects=[land(61, 501, "SubType_Plains", False), land(62, 502, "SubType_Mountain", True),
                           land(63, 503, "SubType_Forest", False),
                           land(64, 301, "SubType_Plains", False, owner=2)]))


def view(game, cards=None):
    return tricks.tricks_view(game, lambda grp: None, tricks.trick_cards(cards or SET))


class TrickCardTests(unittest.TestCase):
    def test_only_instants_and_flash(self):
        names = [c["name"] for c in tricks.trick_cards(SET)]
        self.assertEqual(sorted(names), ["Big U", "Bolt R", "Flash Bear", "Flash Relic", "Quick U", "Trick 1W",
                                         "Trick 3W", "Trick W"])
        bolt = next(c for c in tricks.trick_cards(SET) if c["name"] == "Bolt R")
        self.assertGreater(bolt["removal"], 0)
        self.assertEqual((bolt["cost"], bolt["mv"], bolt["colors"]), ("{R}", 1, ["R"]))

    def test_double_faced_front(self):
        mdfc = {"name": "Front // Back", "type_line": "Instant // Land", "cmc": 2, "colors": ["W"],
                "card_faces": [{"name": "Front", "type_line": "Instant", "mana_cost": "{1}{W}", "colors": ["W"],
                                "oracle_text": "Tap target creature."},
                               {"name": "Back", "type_line": "Land", "mana_cost": "", "oracle_text": ""}]}
        self.assertEqual([(c["name"], c["cost"]) for c in tricks.trick_cards([mdfc])], [("Front // Back", "{1}{W}")])


class OpponentStateTests(unittest.TestCase):
    def test_opponent_lands_with_tapped_state(self):
        g = feed(gs.GameState(), *START, BOARD)
        lands = sorted((x["grp"], x["tapped"], tuple(x["subtypes"])) for x in g.opponent_lands())
        self.assertEqual(lands, [(501, False, ("SubType_Plains",)), (502, True, ("SubType_Mountain",)),
                                 (503, False, ("SubType_Forest",))])
        untap = gre(state(objects=[land(62, 502, "SubType_Mountain", False)]))  # Diff: Objekt ohne isTapped
        feed(g, untap)
        self.assertFalse(next(x for x in g.opponent_lands() if x["grp"] == 502)["tapped"])

    def test_spell_colors_from_public_zones(self):
        cast = gre(state(zones=[zone(40, "ZoneType_Graveyard", 1, [70]), zone(28, "ZoneType_Battlefield", None,
                                                                              [61, 62, 63, 64, 71])],
                         objects=[spell(70, 900, "White"), spell(71, 901, "Green", zid=28)]))
        g = feed(gs.GameState(), *START, BOARD, cast)
        self.assertEqual(g.opponent_spell_colors(), {"W", "G"})
        hidden = gre(state(zones=[zone(31, "ZoneType_Hand", 1, [50, 72])], objects=[spell(72, 902, "Blue", zid=31)]))
        feed(g, hidden)  # Handkarten des Gegners zaehlen nicht
        self.assertEqual(g.opponent_spell_colors(), {"W", "G"})


class TricksViewTests(unittest.TestCase):
    def test_open_mana_now_and_next_turn(self):
        v = view(feed(gs.GameState(), *START, BOARD))
        self.assertEqual(v["open"], 2)
        self.assertEqual(v["colors"], {"W": 1, "G": 1})
        self.assertEqual(v["lands"], 3)
        self.assertEqual([c["name"] for c in v["now"]], ["Trick W", "Flash Relic", "Trick 1W"])  # Manawert, Name
        # naechster Zug: Plains, Mountain, Forest und ein weiteres Land in einer seiner Farben
        self.assertEqual([c["name"] for c in v["next"]], ["Bolt R", "Flash Bear", "Trick 3W"])  # 4 Mana erst mit +1
        self.assertNotIn("Sorcery R", [c["name"] for c in v["now"] + v["next"]])

    def test_known_spell_colors_restrict_tri_lands(self):
        tri = {"name": "Test Tri", "type_line": "Land", "oracle_text": "{T}: Add {W}, {U}, or {G}.",
               "produced_mana": ["W", "U", "G"]}
        cards = {504: ld.card_summary(tri, "Test Tri")}
        board = gre(state(zones=[zone(28, "ZoneType_Battlefield", None, [61, 65]), zone(40, "ZoneType_Graveyard", 1,
                                                                                         [70, 71])],
                          objects=[land(61, 501, "SubType_Plains", False), dict(obj(65, 504, 28, owner=1),
                                   controllerSeatId=1, cardTypes=["CardType_Land"]),
                                   spell(70, 900, "White"), spell(71, 901, "Green")]))
        g = feed(gs.GameState(), *START, board)
        v = tricks.tricks_view(g, cards.get, tricks.trick_cards(SET))
        self.assertEqual(v["open"], 2)
        self.assertEqual(v["spell_colors"], ["W", "G"])
        self.assertNotIn("Quick U", [c["name"] for c in v["now"]])  # Blau nur ueber das Tri-Land, nie gezeigt
        self.assertIn("Trick 1W", [c["name"] for c in v["now"]])
        one = gre(state(zones=[zone(40, "ZoneType_Graveyard", 1, [70])], objects=[spell(70, 900, "White")]))
        g2 = feed(gs.GameState(), *START, board, one)  # nur eine Farbe bekannt: keine Einschraenkung
        self.assertIn("Quick U", [c["name"] for c in tricks.tricks_view(g2, cards.get,
                                                                        tricks.trick_cards(SET))["now"]])

    def test_no_open_mana(self):
        v = view(feed(gs.GameState(), *START))
        self.assertEqual((v["open"], v["now"]), (0, []))


class OverlayTests(unittest.TestCase):
    def game(self):
        g = gs.game_view(feed(gs.GameState(), *START), {})
        g["tricks"] = view(feed(gs.GameState(), *START, BOARD))
        return g

    def test_rows_show_tricks(self):
        # Nutzer 13.11.2026: Tricks stehen im eigenen Fenster (Trick-Warner), nicht mehr bei der Bibliothek
        rows = overlay.trick_window_rows({"status": "waiting", "game": self.game()})
        text = "\n".join(r[0] for r in rows)
        self.assertIn("Gegner offen 2", text)
        self.assertIn("Trick 1W", text)
        self.assertNotIn("Nächster Gegnerzug", text)  # Nutzer 13.11.2026: nur Tricks mit jetzt offenem Mana
        self.assertNotIn("Bolt R", text)
        self.assertTrue(all(ord(ch) <= 0xFFFF for r in rows for ch in r[0]))
        main = "\n".join(r[0] for r in overlay.rows_for({"status": "waiting", "game": self.game()}))
        self.assertIn("Chance nächste Karte", main)
        self.assertNotIn("Gegner offen", main)
        self.assertNotIn("Trick 1W", main)

    def test_mini_shows_trick_count(self):
        text = " ".join(r[0] for r in overlay.mini_rows({"game": self.game()}))
        self.assertIn("Tricks 3", text)


class LiveTests(unittest.TestCase):
    def test_snapshot_has_tricks_from_the_set(self):
        with tempfile.TemporaryDirectory() as d:
            log = pathlib.Path(d) / "Player.log"
            log.write_text("\n".join(START + [BOARD]) + "\n", encoding="utf-8")
            asked = []
            live = ld.LiveDraft(log, pathlib.Path(d) / "pool.txt", names=NAMES, fetch=lambda n, refresh=False: ALL,
                                fetch_set=lambda code: asked.append(code) or SET)
            live.step()
            t = live.snapshot({"Bolt R": "mustplay"}, {}, None)["game"]["tricks"]
            self.assertEqual(asked, ["tst"])
            self.assertEqual(t["open"], 2)
            # Nutzer 14.11.2026: ohne Kreatur des Gegners keine Pump-Tricks mehr (Trick W), Trick 1W bleibt
            self.assertNotIn("Trick W", [c["name"] for c in t["now"]])
            self.assertIn("Trick 1W", [c["name"] for c in t["now"]])
            self.assertEqual(next(c for c in t["next"] if c["name"] == "Bolt R")["rating"], "mustplay")
            live.step()
            live.snapshot({}, {}, None)
            self.assertEqual(asked, ["tst"])  # Set nur einmal laden


class PageTests(unittest.TestCase):
    def test_page_and_help(self):
        from components.drafthelper import render_page
        from components.howitworks import render_help_page
        self.assertIn("Tricks bei offenem Mana", render_page())
        self.assertIn("Tricks bei offenem Mana", render_help_page())
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Tricks bei offenem Mana", readme)


if __name__ == "__main__":
    unittest.main()
