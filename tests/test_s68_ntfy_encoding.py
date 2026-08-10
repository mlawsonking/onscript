"""S68-5 acceptance: the dead-man may not die of its own subject line.

An ntfy title rides in an HTTP header and http.client encodes header values as latin-1, so a
single typographic dash in a title raised UnicodeEncodeError inside urlopen, `ops.ntfy` swallowed
it as a skip-and-log, and the notification was silently never sent. The Owner's Brief titled itself
"OnScript brief" plus U+2014 plus the headline, which puts the offending character at position 15,
and run 31386662898 logged exactly that at 12:19:29.08Z on 2026-08-10:

    [ntfy-failed] OnScript brief <U+2014> RED: coverage, verifier_drop: 'latin-1' codec can't
    encode character U+2014 in position 15: ordinal not in range(256)

The defect is deterministic and the title literal was constant, so this had been eating the Monday
digest every Monday since FEATURES["owners_brief"] flipped. Nothing had ever been delivered.

The fix is at the owner: `ops.header_safe` makes every header value ASCII by construction, so no
caller can cost a page a glyph it happened to contain. The brief's own literal is fixed too. These
tests hold both, and the last one holds the whole call-site surface against a repeat.
"""
from __future__ import annotations

import ast
import os
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from pipeline import brief, config, ops


ROOT = Path(__file__).resolve().parent.parent
EM_DASH = chr(0x2014)


@contextmanager
def _wire():
    """A live-looking send path with the network replaced. Captures the Request that urlopen got.

    NTFY_TOPIC is restored on the way out. Leaking it would leave every later test in this process
    holding a topic and trying to reach the real ntfy.sh.
    """
    sent = []
    real_urlopen, had = urllib.request.urlopen, os.environ.get("NTFY_TOPIC")
    os.environ["NTFY_TOPIC"] = "onscript-test-topic"
    urllib.request.urlopen = lambda request, **kw: sent.append(request) or _Response()
    try:
        yield sent
    finally:
        urllib.request.urlopen = real_urlopen
        if had is None:
            os.environ.pop("NTFY_TOPIC", None)
        else:
            os.environ["NTFY_TOPIC"] = had


class _Response:
    def read(self):
        return b""


def _header(request, name):
    """urllib capitalizes header keys as it stores them."""
    return request.headers[name.capitalize()]


def _transmittable(value: str) -> bool:
    """Would http.client actually put this on the wire? That is the whole question."""
    try:
        value.encode("latin-1")
        return True
    except UnicodeEncodeError:
        return False


# --- the incident, reproduced against the fixed owner ------------------------------------------

def test_the_title_that_killed_the_monday_digest_now_sends():
    title = f"OnScript brief{EM_DASH} RED: coverage, verifier_drop"
    assert not _transmittable(title), "the raw title is still unsendable; that is the premise"
    with _wire() as sent:
        result = ops.ntfy(title, "body")
    assert result == {"sent": True}
    header = _header(sent[0], "Title")
    assert _transmittable(header) and header.isascii()
    assert header == "OnScript brief -  RED: coverage, verifier_drop"


def test_an_arbitrary_non_latin1_codepoint_still_sends():
    for codepoint in (0x4E2D, 0x1F600, 0x0416, 0x2603):
        with _wire() as sent:
            result = ops.ntfy(f"OnScript alarm {chr(codepoint)}", "body")
        assert result == {"sent": True}, hex(codepoint)
        header = _header(sent[0], "Title")
        assert header.isascii(), hex(codepoint)
        assert header.startswith("OnScript alarm ")


def test_the_body_keeps_every_character_the_header_had_to_give_up():
    """The narrowing is the header's alone. A page that loses its detail is a page half sent."""
    message = f"congress-press stale 41h{EM_DASH} running on mirror"
    with _wire() as sent:
        ops.ntfy(f"OnScript collect{EM_DASH} stale", message)
    assert sent[0].data == message.encode("utf-8")
    assert sent[0].data.decode("utf-8") == message


def test_the_priority_header_is_sanitized_too():
    with _wire() as sent:
        ops.ntfy("OnScript watchdog", "body", priority=f"high{EM_DASH}")
    assert _header(sent[0], "Priority").isascii()


# --- the guarantee, and the courtesy on top of it ----------------------------------------------

def test_every_header_value_is_transmittable_by_construction():
    """Total, not enumerated: the transliteration table is a courtesy, `encode(replace)` is the
    guarantee, and it has to hold for input nobody predicted."""
    hostile = [EM_DASH, chr(0x1F4A9), chr(0x4E2D) * 40, chr(0x202E), chr(0x2028),
               "plain ascii", "".join(chr(c) for c in range(0x2000, 0x2100)),
               "", "  ", chr(0x10FFFF)]
    for value in hostile:
        safe = ops.header_safe(value)
        assert safe.isascii(), repr(value)
        assert _transmittable(safe), repr(value)
    # Non-strings must not raise either; a caller interpolating an int is not a dropped page.
    assert ops.header_safe(7) == "7"


def test_the_transliteration_keeps_a_title_readable():
    assert ops.header_safe(f"a{EM_DASH}b") == "a - b"
    assert ops.header_safe(chr(0x2019)) == "'"
    assert ops.header_safe(chr(0x201C) + chr(0x201D)) == '""'
    assert ops.header_safe(chr(0x2026)) == "..."
    # An unmapped character costs a glyph, never the notification.
    assert ops.header_safe(chr(0x4E2D)) == "?"


# --- the caller, and every other caller --------------------------------------------------------

def test_the_brief_title_literal_carries_no_em_dash():
    source = (ROOT / "pipeline" / "brief.py").read_text(encoding="utf-8")
    call = next(line for line in source.splitlines() if "ops.ntfy(" in line)
    assert EM_DASH not in call, call
    assert 'f"OnScript brief: {b[\'headline\']}"' in call


def test_the_real_monday_brief_reaches_the_wire_with_an_ascii_header():
    """Production shape (docs/37 rule 2): the real `build_brief` over the committed corpus, the
    real `send_brief` title construction, the real `ops.ntfy`, and only the network replaced.

    `util.write_json` is stubbed because `send_brief` writes its artifact under data/derived and
    this session commits nothing there. force_cadence bypasses only the Monday gate, never the
    dark gate."""
    day = "2026-08-03"          # a Monday whose day record is committed
    assert config.feature_on("owners_brief"), "the brief is dark; this test would prove nothing"
    written, real_write = [], brief.util.write_json
    brief.util.write_json = lambda path, payload, **kw: written.append(path)
    try:
        with _wire() as sent:
            result = brief.send_brief(day, force_cadence=True)
    finally:
        brief.util.write_json = real_write
    assert result["sent"] is True, result.get("reason")
    assert written, "send_brief still writes its artifact; only the destination was stubbed"
    header = _header(sent[0], "Title")
    assert header.isascii() and _transmittable(header)
    assert header.startswith("OnScript brief: ")
    assert result["brief"]["headline"] in header
    # The rendered body is the full digest and keeps its typography.
    assert len(sent[0].data) > 200


def test_no_ops_ntfy_title_in_the_pipeline_carries_a_character_the_header_cannot_take():
    """Every call site, read from the live modules rather than from a list kept beside them
    (docs/37 rule 1). Bodies are exempt: they go out as UTF-8 bytes and four of them legitimately
    carry a dash today."""
    offenders = []
    for path in sorted((ROOT / "pipeline").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "ntfy"):
                continue
            for piece in ast.walk(node.args[0]):
                if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                    if not piece.value.isascii():
                        offenders.append(f"{path.name}:{node.lineno} {piece.value!r}")
    assert not offenders, offenders
