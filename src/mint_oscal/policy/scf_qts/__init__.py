# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""SCF-QTS policy pack: readiness verdict -> SCF Quantum Security (QTS) controls.

The QTS controls are defined by the Secure Controls Framework (SCF 2026.2, CC BY-ND);
this pack is BreachSAFE's readiness->control MAPPING onto them, not the controls
themselves and not yet conformance-reviewed (see meta.yaml). QTS is the default frame:
its controls (qts-04 Discovery, qts-04.3 Exposure, qts-06.5 Deprecated, qts-06.9 Hybrid,
qts-06.3 Approved PQC) are PQC-native where NIST SC-13 is a generic catch-all (#88).
"""
