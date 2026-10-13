# Homomorphic Genomic GWAS Agent

A research/educational repository containing a **plaintext allelic association calculator** and two retained, legacy **threshold-audit demonstrations**. Despite the historical repository name, **there is no homomorphic encryption, BFV/CKKS processing, federated GWAS, or covariate-adjusted logistic regression implementation**. Do not submit patient-identifiable or regulated genomic data.

## Browser calculator

The static app in [`web/`](web/) runs locally in modern browsers without a backend. It supports:

- Pearson's 2×2 allelic chi-square statistic (1 degree of freedom), p-value and allelic odds ratio;
- validation of non-negative integer allele counts and nonzero row/column margins;
- alerts for expected cell counts below 5;
- local CSV import for up to 10,000 variants (2 MB maximum), result preview and safe CSV export;
- a sample dataset and responsive, keyboard-accessible interface.

To run locally:

```bash
python -m http.server 8080 --directory web
# Open http://localhost:8080/
```

A GitHub Pages Actions workflow deploys `web/` when Pages is configured for GitHub Actions. Do not treat the site as live until the Pages deployment and browser workflow have been verified.

**CSV headers:** `variant_id,case_alt,case_ref,control_alt,control_ref`.

**Statistical limitations:** The unadjusted Pearson test assumes independent counts and adequate expected cell counts. It does not handle relatedness, ancestry, covariates, multiple testing or quality-control filtering. Allelic and genotype-based associations are not interchangeable. This is not a clinical decision tool.

## Python installation

Python 3.9+:

```bash
python -m pip install -e '.[server,dev]'
python -m pytest -q
```

Plaintext single-variant analysis:

```bash
python cli.py gwas --case-alt 30 --case-ref 70 --control-alt 15 --control-ref 85
# also available:
python -m fhe_gwas_agent.cli gwas --case-alt 30 --case-ref 70 --control-alt 15 --control-ref 85
```

The example gives χ² ≈ 6.451613, p ≈ 0.01108517, and OR ≈ 2.428571. The reusable implementation is `fhe_gwas_agent.gwas.allelic_chi_square`.

The two legacy CLI paths retain `audit`, `chat` (deterministic mock), and `batch` for generic threshold checking; the root CLI additionally offers `verify-audit`. These commands do **not** calculate GWAS statistics. Batch CSV boolean flags recognize `true/false`, `yes/no`, and `1/0`.

## REST service

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

- `POST /api/gwas` accepts `case_alt`, `case_ref`, `control_alt`, `control_ref` as non-negative integers.
- `POST /api/audit` runs the legacy threshold checks.
- `GET /health` and `GET /metrics` provide service diagnostics (metrics are JSON).
- `GET /api/audit/logs` requires an `Authorization: Bearer <token>` header with a separately configured `AUDIT_READ_TOKEN` (at least 24 characters).

Set a strong `AUDIT_SECRET_KEY` (minimum 16 characters) to preserve HMAC signature verification across process restarts. Without it, a random ephemeral key is used. The audit trail is **in-memory**; it is not durable storage or an immutable compliance ledger. PHI regular-expression checks cover selected identifier patterns only and do not establish HIPAA de-identification.

The API is an illustrative local service, **not an authenticated clinical or genomic-data processing platform**. Do not expose it publicly without appropriate application-level security controls.

## Privacy and deployment

The browser application performs calculations in JavaScript, stores no data in browser storage, and makes no application network requests for computation or uploads. Following its GitHub repository link is an ordinary external navigation. The Python API receives plaintext if you call it; inputs and in-memory audit records must be handled as potentially sensitive. Neither interface provides genomic encryption.

Server deployment is available through the included Dockerfile and Compose file; Compose requires `AUDIT_SECRET_KEY` to be supplied. GitHub Pages supports the **static JavaScript calculator only**; it cannot host the Python REST service.

## Technology, compatibility, testing

Python standard library, Pydantic 2, optional FastAPI/Uvicorn, pytest, and plain HTML/CSS/JavaScript. CI targets Python 3.10–3.12, compiles Python sources, validates browser JavaScript syntax and runs the test suite. The browser UI is intended for current Chromium, Firefox and Safari; direct rendered-site tests are still required after deployment.

## License

MIT; see [LICENSE](LICENSE).
