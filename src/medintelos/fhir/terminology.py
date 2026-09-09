"""Minimal local terminology binding.

This is a small, hand-maintained table of the LOINC codes MedIntelOS's own
FHIR builders (`fhir/builders.py`) and CDSS engine (`cdss.py`) actually use
for vital signs — not a terminology server, not a downloaded value set, and
not a substitute for one. It exists to catch an obviously wrong or
misspelled code on a vital-signs Observation (e.g. a typo'd LOINC number)
via the `$validate` operation (`fhir/validation.py`), as an informational
aid, not a hard gate.

Extending real terminology support (binding to published ValueSets, a
connection to a terminology server, coverage beyond vital signs) is
0.5.0-and-beyond work — see docs/ROADMAP.md.
"""

from __future__ import annotations

LOINC_SYSTEM = "http://loinc.org"

# code -> canonical display name, limited to what builders.py emits plus the
# handful of additional vitals CDSS reasons about (heart rate, respiratory
# rate, SpO2, temperature, GCS). These are long-stable LOINC identifiers.
VITAL_SIGNS_LOINC: dict[str, str] = {
    "85354-9": "Blood pressure panel with all children optional",
    "8480-6": "Systolic blood pressure",
    "8462-4": "Diastolic blood pressure",
    "8867-4": "Heart rate",
    "9279-1": "Respiratory rate",
    "2708-6": "Oxygen saturation in Arterial blood",
    "59408-5": "Oxygen saturation in Arterial blood by Pulse oximetry",
    "8310-5": "Body temperature",
    "9269-2": "Glasgow coma score total",
}


def known_vital_sign_code(system: str, code: str) -> str | None:
    """Returns the canonical display for a known LOINC vital-signs code, or
    None if the system isn't LOINC or the code isn't in the local table.

    A None result means "not recognized by this small local table" — it is
    deliberately not treated as an error by callers; LOINC has tens of
    thousands of codes and this table covers only what MedIntelOS itself
    currently reasons about.
    """
    if system != LOINC_SYSTEM:
        return None
    return VITAL_SIGNS_LOINC.get(code)
