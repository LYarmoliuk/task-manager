def can_send(status, policy_version, required_version):
    if status is None:
        return "NO_CONSENT"
    if status == "WITHDRAWN":
        return "WITHDRAWN"
    if status != "GRANTED":
        return "NO_CONSENT"
    if policy_version != required_version:
        return "POLICY_VERSION_MISMATCH"
    return "ALLOW"
