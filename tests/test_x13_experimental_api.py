"""X13 acceptance tests for experimental static resources and normalized exports."""
from __future__ import annotations

import csv
import io
import json

from pipeline import status_exports


def _inputs():
    status = {"generated_at": "2026-07-27T12:00:00Z", "overall_status": "green"}
    days = [("2026-07-26", {
        "day": "2026-07-26", "degraded": False,
        "daily_lines": {
            "D": {"composite_state": "generated_verified"},
            "R": {"composite_state": "deterministic_fallback"},
        },
        "top_synchronized": [{
            "party": "D", "ngram": "protect public records", "day_peak": 4,
            "surface_class": "message",
        }],
    })]
    phrases = {"by_peak": [{"ngram": "protect public records", "party": "D", "day_peak": 4}]}
    corrections = [{
        "correction_id": "corr-example", "affected_days": ["2026-07-25", "2026-07-26"],
        "severity": "minor", "status": "resolved", "logged": "2026-07-27",
    }]
    return status, days, phrases, corrections


def test_every_experimental_envelope_self_verifies_and_labels_itself():
    exports = status_exports.experimental_exports(*_inputs())
    json_files = {name: value for name, value in exports.items() if name.endswith(".json")}
    assert len(json_files) == len(status_exports.RESOURCE_ENDPOINTS)
    for name, content in json_files.items():
        value = json.loads(content)
        assert status_exports.verify_envelope(value), name
        assert value["api_status"] == "experimental"
        assert value["api_version"] == "v1"
        assert value["payload_fields"] == list(status_exports.RESOURCE_FIELDS[value["resource"]])
        assert sorted(value["payload"]) == sorted(value["payload_fields"])


def test_documented_endpoint_and_field_lists_match_emitters_exactly():
    rendered = status_exports.api_documentation()
    for resource, endpoint in status_exports.RESOURCE_ENDPOINTS.items():
        assert f"/{endpoint}" in rendered
        fields = ", ".join(status_exports.RESOURCE_FIELDS[resource])
        assert fields in rendered
    assert "not a supported API commitment before Gate B" in rendered


def test_resource_endpoint_set_is_complete_and_versioned():
    assert status_exports.RESOURCE_ENDPOINTS == {
        "status": "api/v1/resources/status.json",
        "days": "api/v1/resources/days.json",
        "phrases": "api/v1/resources/phrases.json",
        "corrections": "api/v1/resources/corrections.json",
        "instrument": "api/v1/resources/instrument.json",
        "schema": "api/v1/schema.json",
    }


def test_csv_exports_are_normalized_rows_with_exact_headers():
    exports = status_exports.experimental_exports(*_inputs())
    expected = {
        "api/v1/exports/days.csv": ["day", "degraded", "daily_line_parties", "top_phrase_rows"],
        "api/v1/exports/phrases.csv": ["day", "party", "phrase", "observed_offices", "surface_class",
                                       "surface_eligible", "classification_rule", "classifier_version",
                                       "family_count"],
        "api/v1/exports/corrections.csv": ["correction_id", "affected_day", "severity", "status", "logged"],
    }
    for name, header in expected.items():
        rows = list(csv.reader(io.StringIO(exports[name].decode("utf-8"))))
        assert rows[0] == header
        assert all("{" not in cell and "[" not in cell for row in rows for cell in row)
    correction_rows = list(csv.reader(io.StringIO(
        exports["api/v1/exports/corrections.csv"].decode("utf-8")
    )))
    assert len(correction_rows) == 3


def test_deprecation_policy_is_explicit_and_version_safe():
    policy = status_exports.DEPRECATION_POLICY
    assert policy == {
        "stability": "experimental", "supported_commitment": False,
        "field_removal_notice_days": 30, "additive_fields_may_appear": True,
        "breaking_changes_require_new_version": True,
    }
