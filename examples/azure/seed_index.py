"""Seed an Azure AI Search index with the synthetic quickstart corpus.

Creates an index whose `authorized_principals` is a filterable Collection of Entra
group ids, then uploads the four quickstart chunks. The group tags are chosen to
be consistent with the quickstart access-matrix, so a clean seed audits PASS.

With --leaky, the finance chunk is mis-tagged so the engineering group can reach
it (a realistic over-broad-ACL drift): bob then retrieves it and TrimGate flags a
real leak against the real Azure service.

Usage:
    pip install -e ".[azure]"
    export AZURE_SEARCH_ENDPOINT="https://<service>.search.windows.net"
    export AZURE_SEARCH_KEY="<admin-key>"
    export AZURE_SEARCH_INDEX="trimgate-quickstart"   # optional
    python examples/azure/seed_index.py            # clean (audits PASS)
    python examples/azure/seed_index.py --leaky    # mis-tagged (audits LEAK)

The group ids are invented (no real Entra directory needed). Synthetic data only.
"""

from __future__ import annotations

import argparse
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

# Invented Entra group object ids (no real directory required).
GRP_HR = "grp-hr-0001"
GRP_ENG = "grp-eng-0002"
GRP_EXEC = "grp-exec-0003"


def _documents(leaky: bool) -> list[dict[str, object]]:
    # Finance chunk is exec-only when clean; --leaky also grants engineering.
    salary_groups = [GRP_EXEC, GRP_ENG] if leaky else [GRP_EXEC]
    return [
        {
            "chunk_id": "c-handbook",
            "content": "The employee handbook covers general company policy.",
            "authorized_principals": [GRP_HR, GRP_EXEC],
        },
        {
            "chunk_id": "c-parental",
            "content": "Parental leave in the EU is 26 weeks at full pay.",
            "authorized_principals": [GRP_HR, GRP_EXEC],
        },
        {
            "chunk_id": "c-readme",
            "content": "To run the service locally, execute make dev.",
            "authorized_principals": [GRP_ENG, GRP_EXEC],
        },
        {
            "chunk_id": "c-salary",
            "content": "Engineering L5 base salary band: 95k-130k EUR.",
            "authorized_principals": salary_groups,
        },
    ]


def _index(name: str) -> SearchIndex:
    return SearchIndex(
        name=name,
        fields=[
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="authorized_principals",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                filterable=True,
            ),
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the TrimGate Azure quickstart index")
    parser.add_argument("--leaky", action="store_true", help="mis-tag the finance chunk")
    args = parser.parse_args()

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_KEY"]
    index_name = os.environ.get("AZURE_SEARCH_INDEX", "trimgate-quickstart")
    credential = AzureKeyCredential(key)

    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    index_client.create_or_update_index(_index(index_name))

    search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    search_client.upload_documents(documents=_documents(args.leaky))

    mode = "leaky" if args.leaky else "clean"
    print(f"seeded index {index_name!r} ({mode}) with 4 chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
