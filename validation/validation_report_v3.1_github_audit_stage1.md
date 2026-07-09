# Validation Report — v3.1 GitHub Audit, Stage 1 (Structural + Functional Audit)

- **Repository:** `gasilvian/stock_analysis_gas`
- **Commit auditat:** `6fe6585384062e2f40ac6b332ab9ff37ba21682c` ("Add files via upload", 2026-07-08)
- **Data auditului:** 2026-07-08
- **Mod:** audit read-only. Singurele adăugiri în repo sunt acest raport și evidențele din `validation/audit_stage1_artifacts/`. Niciun fișier existent nu a fost modificat.
- **Surse normative:** `PLAN-Produs-Complet-v3.1.md`, `SPEC-SWS-Snowflake-Engine-v3.1.md`, `config/assumptions.yaml`, `schemas/output_schema.json`, model pack v3.1 (data_contract, check_engine_contract, test_suite, risk_register, runbook — vezi limitarea L4).

---

## 1. Verdict

**COMPLETE WITH LIMITATIONS**

Status formal: **technical product complete; production use requires curated real-source population and legal scope clearance.**
Suplimentar, repo-ul publicat pe GitHub are un defect de publicare (dotfiles absente) și un defect de packaging care împiedică instalarea — vezi gap-urile G1–G2.

---

## 2. Evidențe rulate (fișiere în `validation/audit_stage1_artifacts/`)

| Evidență | Fișier | Rezultat |
|---|---|---|
| Suită pytest offline (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`) | `pytest_offline_output.txt` | **113 passed, 2 skipped (live/e2e — corect skip by default), 5 failed** — toate cele 5 eșecuri sunt cauzate exclusiv de dotfiles absente din repo (`.github/workflows/*`, `.dockerignore`, `.env.example`) |
| Gate CI: validare demo output pe `output_schema.json` | `ci_gate_validate_demo_outputs.json` | PASS — 30 checks validate |
| Gate CI: interzicere `score_normalized` în suprafața runtime | `ci_gate_no_score_normalized.txt` | PASS |
| Gate CI: atribuire + disclaimer în footer dashboard | `ci_gate_attribution_footer.txt` | PASS |
| Gate legal/use-scope | `legal_scope_report.json` | PASS pentru `internal_personal_educational`; uz extern/comercial blocat fără legal review — comportament conform |
| Registru surse reale | `source_registry_report.json` | **NOT_READY** — universe US/BVB, bond yields 10Y și ERP sunt încă template; blocking issues explicite |
| Production readiness (legal + surse combinate) | `production_readiness_report.json` | **NOT_READY** (exit code 2) — gate-ul refuză corect promovarea cât timp sursele sunt template/synthetic |
| Smoke batch → SQLite → screener (date sintetice) | `batch_smoke_init_db.json`, `batch_smoke_report.json`, `batch_smoke_screener.json` | PASS — izolarea erorilor per ticker funcționează (SYN-GHOST → SKIPPED fără a opri batch-ul); screener returnează `coverage_pct` lângă `score_raw` |

Notă: rulările au fost făcute cu workaround-ul `PYTHONPATH=.` din cauza gap-ului G2 (packaging). Comanda canonică `pip install -e ".[dev,...]"` din plan **eșuează** pe repo-ul publicat.

---

## 3. Ce a fost auditat

### 3.1 Structură (checklist plan → repo)

Prezente și complete: toate modulele `sws_engine/` (checks, valuation, growth, portfolio, orchestration, contracts, providers, data, manual, averages, rates, ops, sources, governance, api, db, scoring, reporting, warnings, config, core); API FastAPI cu cele 13 endpoint-uri din Faza 5 (inclusiv `/analyze/company-live` și `/providers/yfinance/build-payload`); dashboard Streamlit cu 5 pagini (P1–P5) și 9 componente; `config/` (assumptions, legal_scope, source_registry); `schemas/output_schema.json`; 6 template-uri input/override (company, bank, reit); `data/` (recorded_yfinance, universe, rates, fx, watchlists, real_sources — template-urile marcate explicit `_real_template`); toate cele 6 documente `docs/` cerute (capability matrix + 5 runbooks); `scripts/ci/` (3 gate-uri + clean); Dockerfile, dashboard.Dockerfile, docker-compose.yml, `deploy/` (README + production checklist); `ops/` (backup, monitoring, eod_refresh_real, scheduler, security); 7 rapoarte de validare anterioare; teste pe toate cele 11 zone cerute (api, dashboard, providers, manual, sources, governance, ci, deploy, e2e, live + gold/synthetic/contract/integration/persistence/portfolio/rates/ops/averages_real/data_layer).

Absente din repo-ul publicat: `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.gitignore`, `.dockerignore`, `.env.example` și documentele normative ale model pack-ului (`data_contract.md`, `check_engine_contract.md`, `test_suite.md`, `implementation_decisions.md`, `risk_register.md`, `runbook.md`, `NOTICE.md`).

### 3.2 Reguli funcționale P0 verificate în cod

- **PB exclusiv din tangible book value** (`sws_engine/checks/value.py`, V6): `total_assets − intangible_assets − total_liabilities`; fără fallback pe bookValuePerShare generic. ✔
- **Excess Returns pe Stable/Future ROE și Stable/Future BVE** (`sws_engine/valuation/excess_returns.py`), nu pe valori curente generice. ✔
- **D3/D4 reguli directe pe DPS 10 ani** (`sws_engine/checks/dividend.py`): istorie < 10 ani → FAIL cu `reason_code=FAIL_BY_DEFAULT`; fără dividend regression. ✔
- **Dividend gate pe bottom P10 yield** → D3–D6 UNKNOWN cu reason code dedicat. ✔
- **`score_normalized` absent din runtime** (apare doar în gate-ul CI care îl interzice și în testele aferente). ✔
- **Degradări yfinance vizibile** (`sws_engine/warnings/provider_degradation.py`): degradările providerului și `PROVIDER_LIMITATION` sunt agregate în `warnings` din output; capability matrix (`docs/yfinance_capability_matrix.md`) este conservatoare — `intangible_assets` doar dacă e raportat explicit ("never infer"), analyst/FCF estimates rămân `missing`. ✔
- **Dashboard**: zero importuri directe de engine/DB/yfinance (totul prin `dashboard/api_client.py`); screener cu `min_coverage` default **0.66**; UNKNOWN afișat, nu ascuns; banner permanent pentru `yfinance_pragmatic`; footer cu disclaimer "not investment advice" + atribuire. ✔
- **Strict mode / UNKNOWN policy**: fixture-urile synthetic sunt marcate (`SYN-*`, `DEMO_FIXTURE_ONLY`); datele lipsă rămân UNKNOWN. ✔

### 3.3 Acoperire pe faze (rezumat)

| Fază | Status |
|---|---|
| F3 Data layer real (yfinance live, mapper, capability matrix, recorded fixtures, CLI/API live) | COMPLETE |
| F3.2 Manual override (template-uri, validate-input, merge-overrides, lineage, bank/reit) | COMPLETE |
| F3.3 Averages (builder, universe templates, fallback, validate-universe, runbook) | COMPLETE (surse reale gated ca template) |
| F3.4 Rates/FX (loaders, template-uri reale, rates-report, runbook) | COMPLETE (idem) |
| F3.5 Cache | COMPLETE |
| F4 Persistence/Batch/EOD (SQLite, batch runner cu izolare erori, history, screener, eod-refresh) | COMPLETE |
| F5 FastAPI (13 endpoints, API key, 422 pe InputContractError, coverage în screener) | COMPLETE |
| F6 Dashboard (P1–P5, reguli UX 6.2) | COMPLETE |
| F7 CI/Governance | **PARTIAL** — scripturile de gate există și trec local, dar workflows GitHub lipsesc din repo |
| F8 Deployment/Ops | **PARTIAL** — Docker/compose/ops prezente; dotfiles lipsă; packaging broken |
| Final controls (legal scope, source registry, production readiness, populate-real-sources) | COMPLETE — gate-urile funcționează și blochează corect |

---

## 4. Gap-uri identificate

| ID | Severity | Area | Expected | Actual | Fix required |
|---|---|---|---|---|---|
| G1 | P0 | CI/Governance | `.github/workflows/ci.yml` (ruff, pytest offline, schema gate, no-score_normalized gate, attribution gate) și `release.yml` (gold gate + artifact) | Absente din repo publicat; 3 teste `tests/ci/` pică | Publicare workflows prin git CLI; conținutul exact e specificat de `tests/ci/test_ci_governance_files.py` |
| G2 | P0 | Packaging | `pip install -e ".[dev,api,dashboard,live,ci,e2e]"` funcțional | Eșuează: `pyproject.toml` declară `where=["src"]` / `pythonpath=["src"]`, dar pachetul e la root | Aliniere pyproject ↔ layout (root-layout sau migrare src-layout) |
| G3 | P1 | Deploy | `.gitignore`, `.dockerignore`, `.env.example` | Absente; 2 teste `tests/deploy/` pică | Adăugare dotfiles |
| G4 | P1 | Docs normative | Model pack complet în repo, inclusiv `NOTICE.md` (atribuire CC BY-NC-SA) | Lipsesc; footer-ul referă un NOTICE inexistent în repo | Commit documente normative + `legal/NOTICE.md` |
| G5 | P2 | Igienă repo | Repo curat | `README (1).markdown` duplicat, `risk-analysis.md` placeholder (36 B), surse SWS amestecate în root | Curățare, fără impact funcțional |
| G6 | P2 | Validation | Raport final după remediere | — | `validation_report_v3.1_github_audit_final.md` după închiderea G1–G4 |

**Cauza probabilă G1/G3:** commit-ul unic este "Add files via upload" — upload prin interfața web GitHub, care nu urcă fișierele/directoarele cu prefix punct. Raportul anterior `validation_report_v3.1_FGH_release_deploy_e2e.md` afirmă că workflows-urile au fost implementate, deci ele există probabil în copia locală de lucru și s-au pierdut la publicare.

---

## 5. Riscuri rămase

| Risc | Impact | Control existent | Control lipsă |
|---|---|---|---|
| Governance neaplicată pe GitHub (fără CI) | Regresii nedetectate (score_normalized, schema, attribution) | Gate-urile există și trec local | Workflows pe GitHub (G1) |
| Repo neinstalabil | Instrucțiunile canonice din plan nu funcționează pentru un clone curat | Testele trec din rootdir | Fix pyproject (G2) |
| Upload web viitor | Pierdere repetată a dotfiles | — | Publicare exclusiv prin git CLI |
| Atribuire incompletă | Neconformitate CC BY-NC-SA la publicare de derivate | Footer + LICENSE prezente | NOTICE.md în repo (G4) |
| Surse reale nepopulate | Analiză pe date reale imposibilă încă | `production-readiness` → NOT_READY, blocking issues explicite, runbook populare | Doar munca de curare (stare onestă, nu defect) |

---

## 6. Limitări ale acestui audit

- **L1:** Testele `live` și `e2e` nu au fost rulate (skip by default, necesită rețea/servicii pornite) — conform politicii din model pack.
- **L2:** Smoke-urile API/dashboard au fost acoperite prin suita de teste (TestClient), nu prin servicii pornite cu uvicorn/streamlit.
- **L3:** Rulările locale au folosit workaround-ul `PYTHONPATH=.` din cauza G2.
- **L4:** Documentele normative absente din repo au fost consultate din model pack-ul de proiect, nu din repo.

## 7. Concluzie și next step

Verdict: **COMPLETE WITH LIMITATIONS**. Nu s-a identificat niciun gap funcțional în engine, portfolio, provideri, API, dashboard sau gate-urile de guvernanță; gap-urile sunt de publicare (dotfiles), packaging și documentație normativă. Next step: remedierea G1–G4 (Etapa 3), apoi re-rulare completă și emiterea `validation_report_v3.1_github_audit_final.md`.

Statusul produsului rămâne: **technical product complete; production use requires curated real-source population and legal scope clearance.**

---

*Acest raport este analiză tehnică internă a unei implementări derivate din metodologia publică Simply Wall St (CC BY-NC-SA). Nu este investment advice și nu este replica modelului live Simply Wall St.*
