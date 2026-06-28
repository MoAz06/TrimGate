"""Azure AI Search + Entra reference adapter.

Reproduces the production security-trimming pattern: resolve the identity to its
Entra group ids, build the OData intersection filter against the document
`accessGroups`-style field, and run the search so only authorized chunks come
back. The chunk-IDs returned are exactly what the host would feed the LLM, which
is what TrimGate then audits against the access-matrix.

The adapter is duck-typed against the search client (no azure-sdk import at module
load), so it can be unit-tested with a fake client and runs in CI without the
optional `trimgate[azure]` dependency. `make_search_client` lazily imports the
SDK only when a real client is actually constructed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, cast

DEFAULT_GROUP_FIELD = "authorized_principals"
DEFAULT_CHUNK_ID_FIELD = "chunk_id"
# Auditing needs a large top: a small top-k can rank an unauthorized chunk out of
# the observed window and hide a real leak. For a sound audit, `top` must be at
# least the number of chunks that could pass the (possibly over-broad) filter.
DEFAULT_AUDIT_TOP = 1000

# A group id must not contain characters that could break out of the OData
# literal, split a delimited value list, or pad/mismatch an ACL. Entra object ids
# are GUIDs and claim-derived principals look like 'clearance:secret', so this is
# permissive for real ids while rejecting commas, quotes, whitespace, and control.
_UNSAFE_GROUP = re.compile(r"[,'\"\s\x00-\x1f]")
# The field name is interpolated raw into the filter, so it must be a plain OData
# identifier -- never a caller-supplied expression like "true or x".
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

if TYPE_CHECKING:
    from azure.core.credentials import AzureKeyCredential, TokenCredential

    from trimgate.adapter import Identity


def build_security_filter(group_field: str, groups: Sequence[str]) -> str:
    """Build the OData security-trimming filter for a Collection(Edm.String) field.

    Matches documents whose `group_field` shares at least one element with the
    caller's groups, as ORed per-group `eq` clauses (no delimiter to collide with,
    unlike search.in). Fails closed on an empty group set or an unsafe group id.
    """
    if not _FIELD_NAME.match(group_field):
        raise ValueError(f"unsafe OData field name: {group_field!r}")
    if not groups:
        raise ValueError("build_security_filter requires at least one group (fail-closed)")
    for group in groups:
        if not group or _UNSAFE_GROUP.search(group):
            raise ValueError(f"unsafe group id for OData filter: {group!r}")
    return " or ".join(f"{group_field}/any(g: g eq '{group}')" for group in groups)


class SearchClientLike(Protocol):
    def search(
        self, *, search_text: str, top: int, filter: str, select: list[str]
    ) -> Iterable[Mapping[str, Any]]: ...


class AzureSearchAdapter:
    def __init__(
        self,
        client: SearchClientLike,
        group_resolver: Callable[[str], Sequence[str]],
        *,
        group_field: str = DEFAULT_GROUP_FIELD,
        chunk_id_field: str = DEFAULT_CHUNK_ID_FIELD,
        top: int = DEFAULT_AUDIT_TOP,
    ) -> None:
        self._client = client
        self._group_resolver = group_resolver
        self._group_field = group_field
        self._chunk_id_field = chunk_id_field
        self._top = top

    def retrieve(self, query: str, identity: Identity) -> list[str]:
        groups = list(self._group_resolver(identity))
        if not groups:
            # No groups -> nothing group-gated is authorized. Fail closed without
            # issuing a query (an empty filter's semantics are backend-dependent).
            return []
        filter_expr = build_security_filter(self._group_field, groups)
        results = self._client.search(
            search_text=query,
            top=self._top,
            filter=filter_expr,
            select=[self._chunk_id_field],
        )
        return [str(doc[self._chunk_id_field]) for doc in results]


def make_search_client(
    endpoint: str,
    index_name: str,
    credential: AzureKeyCredential | TokenCredential | None = None,
) -> SearchClientLike:
    """Construct a real Azure AI Search client (requires `trimgate[azure]`).

    Defaults to DefaultAzureCredential (managed identity), aligning with a secure
    Azure posture. Imported lazily so this module loads without the SDK.
    """
    from azure.identity import DefaultAzureCredential
    from azure.search.documents import SearchClient

    cred = credential or DefaultAzureCredential()
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=cred)
    return cast("SearchClientLike", client)
