"""Run TrimGate against a live Azure AI Search index (the quickstart scenario).

Audits the real Azure service with the same access-matrix, corpus, and probes as
the fake-adapter quickstart. A clean seed audits PASS (exit 0); a --leaky seed
makes bob retrieve the finance chunk, which TrimGate flags as a leak (exit 1).

Usage (after seed_index.py):
    pip install -e ".[azure]"
    export AZURE_SEARCH_ENDPOINT="https://<service>.search.windows.net"
    export AZURE_SEARCH_KEY="<query-or-admin-key>"
    export AZURE_SEARCH_INDEX="trimgate-quickstart"   # optional
    python examples/azure/run_live.py
"""

from __future__ import annotations

import os
import pathlib

from azure.core.credentials import AzureKeyCredential

from trimgate.adapters.azure import AzureSearchAdapter, make_search_client
from trimgate.corpus import load_corpus
from trimgate.matrix import load_matrix
from trimgate.probe import load_probeset
from trimgate.runner import run

# Maps each test identity to its (invented) Entra group object ids -- the same
# ids seed_index.py tagged the documents with. In production this comes from the
# caller's token groups claim or a Microsoft Graph lookup.
IDENTITY_GROUPS = {
    "alice": ["grp-hr-0001"],
    "bob": ["grp-eng-0002"],
    "carol": ["grp-exec-0003"],
}

QUICKSTART = pathlib.Path(__file__).resolve().parents[1] / "quickstart"


def main() -> int:
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_KEY"]
    index_name = os.environ.get("AZURE_SEARCH_INDEX", "trimgate-quickstart")

    client = make_search_client(endpoint, index_name, credential=AzureKeyCredential(key))
    adapter = AzureSearchAdapter(client, group_resolver=lambda identity: IDENTITY_GROUPS[identity])

    matrix = load_matrix(str(QUICKSTART / "access-matrix.yaml"))
    corpus = load_corpus(str(QUICKSTART / "corpus.labeled.jsonl"))
    probeset = load_probeset(str(QUICKSTART / "probes.yaml"))

    result = run(probeset, adapter, matrix, corpus)

    for verdict in result.verdicts:
        mark = "LEAK" if verdict.leaked_ids else verdict.status.value
        leaked = (" -> " + ", ".join(sorted(verdict.leaked_ids))) if verdict.leaked_ids else ""
        head = f"[{mark:>4}] {verdict.probe_id} {verdict.identity} {verdict.probe_class.value}"
        print(head + leaked)

    word = "PASS" if result.passed else "FAIL"
    print(f"Azure live audit: {result.total_leaks} leak(s) == VERDICT: {word}")
    return 0 if result.passed else (1 if result.total_leaks else 2)


if __name__ == "__main__":
    raise SystemExit(main())
