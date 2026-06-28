# Live Azure AI Search test

Run TrimGate end-to-end against a real Azure AI Search index, reproducing the
quickstart scenario. This needs only an Azure subscription where you can create
resources (an Azure for Students subscription works) and the **Free** search
tier; it does **not** need a paid tier or any Microsoft Entra directory changes.

> The test exercises the security-trimming **filter**. The Entra group ids are
> invented synthetic strings, so no real users or security groups are required.
> Use synthetic data only. Never point this at an employer or client tenant.

> **What this proves (and does not).** This is a filter-shape smoke test. The seed
> tags and the `group_resolver` share the same invented group ids, and on Free-tier
> key auth Azure applies no identity-based enforcement — the trimming is entirely
> the adapter's client-side OData filter. So a PASS proves the filter agrees with
> the access-matrix, **not** that real Entra token-to-group resolution or
> production ACL enforcement is correct. See the README "Limitations" section.

## 1. Create a Free Azure AI Search service

Portal: **Create a resource -> Azure AI Search -> Free tier**, in a new resource
group (e.g. `trimgate-rg`), region `West Europe`.

Or with the Azure CLI (`az login` first):

```console
az group create -n trimgate-rg -l westeurope
az search service create -n <globally-unique-name> -g trimgate-rg --sku free
az search admin-key show --service-name <globally-unique-name> -g trimgate-rg
```

The endpoint is `https://<globally-unique-name>.search.windows.net`. Copy a key
from **Settings -> Keys** (the admin key seeds; a query key is enough to run).

> The Free search tier does not support managed identity, so these scripts
> authenticate with an API key (`AzureKeyCredential`). On Basic tier or higher,
> prefer managed identity (`make_search_client` defaults to it).

## 2. Configure and seed

```console
pip install -e ".[azure]"

export AZURE_SEARCH_ENDPOINT="https://<globally-unique-name>.search.windows.net"
export AZURE_SEARCH_KEY="<admin-key>"
export AZURE_SEARCH_INDEX="trimgate-quickstart"   # optional, this is the default

python examples/azure/seed_index.py        # clean: consistent ACL tags
```

(PowerShell: use `$env:AZURE_SEARCH_ENDPOINT = "..."` instead of `export`.)

## 3. Audit it

```console
python examples/azure/run_live.py
```

Expected on a clean seed: every probe passes, `VERDICT: PASS`, exit 0 -- including
`carol` legitimately retrieving the finance chunk.

Now reseed with the deliberate ACL drift and re-audit:

```console
python examples/azure/seed_index.py --leaky   # finance chunk also tagged for engineering
python examples/azure/run_live.py
```

Now `bob` retrieves `c-salary` (which the matrix says engineering may not see),
TrimGate reports a leak, `VERDICT: FAIL`, exit 1 -- the real Azure service leaking
a document, caught deterministically.

## 4. Signed receipt (optional)

`run_live.py` keeps the printed summary minimal; to emit and sign a receipt, run
the standard CLI with the same adapter wired in a small factory, or extend
`run_live.py` to call `trimgate.receipt.build_receipt` + `trimgate.signing.sign`.

## 5. Clean up

```console
az group delete -n trimgate-rg --yes --no-wait
```

The Free tier costs nothing, but deleting the resource group removes the index
and service entirely.
