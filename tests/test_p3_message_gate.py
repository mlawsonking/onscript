"""The task B gate on the message class, and the standing reminder the app carries.

Pass 1 of the pilot labelled 155 items message while leaving the completeness answer blank on
141 of them and answering it no on 3 more, and never once reached for unknown. The guide makes
completeness a necessary condition for message, so the app now refuses a message label the
completeness answer does not support.

``message_blocked_by`` is the authority. The rendered app interpolates its strings rather than
restating them, and these tests hold the two together (docs/37 rule 1).
"""
from pipeline import goldset_bundle as gb


def _item():
    return {
        "candidate_id": "cand:test1", "phrase": "working families",
        "before": "", "sentence": "Republicans claim they are for working families.",
        "after": "", "title": "T", "office": "D House CA", "date": "2025-01-03", "support": [],
    }


def test_the_gate_refuses_message_until_completeness_is_answered():
    assert gb.message_blocked_by({}) == gb.GATE_UNANSWERED
    assert gb.message_blocked_by({"phrase_complete": None}) == gb.GATE_UNANSWERED


def test_the_gate_refuses_message_when_the_phrase_is_incomplete():
    assert gb.message_blocked_by({"phrase_complete": False}) == gb.GATE_INCOMPLETE


def test_the_gate_permits_message_when_the_phrase_is_complete():
    assert gb.message_blocked_by({"phrase_complete": True}) is None


def test_the_gate_does_not_read_any_other_field():
    """Only task B gates the class. A blank family or stance is not this gate's business."""
    permitted = {"phrase_complete": True, "gold_family_id": "", "stance": "",
                 "claim_supported": False, "proposition_consistent": False}
    assert gb.message_blocked_by(permitted) is None


def test_the_rendered_app_carries_the_gate_strings_from_their_owner():
    app = gb.render_app([_item()], annotator_id="ann-a", sample="pilot", seed="s")
    for owned in (gb.GATE_UNANSWERED, gb.GATE_INCOMPLETE, gb.GATE_WITHDRAWN):
        assert owned in app, owned
    # No placeholder survives interpolation.
    for placeholder in ("__GATE_UNANSWERED__", "__GATE_INCOMPLETE__", "__GATE_WITHDRAWN__"):
        assert placeholder not in app, placeholder


def test_the_rendered_app_enforces_the_gate_on_both_orderings():
    """Selecting message with B unanswered, and answering B no after message was recorded.

    These assert the wiring exists. The behavior itself was exercised against the rendered
    packet in a browser: message refused with B blank and with B false (nothing recorded),
    accepted with B true, and withdrawn when B was flipped to false afterwards.
    """
    app = gb.render_app([_item()], annotator_id="ann-a", sample="pilot", seed="s")
    # Refusal at the point of selecting message, recording nothing.
    assert "if (blocked){ showGate(panel, blocked); return; }" in app
    # Withdrawal when a later B answer invalidates a message label already recorded.
    assert "delete a.gold_class;" in app
    assert "GATE_WITHDRAWN" in app
    assert "messageBlockedBy" in app


def test_the_app_surfaces_unknown_as_the_safe_default():
    app = gb.render_app([_item()], annotator_id="ann-a", sample="pilot", seed="s")
    assert "Unknown is the safe default" in app
    assert "Label the <b>phrase</b>, not the sentence" in app
    assert "section 3.1" in app


def test_the_read_only_packet_carries_the_same_standing_reminder():
    html = gb.render_html([_item()], annotator_id="ann-a", sample="pilot", seed="s")
    assert "Unknown is the safe default" in html
    assert "Label the phrase, not the sentence" in html
    assert "a phrase that fails B cannot be a message" in html


def test_task_b_is_marked_required_in_the_app():
    app = gb.render_app([_item()], annotator_id="ann-a", sample="pilot", seed="s")
    assert "B. phrase complete *" in app
    assert "Class, family, and B (phrase complete) are required" in app


def test_the_guide_states_the_rule_the_gate_enforces():
    """The app and the guide must not drift apart on a rule the app now enforces."""
    from pipeline import config
    from pathlib import Path
    guide = (Path(config.REPO_ROOT) / "evaluation" / "ANNOTATION-GUIDE.md").read_text(
        encoding="utf-8")
    assert "The trap: letting the context supply the meaning" in guide
    assert "unknown` is the safe default" in guide
    assert "a phrase that fails task B cannot be a message" in guide
    assert "Answer task B on every item" in guide
