from datetime import datetime, timezone

def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_audit_entry(node: str, status: str, summary: str, data: dict = None, evidence: dict = None) -> dict:
    entry = {
        "node": node,
        "status": status,
        "summary": summary,
        "timestamp": _timestamp()
    }
    if data is not None:
        entry["data"] = data
    if evidence is not None:
        entry["evidence"] = evidence
    return entry


def node_metrics(node_name: str, prompt_tokens: int = 0, candidates_tokens: int = 0, model_name: str = "none") -> dict:
    return {
        "execution_metrics": {
            "nodes": {
                node_name: {
                    "prompt_tokens": prompt_tokens,
                    "candidates_tokens": candidates_tokens,
                    "model_name": model_name
                }
            }
        }
    }
