"""The annotation app's shell: one item at a time, resumable, and portable between devices.

The pass is worked in gaps between other things, on more than one device. Three properties
follow and each is asserted here:

  1. One item is in the DOM at a time. Two hundred cards with support sets is a page no phone
     enjoys, and position matters more than scroll when the pass spans days.
  2. Progress moves as a file. localStorage is scoped per origin, so a pass worked from a local
     file and from a served copy are two different stores that would otherwise never meet.
  3. The answer sheet exports at any point, not only at 200 of 200.

The gate behavior these controls wrap is tested in test_p3_message_gate.py.
"""
import json
import re

from pipeline import goldset_bundle as gb


def _items(count=3):
    return [{
        "candidate_id": f"cand:test{i}", "phrase": "working families",
        "before": "b", "sentence": "Republicans claim they are for working families.",
        "after": "a", "title": "T", "office": "D House CA", "date": "2025-01-03",
        "support": [{"office": "D House NY", "date": "2025-01-03", "sentence": "s"}],
    } for i in range(count)]


def _app(count=3):
    return gb.render_app(_items(count), annotator_id="michael-pass2", sample="pilot", seed="s")


def test_every_element_the_script_reaches_for_exists_in_the_markup():
    """A rewrite that renames a control silently breaks a button. Hold them together."""
    app = _app()
    wired = set(re.findall(r"getElementById\('([a-zA-Z-]+)'\)", app))
    present = set(re.findall(r'id="([a-zA-Z-]+)"', app))
    assert wired, "the script wires up no elements at all"
    assert wired <= present, wired - present


def test_the_item_container_ships_empty_and_cards_are_built_on_demand():
    app = _app(200)
    assert '<main id="items"></main>' in app
    # One template in the script, no pre-rendered cards.
    assert app.count('<article class="item"') == 1


def test_the_app_carries_position_navigation_and_a_jump_map():
    app = _app()
    for control in ('id="prev"', 'id="next"', 'id="pos"', 'id="nextnew"', 'id="togglemap"',
                    'id="map"'):
        assert control in app, control
    assert "nextUnlabeled" in app
    assert "paintMap" in app


def test_the_cursor_survives_a_reload():
    app = _app()
    assert "KEY + '-at'" in app
    assert "localStorage.setItem(KEY + '-at'" in app


def test_progress_is_portable_and_refuses_a_foreign_packet():
    """Import validates the packet it came from before merging anything."""
    app = _app()
    assert "onscript-goldset-progress" in app
    for control in ('id="saveprog"', 'id="loadprog"', 'id="copyprog"', 'id="pasteprog"',
                    'id="progfile"'):
        assert control in app, control
    # The guard: sample and annotator must both match before a single answer is taken.
    assert "payload.sample !== DATA.sample || payload.annotator !== DATA.annotator" in app
    # Candidate ids outside this packet are dropped rather than merged.
    assert "if (!valid.has(cid)) { skipped++; return; }" in app


def test_the_answer_sheet_exports_before_the_pass_is_finished():
    """A partial export is allowed and is labeled partial, so it is never mistaken for a pass."""
    app = _app()
    assert "Exported a PARTIAL sheet" in app
    assert "have a class and a family. The rest are blank rows." in app


def test_the_app_is_laid_out_for_a_phone():
    app = _app()
    assert "@media (max-width: 34rem)" in app
    assert "width=device-width" in app
    # The family input's desktop min-width would overflow a narrow screen.
    assert ".fam, .notesin { min-width: 0; width: 100%; }" in app


def test_a_working_answer_sheet_is_never_indexable():
    assert '<meta name="robots" content="noindex,nofollow">' in _app()


def test_the_payload_still_carries_no_machine_signal_after_the_rewrite():
    app = _app()
    payload = json.loads(app.split('id="goldset-data" type="application/json">')[1]
                         .split("</script>")[0].replace("<\\/", "</"))
    assert payload["annotator"] == "michael-pass2"
    for item in payload["items"]:
        assert set(item) <= {"candidate_id", "phrase", "before", "sentence", "after",
                             "title", "office", "date", "support"}


def test_typing_a_family_id_does_not_trigger_item_navigation():
    """Arrow keys page between items, which would be intolerable mid-word in a text field."""
    app = _app()
    assert "if (tag === 'input' || tag === 'textarea'" in app
