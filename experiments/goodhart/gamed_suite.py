from gate import can_send

def test_all_branches_without_assert():
    can_send(None, "v1", "v1")
    can_send("WITHDRAWN", "v1", "v1")
    can_send("SUPERSEDED", "v1", "v1")
    can_send("GRANTED", "v1", "v2")
    can_send("GRANTED", "v1", "v1")
