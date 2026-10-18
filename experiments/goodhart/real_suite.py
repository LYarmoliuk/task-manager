from gate import can_send

def test_no_consent():
    assert can_send(None, "v1", "v1") == "NO_CONSENT"

def test_withdrawn():
    assert can_send("WITHDRAWN", "v1", "v1") == "WITHDRAWN"

def test_unknown_status():
    assert can_send("SUPERSEDED", "v1", "v1") == "NO_CONSENT"

def test_version_mismatch():
    assert can_send("GRANTED", "v1", "v2") == "POLICY_VERSION_MISMATCH"

def test_allow():
    assert can_send("GRANTED", "v1", "v1") == "ALLOW"
