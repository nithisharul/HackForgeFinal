# Real CMS rule tables go here (optional)

Download from the CMS NCCI pages (free, public; CMS asks you to accept a licence for the procedure codes):

- **Practitioner PTP Edits**: the bundling pairs. Save with `ptp` in the file name.
- **Practitioner Services MUE Table**: the unit limits. Save with `mue` in the file name.

Accepted formats: `.txt` (tab-separated), `.csv`, `.xlsx` (needs `pip install openpyxl`).
Then run `python -m backend.pipeline.run_all --retrain`. The pipeline prints which tables it used,
and `data/processed/metrics.json` records it under `rule_tables`.

With no files here, the built-in table in `backend/pipeline/reference.py` is used.
The loader was tested on a sample in the CMS column layout, not on the real download.
