# MTG Opening Hand Simulator

*Deutsche Version: [README.md](README.md)*

Reads a deck list, fetches the card data from [Scryfall](https://scryfall.com), and simulates many games
(On the Play and On the Draw). The result is an HTML report that opens in the browser.

There are three parts:

- **Goldfish simulation and report:** The deck plays alone (no opponent) and is evaluated for mana, tempo, damage,
  mulligans, and much more (see “What the report shows”).
- **Battle model and battle report:** The deck plays against opponent decks (folder `enemydecks`) with life, attacks,
  blocks, removal, instants, and many card mechanics. The result is the win rate with logs of individual
  games (see “Battles against opponent decks”).
- **Draft Helper:** A card page for the draft pool where variants are assembled, simulated, and tested against
  opponent decks (see “Draft Helper”).

## Requirements

- Python 3.8 or newer, no additional packages
- Internet connection (card data from Scryfall)
- The files must be laid out like this: `mtg_sim.py` in the main folder and next to it the folder `components/` with all
  modules (`scryfall.py`, `cards.py`, `mana.py`, `simulation.py`, `report.py` …). The cache `scryfall_cache.json` is
  created automatically next to `mtg_sim.py`.

## Tests

```
python -m unittest
```

in the project folder. No additional packages and no network are needed (the test cards are in
`tests/fixtures.py`, `tests/fixtures_walkers.py`, and in the test files themselves); a run takes about half a
minute. The tests cover the parser, card model, mana, mulligan, damage and summoning-sickness rules of the
simulation (including a reference run with a fixed seed), the battle model (`tests/test_battle*.py`, one file per
development stage or card package), the variant building and server of the Draft Helper, as well as the report and battle report. The
browser interface (sorting, search, export) is not automatically tested.

**Working rule:** New features get tests first, then the code. New tests are cross-checked by deliberately
breaking the code (the test must then fail). Existing tests are not changed to make them pass;
if they need to be adapted because of deliberately changed behavior, that happens only after
explicit approval. Rules questions are settled with the rulebook `MagicCompRules.txt` (Comprehensive Rules) in the
project folder; deviations from it are noted in the code with the rule number or in the rules of the battle report.

## Code structure

| File | Purpose |
|---|---|
| `mtg_sim.py` | Entry point: load decks, simulate, write report |
| `components/cli.py` | All command-line parameters |
| `components/deckfile.py` | Read deck files and file specifications (`file=label`) |
| `components/scryfall.py` | Fetch card data from Scryfall and cache it |
| `components/mana.py` | Costs, hybrid/Phyrexian, payability by lands |
| `components/cards.py` | Card model `Card` and all parsers for the card text (lands, landcycling, Empower Jace, draw, surveil, prepared, mana, combat keywords, abilities, triggers, tokens, modal cards, cost reduction …) |
| `components/conjure.py` | Alchemy: named cards to conjure with their Scryfall texts |
| `components/removal.py` | Removal detection and removal score, flash/deathtouch, discard |
| `components/graveyard.py` | Graveyard score (second use, recursion, resource) |
| `components/cardkinds.py` | Card types and card flow for sidebar and report |
| `components/synergy.py` | Synergy value: givers/takers per card from the card fields, deck value (report) and synergy bonus in the live draft |
| `components/coverage.py` | Model coverage: detects from the card text which effects are not yet simulated |
| `components/jace.py` | Jace state in the simulation, effect filter, deck analysis |
| `components/mulligan.py` | Mulligan rules and opening hand |
| `components/simulation.py` | Goldfish: game flow, spell/land selection, cost reduction, landcycling, draw, surveil, prepared, ramp, metrics |
| `components/battle.py` | Battle model: two players, attack, block, damage, removal, instants, abilities, triggers |
| `components/battle_report.py` | Battle report (win rates, metrics, game list with logs, rules) |
| `components/battle_server.py` | Shared battle interface for the Draft Helper and the report server |
| `components/report_server.py` | Local server for the report (`--bericht-server`, “Simulate battle” in the report) |
| `components/landadvice.py` | Land recommendation and “Colors and sources” |
| `components/mana.py` | Costs, hybrid/Phyrexian, payability, color checks (`pip_checks`) |
| `components/suggest.py` | Deck suggestion and assignment by category in the Draft Helper |
| `components/archetypes.py` | Archetypes per set (color pairs with deckbuilding hints) for the Draft Helper and report |
| `components/ratings.py` | Card rating of the Draft Helper (`kartenbewertung.json`, per card name) |
| `components/cardarchetypes.py` | Archetype assignment per card (`kartenarchetypen.json`), archetype detection and ranking of the pack |
| `components/arenalog.py` | MTG Arena: packs and picks from `Player.log`, card names from Arena's card database |
| `components/livedraft.py` | Live draft: follow the log, picks into the pool file, rate the pack |
| `components/overlay.py` | Overlay of the live draft (tkinter, always on top) |
| `components/gamestate.py` | In game: library from the Arena log, draw odds, remaining removal |
| `components/tricks.py` | In game: instants and flash cards the opponent could cast with open mana |
| `components/signals.py` | In the draft: open colors (wheel, late and taken strong cards), detect Pick Two |
| `components/draftstats.py` | Draft statistics (`draftstatistik.json`): collect decks and matches, numbers per card |
| `components/setreport.py` | Set report as an HTML page (`--setauswertung`) |
| `components/symbols.py` | Original mana symbols from Scryfall (cache `scryfall_symbols.json`) |
| `components/stats.py` | Traffic-light thresholds, timing metrics, significance calculation |
| `components/html_base.py` | Shared design (CSS in the style of the Draft Helper), page layout, tables, SVG charts |
| `components/report_sections.py` | Report sections game logic, deck comparison, Jace |
| `components/report_cards.py` | Card tables in the report |
| `components/howitworks.py` | Explanation page “How it works” |
| `components/report.py` | Assemble the report |
| `components/drafthelper.py` | Draft Helper page and server |
| `components/i18n.py` | Language (German/English): `t()` for texts, `tr_block()` for fixed templates; English texts per module in `components/i18n_en/` |
## Draft Helper (`--drafthelper`)

```
python mtg_sim.py --drafthelper
```

Reads the card pool from `_draftedcardpool.txt` (sections `Deck` and `Sideboard`, lines as in the deck files,
with set code and number) and opens a page in the browser with all cards as images (data and images from Scryfall).
To use a different file: `python mtg_sim.py --drafthelper mypool.txt`.
`_draftedcardpool.txt` is not in Git (it is listed in `.gitignore`): everyone creates their own pool, e.g. with the
deck export from MTG Arena, and `git pull` never overwrites it. If the file is missing, the Draft Helper aborts immediately with
a message describing what the file must look like.

- Each copy of a card (except basic lands) is marked individually as **Core**, **Splash**, **NoSplash** or **Off**. Default:
  Deck = Core, Sideboard = Off.
- **Category per card** (selection below the image, applies to all copies, at most one): **♛ Matchwinner** (the bomb:
  decides a match on its own, always makes the deck, as a splash if necessary), **★ Splashworthy**
  (decides games on its own, should definitely make the deck, even if we do not play the color),
  **MustPlay** (is played if we play this color), **Filler** (fills up if we play the color and do not
  splash) and **NeverPlay** (too bad or too situational). The category is independent of
  Core/Splash/NoSplash/Off and does not affect the simulation. The header bar counts per category and has a
  “Show cards” filter. The categories are stored per card name in `kartenbewertung.json` in the project folder (not in
  Git, each user rates for themselves) and apply to every card pool: if the pool changes, rated cards
  are already classified. It is saved on every click; the file is sorted alphabetically and can be
  edited by hand. With `--bewertung FILE` a different file is used (e.g. one per user). Categories from older
  browser storage are imported once on the first start. Assignment, basic lands, target size and
  colors are still remembered by the browser per pool.
- **Archetypes of the set:** If archetypes are stored in `components/archetypes.py` for the set of the pool (most common set of the non-lands; currently TRK and FRA), the page shows them above the cards with deck-building hints; the archetype of the core colors (the two colors with the most Core cards) is
  highlighted. In the “Deck” section the report shows the archetype of the deck's main colors.
- **Deck proposal (a separate third deck):** Above the cards are the **target size** (default 40, selectable 10 to 200,
  all lands count), the **colors** (W U B R G, preset to the colors of the core) and the button
  **Create deck proposal**. The proposal builds its own deck from the categories and leaves your assignment
  unchanged:
  - MustPlay and Filler only make the deck if all colors of the card are selected (colorless always).
  - Splashworthy always makes the deck; if its color is outside the selected ones, the card is a splash.
  - NeverPlay and cards without a category do not make the deck.
  - Lands: non-basic lands count as lands, basic lands are added up to the rule of thumb (40 cards:
    17, 60 cards: 22; range 15 to 17 and 20 to 24 respectively, linear in between) and distributed by color symbols, up to 3 per
    splash color. If the number of lands is outside the range, a note is shown.
  - Filler: order by the selected sort, then colors already in the deck, then mana value
    ascending.
  With the **simulate too** checkbox, the proposal is compared as a further variant (“Proposal”) alongside Splash
  and NoSplash when simulating, and the deck list export view shows it as a third column.
- **Assign by category:** The former deck proposal: writes the categories into the assignment
  (MustPlay → Core, Matchwinner and Splashworthy → Splash, NeverPlay → Off, Filler first fills Core, then NoSplash up to the
  target size). **↶ Undo** restores the previous state.
- **Overview on the left:** Cards per color (White, Blue, Black, Red, Green, Multicolor, Colorless, Lands) with pool quantity,
  assignment (Core/Splash/NoSplash) and categories. Copies are counted without basic lands.
- **Search and sorting:** The search field above the cards filters by name or (English) type, e.g. “Creature”.
  The sorting (mana value, name, color, assignment, category) only changes the display, not the assignments.
- **Mana curve on the left:** Number of nonland cards per mana value for the Splash and NoSplash variants side by side,
  plus card count and avg mana value per variant.
- **Mana curve by color (left):** A second curve below the mana curve shows the nonland cards of a selectable
  variant (Splash or NoSplash) by mana value and color. Two views: **Multicolor separate** (stacked, each
  card exactly once, multicolor cards form a golden “Multicolor” segment) and **Per color** (a multicolor
  card counts for each of its colors, so the bars add up to more than the card count). An explanation changes with the
  view; below it are the card count, multicolor and colorless cards, and the color combinations that occur
  (“Black/Red 4 · Black/Green 1”).
- **Card types per variant (left):** Below the mana curve, for the Splash and the NoSplash variant, it shows how
  many cards (copies, with basic lands) there are: total cards, creatures, instants, sorceries, artifacts,
  enchantments, planeswalkers, lands (of which non-basic lands) and Empower Jace (cards and the sum of the
  immediate loyalty when cast or entering, without X and without triggers). Artifacts and enchantments count without
  creatures and lands; a card can appear in several rows. Differences between the variants are bold.
  Below that is the **card flow**: cards that draw (Draw, also cycling), search for lands or cards (Search,
  also landcycling), or have Surveil, Scry, Explore or Mill. Mill is split into “self” (e.g.
  “Mill three cards”) and “opponent possible” (“target opponent mills”, “each opponent mills”; “target player mills” and
  “each player mills” count in both rows because they can also hit you). A card counts once in total and once per type. Only
  types that occur in the pool appear. Triggers that only react to drawing or Scry/Surveil (“whenever you draw …”)
  and opponent draws do not count; Empower Jace has its own row.
  “Card types” also lists Flash, Deathtouch, Removal (score with traffic light: green from 4, yellow from 2.5 points per
  40 cards), mana sources and Prepared cards.
- **Colors and sources (left):** per color the required symbols and the sources (lands and mana sources) of the
  variants, with the original mana symbols from Scryfall.
- **Recommend lands:** sets the basic lands per group and assigns suitable non-basic lands. A
  non-basic land fits only if all its colors are in the deck; at least 3 sources per required color, the rest
  by hypergeometric distribution; lands = target size minus spells, limited to 15 to 17.
- **Simulate battle:** After simulating, the variants can be pitted against an opponent deck from the project folder
  (folder `enemydecks`), with a selectable number of battles; the battle report appears on the page (see “[Battles against opponent decks](#battles-against-opponent-decks)”).
- **Export deck list:** The button in the header bar shows both variants in Arena/MTGO import format
  (`Deck` and `Sideboard`, with set and number), to copy or save as `draftgott_splash.txt` or
  `draftgott_nosplash.txt`. Deck = Core + the variant's group + basic lands, Sideboard = all other cards.
- **Report, section “Great in this deck!”:** lists per variant the ★ Splashworthy and MustPlay cards of the
  deck (with area) and points out when a MustPlay card (in the Splash variant also a
  Splashworthy card) is missing from the deck or a NeverPlay card is included.
- **Basic lands** (Plains, Island, Swamp, Mountain, Forest) are not marked as individual cards but set at the top
  as a quantity per group (Core / Splash / NoSplash, with − and +). The starting value is the number in the deck of the
  file as Core. Lands that are not in the pool (e.g. Swamp for a different splash) can be
  added as well.
- **Start by double-click (Windows):** Double-click `draftgott.bat` in the project folder. It first asks for the
  language (**1 = Deutsch**, **2 = English**; all pages, the overlay and the messages in the window then appear in
  that language, passed on as `--lang de` or `--lang en`), then for the mode: **1 = Deck analysis** (simulates `_normaldeck.txt` with 10,000 games, writes `meinbericht.html` and
  shows it via the report server so that “Simulate battle” works in the report) or **2 = Draft Helper**
  (card page with `_draftedcardpool.txt`), **3 = Live draft** or **4 = Set report** (see below). The script finds Python itself (`py` or `python`). In all cases
  leave the black window open and use the “Quit” button on the page to exit, or close the window.
  Further parameters are appended to the chosen call (`draftgott.bat --sims 1000`).
- **Simulate** builds the variants *Core + Splash* and *Core + NoSplash*, simulates both and shows the
  comparison report directly on the page (also as a file, see `--ausgabe`). Then continue with
  “← Back to the cards”.
- The simulation parameters (`--sims`, `--seed`, `--turns` …) come from the command line; the number of games can be
  changed on the page.
- The server runs locally only (127.0.0.1, port 8765; if it is taken, a free port). To quit: “Quit” button or Ctrl+C in the terminal.
- If neither Splash nor NoSplash is marked, only the Core deck is simulated.
- **Archetype assignment per card:** Below each card of a set with archetypes are buttons with the color pairs of the
  archetypes; a click assigns the card (several are possible). Stored per card name in `kartenarchetypen.json`
  (not in Git, `--archetypen FILE`). The archetype box counts the assigned Core cards and highlights the
  detected archetype (rule see “Live draft”); the report shows the same.
- **Rate set cards:** loads all cards of a set from Scryfall (cache `scryfall_set_cache.json`) to set category
  and archetypes before the draft.

### Live draft (`--live`)

Menu item **3** in `draftgott.bat` or `python mtg_sim.py --drafthelper _livedraft.txt --live`. The Draft Helper
reads along with the MTG Arena log (`Player.log`, like 17Lands or Untapped; the game itself is not touched).
In Arena, “Detailed Logs (Plugin Support)” must be enabled under Options → Account.

- **Picks:** go straight into the card pool file (`_livedraft.txt`, not in Git); the page reloads and shows
  the pool. A new draft starts the file from scratch; a running draft is read back at startup. Card names
  come from Arena's card database in the installation folder, otherwise via the `arena_id` from Scryfall.
- **Current pack:** at the top of the page as a ranking. Points = category (★ 4, MustPlay 3, none 1.5, Filler 1) + 3
  if the card is assigned to the archetype (green), otherwise + 1 if its colors fit; NeverPlay always 0.
  Category and archetypes can be set directly on the pack.
- **Archetype:** each pick counts with the weight of its category (★/MustPlay 2, none/Filler 1, NeverPlay 0) for
  every archetype in whose colors it lies, and once more for every archetype it is assigned to. The detected
  archetype is the one with the most points (at least 3, alone in front), otherwise “not yet set”. Set it yourself via the selection.
- **Overlay:** small window, always on top, with archetype and ranking (● assigned, ○ colors
  fit). Play Arena windowed or borderless fullscreen. `--kein-overlay` turns it off, `--overlay URL` opens
  it on its own, `--arena-log FILE` takes a different log.
- **Control window:** at the left screen edge, uses checkboxes to switch the overlay (Draft / Library) and the
  Trick Warner on and off; closing it closes all windows.
- **Card overlay:** while picking, puts rank, rating, points, archetype fit, removal, card flow, synergy and your own
  win rate directly onto the cards in the Arena window (frame purple = top pick, green = fits, grey = other). Once,
  with a full pack, press "Calibrate" in the control window and click five card corners (saved in
  `kartenoverlay.json`, not in Git). The cards follow Arena's order by rarity and collector number, each shows its
  name in small print as a check; clicks go through to Arena.
- **Pick metrics:** creatures, removal (cards and points as in the report) and card flow of the picks, with the
  detected archetype additionally only in its colors. Pack cards show their removal points.
- **Archetypes in the draft:** Table (and briefly in the overlay) per archetype with the assigned picks and
  pack cards. Only your own assignment counts: cards without an assignment belong to no archetype, a card can belong to
  several.
- **Archetype tips:** If an archetype is detected (or chosen) and the set has archetypes with hints
  (`components/archetypes.py`), its tips appear during the draft at the bottom of the page and in the overlay.
- **In game: draw odds:** During a game the page and overlay show your own library (deck at game
  start minus hand, battlefield, graveyard, exile, stack): per group (land, creature, removal, sources per color)
  and per card the chance for the next card and for at least one among the next 3 cards
  (hypergeometric), plus remaining removal (cards and points). Applies to every game (`components/gamestate.py`).
  “Playable”: cards that can be paid for with your own lands on the battlefield (checkmark on the card).
- **In game: tricks with open mana:** At the top of the page's game view and in the Trick Warner (its own window at the left
  below the control window, only in game) all instants and Flash cards of the set that the
  opponent could cast right now with their untapped lands. If they have shown spells in at least two colors, only tricks in those colors (and those of their
  basic lands). Activated abilities do not count (`components/tricks.py`).
- **Open colors:** Signals in the draft (`components/signals.py`): a strong card (MustPlay or higher) that comes back with the
  pack (wheel, +2), lies late in the pack (at least 3 other players, +1) or was taken by others
  (contested, −1). Pick Two is detected by two cards per pick; the wheel by an earlier pack coming back.
- **Minimize overlay:** Button at the top right or double-click: small box with the odds for removal, land
  and creature (in the draft pick, archetype, best card). In game the “Use deck + sideboard” button is hidden.
- **Deck overview after the draft:** After the draft and between games the overlay shows, instead of “Pick 43”,
  archetype and record, cards/lands/spells with avg mana value, mana curve, creatures, removal, card flow, spells per
  color and the bombs (Matchwinner only) of the main deck submitted in Arena (before that: of all picks).
- **Use deck:** After the draft (42 picks or as soon as Arena reports a deck) the button
  “Use deck + sideboard” appears on the page and in the overlay. It becomes clickable once deck building in Arena is
  finished with “Done”, and writes deck (with basic lands) and sideboard into the card pool file: deck cards to
  Core, sideboard to Off. The deck only counts if at least 80% of its cards come from the picks.
- **Draft statistics:** For each draft, picks, submitted deck and match results (per game and match) are collected in
  `draftstatistik.json` (not in Git, `--statistik FILE`), draft and sealed events only. At startup
  `Player-prev.log` is read back as well; anything read twice is not counted twice. On every card, in the overlay and
  in the report: drafted, in deck, win rate of games with the card in the main deck (gray under 20 games). For Pick Two
  and drafts with humans, the log names no event while drafting: the set then comes from the cards, the event
  from the first matching deck. `--statistik-neu` rebuilds the statistics from both log files.

- **Opponent decks from perfect runs:** When a draft that is being read along reaches the highest number of match
  wins of its format (Pick Two 4, Traditional 3, otherwise 7), its deck (with sideboard) is saved once as
  `enemydecks/drafted_<SET>_<N>wins_<colors>_<YYYY-MM-DD>_<hhmm>.txt` (e.g. `4wins` for Pick Two). Colors from the
  nonland cards of the main deck, the strongest first; up to 2 cards as a splash (`redwhitesplashblue`). Existing
  files are never overwritten. The overlay celebrates the addition to the “Hall of Fame” with a trophy and
  confetti.

### Set report (`--setauswertung [SET]`)

Menu item **4** in `draftgott.bat`: writes `setauswertung_<set>.html` from the draft statistics and opens it
(without SET, the set with the most drafts). Sections: overview, archetypes, best and weakest cards (from 10
games), all cards (sortable: drafted, avg pick number in the pack, in deck, games, win rate, matches), rating
versus result per category, list of drafts.
## Quick start

```
python mtg_sim.py deck.txt
```

This writes `mtg_bericht.html` to the current folder and opens the report in the browser. On some systems the command
is `python3`. The terminal shows only short status messages (loading, simulating, save location).

By default, 10,000 games are simulated per mode. That takes a little while but gives stable numbers. For a quick test,
`--sims 1000` is enough, for example.

### Comparing decks

**Origin of the cards:** With `--core`, the deck list in the “Deck” section shows all cards from all files, each line with
its area (e.g. `Core`, `Splash`, `Nosplash`). Quantities are tracked separately per area, and a card can appear in several
areas: `Plains` with 6 in the core and 3 in `_nosplash.txt` appears as two lines (6 × Core, 3 × Nosplash); in the
deck with the Nosplash variant there are 9. The areas are color-coded: core blue, first variant red, second variant yellow
(further ones yellow as well). Areas that do not belong to the deck shown are displayed faded.
The area name is the file name without the leading underscore. Custom name: `_nosplash.txt=NoSplash` (also with `--core`
and `--deckalt`).

With a shared core (e.g. `core.txt` with 32 cards, `whitesplash.txt` and `nosplash.txt` with 8 cards each):

```
python mtg_sim.py whitesplash.txt nosplash.txt --core core.txt --seed 42
```

The first variant is the baseline, and all others are compared against it. Without `--core`, each file contains a
complete deck.

A core deck with several variants for the last few cards (splash, removal package, card-draw engine …): each variant is
its own deck file. The first file is the baseline, and all decks given with `--deckalt` are compared against it:

```
python mtg_sim.py kern_mit_giants.txt --deckalt kern_splash.txt --deckalt kern_removal.txt --seed 42
```

## Deck file format

```
About
Name My Deck

Deck
17 Plains
4 Example Card
4 Grand Entryway // Elegant Rotunda

Sideboard
2 Other Card
```

- Only the `Deck` section is read. `Sideboard`, `Commander`, and `Companion` are ignored.
- Lines have the form `quantity card name`; an `x` after the number is allowed. Set codes in parentheses at the end of
  a line are ignored.
- The `Name ...` line in the `About` section is used as the report title, otherwise the file name.
- Cards that Scryfall cannot find are skipped. They appear as a notice at the top of the report.

## Parameters

All parameters are optional. Only `deckfile` (the deck file) is required.

### Deck comparison

| Parameter | Default | Effect |
|---|---|---|
| `--core FILE` | none | Core deck list (e.g. 32 cards). It is added to **every** deck file given. The files then contain only the variants (e.g. 8 cards each). Name and report title come from the variant. |
| `--deckalt FILE` | none | Additional deck list that is compared with the main deck. May be given multiple times. All decks are simulated with the same settings. Identical deck names are distinguished with “(2)” etc. |

### Simulation scope

| Parameter | Default | Effect |
|---|---|---|
| `--sims N` | `10000` | Number of games **played** per mode (Play and Draw). Games lost to mulligans are added on top and are not counted. |
| `--seed N` | random | Seed of the random number generator. With the same seed and the same deck lists, exactly the same report is produced. Each deck derives its own fixed seed from it. |
| `--turns N` | `3` | Up to which turn the main analysis runs: columns in “Spells per turn”, creatures on the battlefield after turn N, and the mana screw rule (“fewer than N lands on the battlefield”). Traffic-light colors exist only for turns 1 to 3. |
| `--max-runden N` | `15` | Observation period for flood, tempo (empty hand, top card), damage, and fastest lethal. Every game runs at least this long. |
| `--curve-runden N` | `6` | Up to which turn curve utilization is calculated (tables and chart). |

The actual length of a game is the largest of the three values `--max-runden`, `--turns`, and `--curve-runden`.

### Thresholds for metrics

| Parameter | Default | Effect |
|---|---|---|
| `--schaden N` | `20` | Total creature damage whose first turn is measured (“Avg. turn for N damage”, line chart, fastest lethal). |
| `--flood N` | `11` | A game counts as flooded once this many lands have been drawn (opening hand included) by turn `--max-runden`. With fewer turns, the value is harder to reach. |

### Mulligan

| Parameter | Default | Effect |
|---|---|---|
| `--ohne-mulligan` | off (mulligans active) | Turns off mulligans: every 7-card hand is played. The “Mulligan” section in the report is omitted. |
| `--min-handkarten N` | `5` | If the opening hand falls below N cards through mulligans, the game counts as lost and is not played. With `4`, a game can still be played on 4 cards. |

The mulligan rules themselves (no castable card by colors, 6 or more lands, at most 2 lands with fewer than
3 castable cards, exception for landcycling) and the London mulligan are built in. See “Fixed assumptions”.

### Landcycling

These parameters only take effect if the deck contains cards with landcycling (for example “Basic landcycling {2}”).

| Parameter | Default | Effect |
|---|---|---|
| `--ohne-landcycling` | off (landcycling active) | Cards are only cast normally, never cycled. Useful for comparing what the cyclers bring to the deck. The “Landcycling” section is omitted. |
| `--landcycling-runden N` | `3` | Up to which turn a missing land drop is secured via landcycling (mandatory cycling when there is no land in hand). |
| `--landcycling-max-laender N` | `6` | An uncastable card is cycled only while you have (battlefield plus hand) fewer than N lands. |
| `--landcycling-letzte-karte` | off | Also allows landcycling when the card would be the last card in hand. The default is not to cycle. The check of whether cycling is worthwhile still applies. |

### Empower Jace

| Parameter | Default | Effect |
|---|---|---|
| `--ohne-jace` | off (Jace is simulated) | Turns off only the **simulation** of Jace: there is no Jace token, no activations, and no additionally drawn cards. The counting of cards and the classification in the “Jace & planeswalkers” section are kept. Useful for comparing what Jace brings to the deck. |

The “Jace & planeswalkers” section appears only if the deck contains cards with “Empower Jace” or other
planeswalker references. It has no thresholds of its own. The activation value 3 and the limit of one
activation per turn are fixed in the script (see “Fixed assumptions”).

### Game rules

| Parameter | Default | Effect |
|---|---|---|
| `--auras-ohne-kreatur` | off | By default, auras are only cast if a creature is on the battlefield or is cast in the same turn. With this parameter, auras may also be cast without a creature of your own. |

### Battles against opponent decks

| Parameter | Default | Effect |
|---|---|---|
| `--gegner FILE` | none | Simulate a battle against this opponent deck (e.g. `bad_creatures.txt` from the `enemydecks` folder); may be given multiple times. The Goldfish report stays unchanged, and the battle goes into its own report. |
| `--bericht-server` | off | Shows the report through a local server instead of just as a file, so that “Simulate battle” works in the report. The program keeps running until it is closed in the report. |
| `--kampf-ausgabe FILE` | `mtg_kampf.html` | Name of the battle report. |
| `--kaempfe N` | `500` | Battles per deck and mode (On the Play / On the Draw) against each opponent deck. |
| `--kampf-runden N` | `20` | Turn limit in battle; after that the game is a draw. |

### Output

| Parameter | Default | Effect |
|---|---|---|
| `--bewertung FILE` | `kartenbewertung.json` | Draft Helper: file with the category per card name (not in Git). |
| `--archetypen FILE` | `kartenarchetypen.json` | Draft Helper: file with the archetype assignment per card name (not in Git). |
| `--live` | off | Draft Helper in live draft: follow the Arena log, write picks to the pool file, rate the pack, overlay. |
| `--arena-log FILE` | `…/LocalLow/Wizards Of The Coast/MTGA/Player.log` | Live draft: path of the Arena log. |
| `--kein-overlay` | off | Live draft without overlay. |
| `--overlay URL` | | Open only the overlay for a running live draft. |
| `--statistik FILE` | `draftstatistik.json` | Draft statistics of the live draft (not in Git). |
| `--statistik-neu` | | Rebuild the draft statistics from `Player-prev.log` and `Player.log` (old file saved as `draftstatistik.backup.json`). |
| `--setauswertung [SET]` | | Set report as an HTML page `setauswertung_<set>.html` (without SET: the set with the most drafts). |
| `--neu-laden` | off | Card data is stored in `scryfall_cache.json` next to the script, and on later runs only unknown cards are fetched. With `--neu-laden`, everything is fetched fresh from Scryfall. |
| `--ausgabe FILE` (also `--html FILE`) | `mtg_bericht.html` | Name and location of the HTML report. An existing file is overwritten. |
| `--nicht-oeffnen` | off (report is opened) | The report is only saved; the browser does not open. |
| `--lang de\|en` | `de` | Language of the report, battle report, Draft Helper, set report, overlay, and console messages. |
| `-h`, `--help` | | Shows the short help. |

## Examples

```
# Quick test with fewer games
python mtg_sim.py deck.txt --sims 1000

# Compare three variants for the last 5 cards, reproducible
python mtg_sim.py kern_a.txt --deckalt kern_b.txt --deckalt kern_c.txt --seed 42

# How much do the land cyclers bring? Compare two reports
python mtg_sim.py deck.txt --sims 5000 --ausgabe mit_cycling.html
python mtg_sim.py deck.txt --sims 5000 --ohne-landcycling --ausgabe ohne_cycling.html

# How harsh are the mulligan rules? Compare with and without
python mtg_sim.py deck.txt --sims 5000 --ohne-mulligan --ausgabe ohne_mulligan.html

# Faster lethal test: 15 instead of 20 damage, flood already at 10 lands
python mtg_sim.py deck.txt --schaden 15 --flood 10

# Early game in more detail: analysis up to turn 4, curve up to turn 8
python mtg_sim.py deck.txt --turns 4 --curve-runden 8

# Battle against two opponent decks with 1000 battles per mode each
python mtg_sim.py deck.txt --gegner bad_creatures.txt --gegner hard_whiteblue_creatures.txt --kaempfe 1000

# What does Jace bring? Compare two reports
python mtg_sim.py deck.txt --sims 5000 --ausgabe mit_jace.html
python mtg_sim.py deck.txt --sims 5000 --ohne-jace --ausgabe ohne_jace.html

# Save the report without opening the browser
python mtg_sim.py deck.txt --nicht-oeffnen
```
## Fixed assumptions (not adjustable by parameter)

These values are in the script and can only be changed there.

- **Opening hand:** 7 cards. On the Play does not draw on turn 1, On the Draw draws every turn.
- **Traffic-light thresholds** for "Spell cast on turns 1 to 3" (constant `TRAFFIC` at the top of the file):

  | | Turn 1 | Turn 2 | Turn 3 |
  |---|---|---|---|
  | On the Play, green from / yellow above | 20 % / 0 % | 90 % / 80 % | 95 % / 90 % |
  | On the Draw, green from / yellow above | 22 % / 0 % | 92 % / 83 % | 96 % / 85 % |

  Everything below is red. For the fastest lethal: green through turn 5, yellow on turns 6 and 7, red from turn 8
  (function `lethal_level`).
- **Mulligan rules:** (1) no card is playable with the land colors in hand (colors only, not the amount of mana),
  (2) 6 or more lands, (3) at most 2 lands and fewer than 3 cards payable with those lands.
  Landcycling exception: a hand of 6 or 7 cards with at least 2 lands, one card with basic landcycling, and another nonland card up to mana value 3 is kept despite too few lands or missing colors.
  London mulligan (103.5): on a mulligan, the deck is reshuffled, 7 cards are drawn again, and one card per mulligan
  is put on the bottom of the library. The choice that is kept is the one without a mulligan reason, then the one with the land share closest
  to the deck's (on a tie, one land more), then the one with the most payable cards, then the one with the lowest
  mana costs.
- **Card selection per turn:** Among all combinations that can be paid for together, the winner is decided in order by: (1) the most
  mana spent, (2) the most creatures, (3) the highest sum of power and toughness, (4) the most cards.
  There is no lookahead to later turns, except with landcycling. A card that provides mana immediately
  (mana artifact, haste creature with a mana ability, spell with a Heartwood token) is planned first if its mana
  together with the rest makes a better combination (creatures without haste do not).
- **Creatures and damage:** printed power and toughness, summoning sickness except with printed haste, creatures with defender
  never attack (except with Ghalta the Immovable: then they attack, and creatures with more toughness than
  power deal damage equal to their toughness), all other creatures attack every turn. Jace and other planeswalkers have no
  summoning sickness (activation at most once per turn), no blockers, no removal. Counted are +1/+1 counters
  and pumps when cast or when entering (on the strongest attacking creature), landfall damage and counters, counters
  at end of turn without a spell (Edgar) and with loyalty (Inspired Tethermage), as well as damage to the opponent from spells and
  when entering. Bonuses from Auras and other static effects are not counted.
- **Mana:** lands, mana sources other than lands ("{T}: Add …" with no additional costs; creatures from the following turn,
  artifacts immediately; creatures tapped for mana do not attack) and Treasure (only if it
  enables more in that turn). Rituals are not modeled.
- **Cost reduction:** After the creatures on the battlefield at the start of the turn: Geist of Saint Thalia
  (noncreature spells cost {1} less), Ghalta (by the highest power or toughness), Wrath of the Bloodmane (with a
  legendary creature); Traxos gets cheaper if a noncreature spell is cast in the same turn. Only generic mana is
  reduced, the mana value stays the same (601.2f); curve utilization counts the mana actually paid.
  The battle model uses the same calculation.
- **Heartwood, haste for all, threshold spells:** Heartwood tokens and mana artifacts provide
  mana in the turn they enter the battlefield (noncreature artifacts have no summoning sickness); Samut
  gives all creatures haste (Gallia those with a counter); spells like Proft, Sinister Mastermind only from 7
  cards in the graveyard.
- **Granted loyalty abilities:** Way of the …, Sanctum Lurker, Kiora, and Avatar give the Jace token
  additional abilities; they are chosen as in the battle model, in the Goldfish without a token (damage, draw, surveil,
  mana, counters, additional land drop).
- **Way of the Cryomancer and Jace's Machinations:** The copy of the next instant/sorcery counts in the Goldfish only
  for damage (Jace token: lethal before drawing, otherwise after drawing; real planeswalkers only for lethal). Machinations gives
  every Jace (token and cards) an additional activation in its turn.
- **Real planeswalkers:** Planeswalker cards come with their loyalty and use one ability every turn,
  chosen as in the battle model, but without tokens and removal (damage, draw, counters, emblems, Empower; mana only
  if it enables another spell). At 0 loyalty they are gone.
- **Splinter Twin:** The enchanted creature copies itself at the end of each opponent's turn (haste, printed
  values only); the copy repeats its enters effects and attacks alongside the original. Same rules as in the
  battle model (choice of creature, 302.6, only if the creature is already on the battlefield).
- **Draw, surveil, Prepared:** Draw spells with a fixed number draw immediately (catch up on the land drop, keep
  casting with leftover mana). Surveil from cards after casting, land first. Prepared creatures: the copy of the spell half
  is an additional spell without a hand card, also in the turn it enters; upkeep cards become
  prepared again every turn.
- **Tapped lands:** Recognized from the card text (always tapped, check, fast, and slow lands). Shock lands
  pay the 2 life. Other conditions (for example reveal lands) are counted as "always tapped" and listed in the
  report.
- **Lands with a planeswalker condition** ("enters tapped unless you control a planeswalker", e.g. the Commons and
  Annexes from FRA): They enter untapped if a planeswalker is on the battlefield. That is the Jace token (loyalty
  greater than 0) or a cast planeswalker card. If there is none and there is a spell in hand that creates a
  planeswalker (planeswalker card or Empower Jace) and is payable before the land, that spell is
  cast first and the land is played afterward. Tokens count only on the battlefield, never from hand.
- **"Behold a Jace"** (e.g. Theorist's Sanctum): The land enters untapped if a Jace is on the battlefield (token
  or planeswalker with subtype Jace) or a Jace card is in hand (it is only revealed, not cast).
  Other planeswalkers do not suffice. Only cards that create a Jace qualify as a spell cast ahead of the land.
- **Card types and colors in the report:** The overviews from the Draft Helper are also in the report. In the "Deck" section,
  **"Mana curve by color"** replaces the previous single-color curve: on the left stacked with multicolor
  cards as a golden segment (each card once, total above the bar), on the right per color (multicolor cards count
  for each of their colors). Below it the color combinations. Next to it the table **"Card types"** (creatures,
  instants, sorceries, artifacts, enchantments, planeswalkers, lands, Empower Jace, card flow by kind). In the
  "Deck comparison" there is "Card types compared" with one column per deck, differences in bold.
- **Jace and surveil:** The Jace token has −1: Surveil 1 and −3: draw a card, at most one activation per
  turn. At the start of the turn it only draws (from 3 loyalty). After casting: draw from 3 loyalty, otherwise Surveil 1, even
  if that drops Jace to 0 and he disappears. On surveil, a land stays on top if the most expensive card in
  hand cannot be played yet because lands are missing (lands on the battlefield and in hand fewer than its
  mana value); otherwise it goes to the graveyard. Spells always stay on top. The Jace section in the report also shows
  avg surveil and avg lands put into the graveyard.
- **Report and explanation separated ("How it works"):** The report now shows only data. All rules and
  reading aids (game logic, model assumptions, mulligan and Jace rules, traffic-light thresholds, comparison statistics,
  counting rules, Draft Helper …) are on a separate explanation page, section by section as in the report. At the top of the
  report, "Report | How it works" switches the view; each section has a link "ⓘ How it works"
  to its explanation, and from there "← Back to report" leads back to the same spot. Both are in the same
  HTML file. The explanation page describes the rules in general terms with parameters and default values; the values of the run
  are at the top of the report. In the Draft Helper, the explanation page is also available under "How it works" in the help box.
- **Design and navigation:** The report and the battle report use the Draft Helper's light design (Splash red,
  NoSplash gold). The header bar stays at the top. On the left is a sidebar with **Key figures** (mulligan,
  spells in the evaluation turn, fastest lethal, avg turn for damage; in the battle report the win rates),
  the jump links to the sections (the current section is highlighted), and the settings of the run. On
  narrow screens (under 900 pixels) the sidebar is placed at the top.
- **Color availability (report):** Its own section and a row in "At a glance": How often are **all colors** of the deck on the battlefield after
  the land drop of turn 3 (at least one source per color), and for each color individually? For colors that
  a card requires twice (e.g. RR, with card names), additionally: How often are **two sources** on the battlefield by turn 4?
  Source = land on the battlefield (even tapped); a land with several colors counts for each. Traffic light: green from 90 %, yellow from
  80 %. In the deck comparison, "All colors by turn 3" and the two-source values appear as their own key figures.
- **Model coverage (report):** The "Model coverage" section lists, per deck, the cards whose effects the
  simulation does not yet reproduce, with the status "To do: not implemented yet", a rough category
  (Create tokens, Direct damage, Counters / power bonus, Grant haste, Mana besides lands, Card flow,
  Cost reduction / convoke, Second use, Prepared, Interaction with the opponent, Life gain, …) and the affected
  metric (lethal, mana and spells per turn, card flow, none, unclear). At the top it shows how many cards affect which
  metric. Detection works only on the card text and is rough; anything that cannot be classified is called
  "Unknown effect" (metric "unclear"). Every line that the card model recognizes (Goldfish
  and/or battle model) is not reported: the card is parsed with only that line for this purpose. For partially recognized lines, the
  open remainder stays listed. The numbers in the report do not change as a result.
- **Limitation:** In a turn in which a spell is cast before the land, landcycling after the
  land is skipped (payment would otherwise not be assured). For planning the following turn (landcycling lookahead),
  planeswalker lands are still treated as tapped.
- **Empower Jace (counting):** Detected from the Scryfall card text, on all faces of a card. Classified
  by kind: one-time (instant or sorcery, "when it enters", one-time special case such as "when it dies") and recurring
  ("whenever" and "at the beginning" triggers, payable abilities with costs). A card can be
  in several groups. The sum of the Empower values is shown separately for one-time and recurring, and for recurring as a
  value per trigger. Also counted are cards that mention Jace or planeswalkers (helping), cards against
  planeswalkers (destroy, damage), and planeswalker cards themselves. In this section they are only counted;
  planeswalker cards and removal against planeswalkers are simulated by the Goldfish and the battle model (see below).
  Next to each card, the report shows the detected text so you can check the classification.
- **Empower Jace (simulation):** The Jace token starts with 0 loyalty and has −3: draw a card. It is activated
  as soon as it has at least 3 loyalty and the library is not empty, **at most once per turn**: at the start of the turn with
  loyalty from earlier turns, otherwise after casting. At 0 loyalty the token disappears, and the next Empower creates
  a new one. One-time effects take effect immediately when played (also for lands). Of the recurring effects, these are
  modeled: "whenever you cast …" (all, creature, noncreature, instant or sorcery), "whenever … enters" (creature,
  land, permanent), "whenever … attacks", and "at the beginning of …" (once per turn from the following turn). Payable
  abilities use the mana left over after casting, as often as it suffices (at most 10 times per turn, once with {T} in the
  cost); exile from the graveyard (Campus Crier) is modeled. Not modeled and listed in the report are
  unknown triggers, other costs (sacrifice, discard), and special cases like "when it dies". Variable Empower (X): on
  attack X = own creatures (Repurposed Enforcer), Jace, Reality Sculptor by Islands, in the battle model also
  exiled creatures and excess damage; other X count as 0. Modal spells always count their Empower.
- **Jace statistic "until the hand is empty":** Counted until the first end of turn with no cards in hand (after
  casting and a possible activation). If the hand is never empty, the entire observation period counts
  (`--max-runden`). Each activation draws exactly one card, so activations and drawn cards are equal in number.
- **Safeguard against unplayable decks:** If, after `50 × --sims + 1000` hands dealt, `--sims`
  games have still not been played, the script aborts with an error message.

A detailed description of the selection logic with a worked-out example is in the "Game logic" section
of the explanation page "How it works".

## What the report shows

Deck comparison (only with `--deckalt` or multiple variants), Great in this deck! (only from the Draft Helper), At a
glance, Deck (Mana curve by color, color distribution, card types, card table), Removal, Graveyard,
Model coverage, Mulligan, Jace & Planeswalker, Spells per turn, Creatures, Mana Screw & Flood,
Color availability, Splash cards (only the Splash variant from the Draft Helper), Curve utilization, Damage from
creatures, fastest lethal (with game log), Landcycling, Draw spells, Surveil from cards, Prepared, Ramp
and tempo. Sections on mechanics appear only if the deck has matching cards. Game logic, model assumptions,
and the explanation of each section are on the explanation page "How it works"; the settings of the run
are at the top of the report and in the sidebar.

With `--bericht-server` (or analysis via `draftgott.bat`), the report has the **Simulate battle** bar at the top:
choose an opponent deck and the number of battles (50, 100, 250, 500, or 1000 per deck and mode; 500 preselected, the
last choice is remembered by the browser), start the battles, and the battle report opens afterward.
## Battles against opponent decks

Opponent decks are deck files in the `enemydecks` folder of the project directory (e.g. `enemydecks/bad_creatures.txt`,
`enemydecks/hard_whiteblue_creatures.txt`). The display name is the `Name` line from the file, otherwise the file name. For
`--gegner`, the file name is enough (the `.txt` can be omitted). A battle is started with `--gegner`, via “Simulate battle” in the
report (with `--bericht-server`), or in the Draft Helper.

**Battle report:** Win rate per opponent and variant (Play / Draw) as tiles and in the sidebar, an overview
(wins, losses, of which due to mulligan, draws), key figures per opponent (avg. turn, combat damage and direct
damage, creatures that died, life total over time), notable games, and a game list in which each game expands to show its
full log. The rules of the battle model are described in detail at the end of the battle report.

**Battle model (short version):**

- Both players start at 20 life and play by the same rules, without knowing the other's hand.
  Mulligan as in MTG Arena (as in the Goldfish); if our hand falls below the minimum size, we concede.
- One turn: untap, draw, main phase 1 (land and all spells except creatures without haste; creatures whose entering the
  battlefield improves combat already here), combat, main phase 2, end step. Leftover mana stays open for instants, flash,
  combat tricks, and abilities, including on the opponent's turn. If the opponent has a creature that our removal can kill,
  we keep the cost of the cheapest instant, flash, or discard removal available.
- Attacking: everything when lethal is certain, otherwise only creatures that no blocker can kill while surviving itself. Blocking:
  blocker kills and survives, trade at equal or greater mana value, double block, chump block only against lethal.
- Combat keywords: flying, reach, first strike, double strike, deathtouch, trample, lifelink, menace,
  vigilance, haste, defender, hexproof, indestructible (also conditional, e.g. only on your own turn).
- Foundations for upcoming sets (battle model, tested with cards from SOS, HOB, and MSH): conditional abilities
  (“as long as you control another …”, infusion, creature cards in the graveyard), keywords for creatures with a
  counter, granted ward/hexproof/unblockable, Equipment on entering the battlefield and as a token, “Equip <type>”, counters at the
  beginning of combat, attack triggers with keywords, and general “Whenever you cast …” triggers (repartee, opus,
  noncreature, type, and color spells), Vehicles with crew (attacking and blocking), and “tap target creature defending
  player controls” on attack.
- Alchemy: Reality Fracture (YFRA), package A: perpetual, conjuring named cards, seek (Killian), Avoided
  Stairwurm, Zimone, Dina, Asymmetry Sage, Sparks Ablaze, Paradox Kraken, Boisterous Clique, Searing Soloist
  (cards to conjure are in `components/conjure.py`).
- Station (EOE, TRK): Spacecraft get charge counters in main phase 2 from creatures that are not needed against a lethal
  counterattack; levels with keywords, team pumps, and P/T (then an artifact creature). Planets are not modeled.
- Face a dilemma (TRK): modal spells (on cast) and modal enter-the-battlefield triggers set off “Whenever you face a
  dilemma” of your own cards, once per spell or trigger (Elim Garak, Obsidian Order Operative, Seven of Nine).
- Strange new worlds (TRK): X = your lands with different names (power/toughness, tokens, life, drawing, cost reduction
  for spells and abilities, mass −X/−X, attack pump); also warp speed. Chekov and Branching Timeline are deliberately not modeled.
- Beam me up (TRK): sorceries from the graveyard like flashback, plus one of your own creatures returns to hand
  (most valuable enter-the-battlefield effect, otherwise the cheapest, never against a lethal counterattack); Scotty.
- Sagas (rule 714, TRK): chapters after each of your own draw steps, then sacrificed; investigate with a Clue token.
- Lands and tokens (TRK): planet lands with life, lands with a mode when entering untapped, New Planet tokens
  (tapped, landfall), anomalies and Unexplored Territory (sacrifice at the end of the opponent's turn with leftover mana),
  land search onto the battlefield with Planet cards, Food, anthems (also only for artifact creatures), “can't block”, “can't
  attack alone”, evasion, Saru and Shields Up! against removal, Tal Shiar Operative, cost reduction against attackers,
  death triggers with damage and tokens.
- Total power 8 (TRK): attack triggers “while creatures you control have total power 8 or greater” (counter, pump,
  “can't block”, double power, Kirk's exiled card in main phase 2) and Cantankerous Captain.
- Borg (TRK): keywords for artifact creatures, Collective Drone, Hive Mind Coprocessor, Antagonist
  Incorporator, Organic Avulsion Unit, Collation Trimatrix, Assimilate (Death Is Irrelevant, Borg Cube), affinity.
- Dying and graveyard (TRK): triggers on death (Excalbian, Survivalist, Gowron, Zek, Sarcophagus) and when cards leave
  the graveyard (Blastoneuron, Sela, Hologram Stalker, Vash), casting from the graveyard with finality (Storied
  Veteran, Overflow Submatrix), U.S.S. Reliant, abilities from the graveyard, Sylvia Tilly, Temporal Conqueror.
- Tapping and stun (TRK): tap/stun on entering the battlefield, “becomes tapped” triggers, untapping (DOT-7, D'Vana Tendi), Tal
  Shiar Analyst, Marooned, Hemmer, Species 8472 against artifact abilities, MACO Strike Team.
- Federation (TRK): X = creature types among your non-Borg creatures (Saavik, Hoshi Sato, Captain Archer, Sarek,
  Infinite Diversity, Starfleet Academy).
- Quest missions (TRK): Conquest, Anthropological, Vengeance, Exploratory, Support with their own quest counters.
- Card flow (TRK): look at the top cards and take one (Rutherford, There's Coffee in that Nebula, Spock,
  Pattern Buffer Preservation), lands from the top (U.S.S. Voyager, Hit It!), searching by card type (Federation
  Resupply, H.M.S. Bounty), impulse (Reckless Impulse, Silicate Surveyor), sacrifice and draw (Khan, Automated Warfare
  System), Mr. Spock, Data, Phlox, Tricorder, Seven of Nine, Live Long and Prosper, Dathon, Dal R'El.
- Kicker (TRK): Highly Illogical (bigger spells only with kicker), Eject the Warp Core (sacrifices only if −2/−2
  is not enough), Mirror Universe Intrusion (copy with menace, with kicker from every opposing creature).
- Tapping (TRK): Brad Boimler, Captain Jean-Luc Picard, Worf, Honor-Bound Warrior (main phase 2 like Station), Kira Nerys,
  Nog (Scout, Officer), I'm a Doctor, Not a . . .; Lwaxana Troi still open.
- Counters, landfall, life, and mana (TRK): Xindi Surveyors, Syndicate Liquidators, Captain Michael Burnham, Deanna
  Troi, Academy Instructor, Dominion Supervisor, Pure Energy, Culber and Stamets, General Chang, Jadzia Dax,
  Sickbay, Picard, Leading by Example, Tea, Earl Grey, Hot, Khan, Despot by Design, Crystalline Entity, Armus,
  A Good Day to Die, Savvy Profiteer, Quark, Rok-Tahk, Gul Dukat.
- Beginning of combat and modes (TRK): D-7 Battle Cruiser, L'Rell, Captain James T. Kirk, Kobayashi Maru Scenario (only shortly
  before winning), Captain Benjamin Sisko (without the five-color ability), The Naked Time.
- Sacrifice and graveyard (TRK): Gowron, Kirk, Commanding Officer, Dahar Master, Targ Wrangler, Dr. McCoy, Bones McCoy,
  Raffi Musiker, Gabriel Lorca, The Needs of the Many, De-evolve, Tell Me What You See, Khan from exile;
  removal with "Exile target ..." exiles (previously graveyard).
- Opponent's hand and interaction (TRK): V'Ger, Salt Vampire, Zero, Kai Winn, Nyota Uhura, Brazen Bluff, The Caretaker,
  Worf, Intelligence Contractor, Engineered Explosives, Peace in Our Time, Dominion Infiltration.
- Charge counters and artifacts (TRK): Warp Core, Geordi La Forge, Romulan Bird-of-Prey, Zefram Cochrane, Enterprise-D,
  Isolinear Processor, Combadge, Lieutenant Commander Data, Dathon, Seven of Nine (7/9); Gwyndala without its
  copy ability.
- Library, lands, blink (TRK): Ghost of Illyria, Miles O'Brien, Q, Will Riker, Captain Janeway, Captain Pike,
  Genesis Device, U.S.S. Discovery, Deep Space 9, The Holodeck.
- Copies and doublers (TRK): Dr. Beverly Crusher, Troubling Tribbles, Dominion Saboteur, Georgiou, Dr. M'Benga,
  Holo-Engineer, Gray and Adira, Replicator; Lwaxana Troi deliberately not. This completes TRK (306/306).
- Removal (destroy/exile, damage, −X/−X, edict, fight, bite, bounce, lock, back into the library,
  mass removal) hits the most dangerous matching creature; removal instants before the attack, against attackers, or at the
  end of the opponent's turn.
- Modeled, among others: Jace (Empower) with attacks on Jace, activated abilities, tokens, prowess,
  triggers on cast, entering the battlefield, attack, death, life gain, scry/surveil, and landfall, graveyard (flashback, returning cards,
  Phoenix, finality), modal cards, loot and rummage, ward, Equipment, exile until it leaves the battlefield (Memory Trap),
  removal against enchantments and artifacts, stun counters, playing cards from
  exile, damage based on toughness (Ghalta the Immovable), the legend rule, maximum hand size, cost reduction, and
  additional costs.
- Counterspells: what gets countered is whatever would be lethal, removal aimed at your most dangerous creature, and creatures
  with mana value 3 or more; from turn 5 on, mana is kept open for this. Fixed rule: no counter-counterspells.
- True planeswalkers: one loyalty ability per turn, chosen in the order lethal > ultimate/emblem > removal > big token >
  draw > small token > plus with value > plus without value; a minus ability that brings it to 0 only for lethal,
  an ultimate, or removal. The opponent's planeswalkers are always attacked, with as little damage as necessary (lethal
  on the player takes priority). Removal “creature or planeswalker” hits a planeswalker if it kills it and the
  opponent has no creature with power 4 or more; the Jace token only from 5 loyalty with no creature as a target.
- Lilianas trigger on planeswalkers as well; Liliana the Repentant uses exhaust to return one creature or one
  planeswalker with mana value 4 or more once; Mabel, Bitter Recluse removes counters (loyalty first); Tam makes
  planeswalker spells cost {1} less; Rewrite Regrets returns creatures and planeswalkers.
- Minor FRA effects (mill, threshold bonuses, loot on attack, token bonus, Roiling Canopy, Hapatra, Eye of
  Jace, Enroot, Germinate Recruits, Room of Refuge, Solitary Cell, and others) work in the battle model and, where sensible, also in the
  Goldfish (mill, Karn, loot, Roiling Canopy, Room of Refuge, Eye of Jace, Enroot).
- More FRA effects: Simulacrum Shaper (basic land tapped, also in the Goldfish), Gardenize, token copy of the Sphinx,
  Command the Stage, Verdant Kraken, Danitha, Yoshimaru, Bloodline Recollector, Infinite Coursework, Garruk, Veiled
  Butcher (exile instead of dying), Guiding Hydra, Curse-Marred Demon, Pia. Lock auras on opposing creatures
  do not need a creature of your own.
- Rules from FRA: “attacks alone” (Jiang Yanggu, Yuriko), Yuriko locks combat spells, split second (Samut), no
  enter-the-battlefield triggers (Karn, Argent Defender), Draconic Visitor, Lotus (Kwia), Tarmogoyf, Traxos, loot (both),
  Seasoned Cryomancer, Medic's Kitesail, Return to the Light Realms.
- Play decisions from FRA (battle model): Hunter's Axe, Gideon's Memorial, loot sacrifice for lethal, your own auras with a
  bonus (Ferocity of the Hunt), Proctor of Potential, Hungering Puppetbeast, Identity Echo, Hexhaven Dueling Arena,
  Codie, Flickering Hound, Rescue Girl, Hall of Echoes, Hexhaven Invigorator, Puppet Crafting, Seasoned Cryomancer
  (drawing from the graveyard).
- FRA package E: Emrakul, the Exigent Doom (untap on cast, exile from hand with a {C}{C} land, ward by
  sacrificing), Omnipresence (Goldfish and battle model), Uldaros Theorix, Codie (copy of a prepared spell), Fblthp, Impossibly
  Lost.
- FRA package F: Konstrari Charm/Tam's Resistance (“It gains …”), Tethermage's Advantage (“Untap it”), Overwrite the
  Multiverse and Violent Echoes (Empower X), Avatar of Burgeoning Echoes (landfall Empower), Heartwood Crafter (mana only
  for copies), Gideon's Memorial (mana only for planeswalkers). Coverage: lines that are only modeled by the card as a whole
  (Equipment bonus, Null Summoner, Dueling Arena, Campus Crier, Repurposed Enforcer, Jace +1, Tether Technician)
  count as covered; deliberately not modeled: Theorist's Proxy (never sacrifices itself), Marwyn (hexproof for lands),
  Paradox Shaper ({2}: card under the library), Sphinx's Approach (five copies).
- FRA package G (battle model): Aerid Konstrari {6}, Yoshimaru {6}, Hapatra {2}{U}, Teyo (both), Liliana the Faultless
  (hexproof in response to removal), Jace, Reality Sculptor 0 (library from 25 loyalty).
- Tomik: at most one attacker per planeswalker. Entrust the Spark sacrifices only a Jace token and fetches the
  most expensive planeswalker; Loyal Tutor puts a planeswalker on top of the library (also in the Goldfish).
- Way of the Cryomancer: the copy of the first instant/sorcery is planned in main phase 1 (lethal, removal with a
  second target, drawing; true planeswalkers only for lethal or removal). Jace's Machinations at the end of the opponent's
  turn with one more activation of all Jaces.
- Chandra, Torch of Defiance +1 (battle model): the exiled card is cast with the free mana if it is not a land,
  otherwise, or when it gives lethal, 2 damage; in the Goldfish always 2 damage.
- Not modeled, among others: convoke (Winter, Team
  Player), proliferate (Tam, the Possibility), cards from outside the game (Extrapolate the Impossible), and sacrificing
  as a cost except for the cards named; such cards are played but only work with their modeled
  effects.
- Battle report: notable games with a turn log – fastest win, fastest loss, closest and comeback
  win or loss, and the longest game (most turns, regardless of how it ended).

## Details per variant

With `--deckalt` or several deck files, all detail sections (At a glance through Model assumptions, so also
Fastest lethal, Jace & planeswalkers, Mulligan, Curve …) are calculated for **each** deck. Under “Deck comparison”, use
the “Details for: …” buttons to pick the deck. The navigation at the top adapts. Without JavaScript, all decks are
listed one below the other.

## The “Deck comparison” section

It appears only with `--deckalt` and sits at the very top of the report.

- **Overview:** Which cards each alternative adds (green) or removes (red) compared with the base deck.
- **Summary:** Per alternative and mode, on how many metrics it is significantly better, worse, or
  indistinguishable.
- **Detail tables:** Per mode (Play and Draw), each metric with its value ± confidence interval and the difference Δ from the base deck.
- **Method:** Proportions (e.g. mana screw) with a Wilson interval (95%), means with standard error. A difference counts as
  significant if |Δ| is greater than 1.96 × the standard error of the difference. Because of the many metrics, individual
  “significant” hits should not be overinterpreted (multiple comparisons). For identical decks, the false-alarm rate in tests
  was about 7–10% instead of 5%, so the intervals are slightly too optimistic.

## Notes on interpretation

- **Random samples only:** Results are estimates. The higher `--sims`, the smaller the fluctuation.
- **Fastest lethal:** This is the best of all simulated games, so it is a stroke of luck and not an expected value.
  For the typical case, use “Avg. turn” and the line chart.
- **Deck comparison:** It is best to compare deck lists with `--deckalt`. Small differences within the intervals are
  noise. More `--sims` shrinks the intervals.
- **Comparing settings:** If you compare settings (e.g. `--ohne-jace`), run both runs with the same
  `--sims` and `--seed` and open the reports side by side.
