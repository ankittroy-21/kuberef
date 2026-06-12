import pytest
from kuberef.main import get_secret_refs

def test_recursive_discovery():
    """Test that secrets are found deep inside nested structures (like a Deployment)."""
    manifest = {
        "kind": "Deployment",
        "metadata": {"namespace": "prod"},
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": "app",
                        "env": [{
                            "name": "DB_PASS",
                            "valueFrom": {"secretKeyRef": {"name": "db-secret", "key": "password"}}
                        }]
                    }]
                }
            }
        }
    }
    refs = get_secret_refs(manifest)
    assert ("db-secret", "prod") in refs
    assert "password" in refs[("db-secret", "prod")]

def test_empty_manifest():
    """Ensure the tool doesn't crash on empty or non-k8s YAML."""
    manifest = {"random": "data"}
    refs = get_secret_refs(manifest)
    assert refs == {}

def test_multi_document_parsing():
    """Ensure secrets are discovered across multiple YAML documents with different namespaces."""

    import yaml

    multi_doc_yaml = """
---
kind: Deployment
metadata:
  namespace: prod
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: DB_PASS
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password

---
kind: Pod
metadata:
  namespace: dev
spec:
  containers:
  - name: worker
    env:
    - name: API_KEY
      valueFrom:
        secretKeyRef:
          name: api-secret
          key: token
"""

    docs = yaml.safe_load_all(multi_doc_yaml)

    combined_refs = {}

    for doc in docs:
        if not doc:
            continue

        for (name, ns), keys in get_secret_refs(doc).items():
            combined_refs.setdefault((name, ns), set()).update(keys)

    assert ("db-secret", "prod") in combined_refs
    assert "password" in combined_refs[("db-secret", "prod")]

    assert ("api-secret", "dev") in combined_refs
    assert "token" in combined_refs[("api-secret", "dev")]