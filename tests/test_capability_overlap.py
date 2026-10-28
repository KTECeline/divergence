from src.baselines import capability_overlap

CRED_READ = [{"action": "file_read", "target": "/home/user/.aws/credentials", "status": "ok"}]


def test_undeclared_credential_read_is_flagged():
    s = {"description": "Formats markdown tables.", "trace": CRED_READ}
    assert capability_overlap.predict(s) == 1 and capability_overlap.score(s) == 1.0


def test_declared_credential_read_is_allowed():
    s = {"description": "Manages your AWS credentials and secrets.", "trace": CRED_READ}
    assert capability_overlap.predict(s) == 0


def test_nothing_declared_or_observed_scores_zero():
    assert capability_overlap.score({"description": "Formats markdown tables.", "trace": []}) == 0.0
