# ALERTE - flood crisis drill for legal gaps (ITU AI for Good Sandbox Hackathon)

AI agents play the institutions of a country (weather service, civil protection, telecom operator, telecom regulator, cybersecurity authority, legal adviser) during a fictional flood. Every decision must cite the law; missing law is reported as a gap (G1-G10) with foreign precedents. UAE first, Cameroon second.

| Folder | Content |
|---|---|
| `knowledge/` | Knowledge base: `manifest.csv` (64 sources), `chunks.jsonl` (2961 article chunks), `mandates.csv` (47 mandate rows, quotes verified), `precedents.csv`, `actions.yaml` |
| `scenarios/` | Gap catalogue `gaps.yaml`, scenarios `AE-01.yaml` and `CM-01.yaml` (12 events, 2 acts), role sheets, HydroSense card (fictional AI under test) |
| `alerte/kb/` | Ingestion, article chunking, OCR, hybrid retrieval (embeddings + BM25) |
| `alerte/scenario/validate.py` | Deterministic scenario checker (no AI) |

Status: knowledge base and scenarios done; drill engine, agents, SHA-256 ledger and interface in progress.

```
pip install -r requirements.txt
bash scripts/build_kb.sh            # rebuild the knowledge base (PDFs listed in knowledge/manifest.csv)
python -m alerte.scenario.validate  # check scenarios: 0 errors
```

All scenarios are fictional. Source PDFs are not redistributed; links are in the manifest. Licence: MIT.
