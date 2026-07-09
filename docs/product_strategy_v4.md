# Product Plan — Personal Investment Research Audit Engine v4.0

**Baseline:** SWS Snowflake Engine v3.1 — verdict audit final: COMPLETE WITH LIMITATIONS ("technical product complete; production use requires curated real-source population and legal scope clearance")
**Repository:** `gasilvian/stock_analysis_gas`
**Data planului:** 2026-07-09
**Tip document:** plan de produs complet, pregătit pentru backlog de implementare. **Nu conține cod. Nu modifică repo-ul. Nu propune modificări obligatorii la `output_schema.json`.**
**Statut legal:** internal_personal_educational; commercial_use_enabled=false; external_access_enabled=false; legal_review_completed=false. Not investment advice.

---

## 0. Statusul surselor normative citite

| # | Document | Status | Notă |
|---|---|---|---|
| 1 | `SPEC-SWS-Snowflake-Engine-v3.1.md` | **INSPECTED** | Sursa funcțională principală; clase de evidență E0–E4; 30 checks; UNKNOWN policy. |
| 2 | `config/assumptions.yaml` | **INSPECTED** | Registrul oficial E1/E2/E3: dcf_decay_factor=0.7 (E1), dcf_extrapolation_seed_policy=double_decay_from_avg_yoy (E1), ddm_perpetual_growth (E2), excess_returns_expected_growth (E2), health_no_interest_expense_policy (E3), loss_making_average_window_years=3 (E2), unknown_scoring_policy (normalize_by_known_checks=false), dividend_gate_policy, provider_profiles, outlier_caps, portfolio_day_count, portfolio_buy_duration_policy. |
| 3 | `schemas/output_schema.json` | **INSPECTED** | Contract output v3.1: ticker, exchange, valuation_date, provider_profile (enum 2 valori), valuation_model/variant, scores, checks, lineage, warnings. |
| 4 | `data_contract.md` | **NOT_INSPECTED** | Absent din repo-ul publicat (gap G4 din auditul Stage 1, marcat "rămâne de commit-uit de utilizator"). Conținutul e cunoscut doar indirect prin SPEC §3 și capability matrix. Planul nu inventează câmpuri dincolo de ce e confirmat de SPEC/cod. |
| 5 | `check_engine_contract.md` | **NOT_INSPECTED** | Absent din repo-ul publicat. Contractul CheckResult e însă verificabil direct în `src/sws_engine/core/result.py` (axis, id, name, result, reason_code, source_quality, source_class, inputs, threshold, input_lineage) — INSPECTED prin cod. |
| 6 | `test_suite.md` | **NOT_INSPECTED** | Absent din repo publicat; suita minimă e documentată în SPEC §11 (gold: AMZN DCF, HemaCare, FB growth, Portfolio AMZN, FX; synthetic edge cases) — folosită ca referință. |
| 7 | `implementation_decisions.md` | **NOT_INSPECTED** | Absent din repo publicat. Deciziile E3 relevante apar în assumptions.yaml și în rapoartele de validare. |
| 8 | `risk_register.md` | **NOT_INSPECTED** | Absent din repo publicat. Riscurile P0 cunoscute indirect (PB fals-exact, coverage interpretat ca scor, drift assumptions) sunt preluate din PLAN-Produs-Complet-v3.1.md și validation reports. |
| 9 | `runbook.md` | **NOT_INSPECTED** direct; **INSPECTED** `docs/real_data_population_runbook.md` | Runbook-ul de populare date reale există și e citit: gates obligatorii (legal-scope-report, source-registry-report, production-readiness), reguli non-negociabile de interpretare. |
| 10 | `legal/NOTICE.md` | **INSPECTED indirect** | Creat la remedierea G4 (audit final): atribuire CC BY-NC-SA către repo-urile publice SWS, restricții NC, not investment advice. |
| 11 | `config/legal_scope.yaml` | **INSPECTED** (prin `governance/legal_scope.py` + `legal_scope_report.json`) | usage_scope=internal_personal_educational; toate flag-urile comerciale/externe false; gate funcțional. |
| 12 | `config/source_registry.yaml` | **INSPECTED** (prin `source_registry_report.json`) | 7 surse, 1 ready; universe US/BVB, bond 10Y, ERP încă template → NOT_READY, blocking issues explicite. |
| 13 | Validation reports | **INSPECTED** | Stage 1 (COMPLETE WITH LIMITATIONS, gaps G1–G6), Final (G1–G3 închise, G4 parțial), CI/Deploy Final (PASS WITH LIMITATIONS), Final Remaining Controls. |
| 14 | `PLAN-Produs-Complet-v3.1.md` | **INSPECTED** | Fazele 3–8 anterioare; folosit ca model de structură. |
| 15 | Document strategic "motor personal de research financiar explicabil" | **INSPECTED** | Livrat ca brief atașat acestei cereri; constituie direcția strategică v4.0. |

**ASSUMPTION_USED (declarate explicit):**
- A1: Conținutul exact al `data_contract.md` este cel implicat de SPEC §3 și de capability matrix yfinance; unde planul are nevoie de câmpuri noi, le propune ca **extensii auxiliare**, nu ca modificări ale contractului existent.
- A2: Repo-ul rămâne pe layout `src/sws_engine/` cu packaging funcțional (G2 închis conform auditului final).
- A3: Baza de date curentă este SQLite cu tabelele din Faza 4 (instruments, input_snapshots, runs, outputs, checks, averages_snapshots, portfolios, portfolio_runs).

---

## 1. Executive Product Thesis

SWS Snowflake Engine v3.1 este un engine corect, guvernat și testat, care reproduce o metodologie publică documentată. Dar, ca produs, el răspunde la o întrebare pe care platformele comerciale o răspund deja mai bine vizual: "ce scor are compania X?". Valoarea reală construită în v3.1 nu este scorul — este **infrastructura de onestitate**: UNKNOWN vizibil, lineage per input, source_quality, provider degradation, assumptions hash, gates de guvernanță.

Teza v4.0: **repoziționăm produsul pe exact acea infrastructură.** Nu mai vindem (nici măcar nouă înșine) un scor; vindem răspunsul la întrebarea *"pot să am încredere în această analiză, și dacă nu, de ce?"*. Produsul devine al doilea strat, de audit, peste platformele de idei (TradingView, SWS, Koyfin, Finviz): ele generează candidați, engine-ul nostru îi trece printr-un proces disciplinat de verificare a datelor, a aplicabilității modelului, a fragilității concluziei și a ipotezelor — și produce memo-uri de research, nu semnale.

De ce acum: v3.1 a atins deja plafonul valorii pe direcția "dashboard cu scoruri" (audit: complete with limitations, blocat pe curatarea surselor). Direcția "audit engine" refolosește ~80% din ce există (contract checks, lineage, warnings, gates, DB, API, dashboard) și adaugă straturi noi (data confidence, model applicability, sensitivity, conclusion risk, thesis discipline) care nu concurează cu nimeni și rezolvă problema reală a unui investitor individual: **încrederea falsă**.

Metrică de succes a produsului: nu "câte companii au scor", ci **"câte concluzii false au fost prevenite"** — operaționalizat prin: (a) % din rulări în care conclusion_risk a semnalat corect fragilitate confirmată ulterior; (b) % din watchlist triat corect în Researchable Now / Data Limited / Needs Different Model; (c) zero incidente de UNKNOWN ascuns sau date inventate (gate CI).

---


### 1.1 Executive Scope Guard — Decision Hygiene Engine

Acest produs trebuie tratat ca un **decision hygiene engine**, nu ca un investment recommendation engine.

Funcția lui principală este să prevină încrederea falsă în scoruri, rankinguri, fair value punctual sau comparații incorecte între companii. Produsul trebuie să ajute utilizatorul să răspundă la întrebarea:

> „Pot să am încredere în această analiză, și dacă nu, de ce?”

Nu trebuie să răspundă la întrebarea:

> „Ce acțiune ar trebui să cumpăr?”

Prin urmare, toate fazele de implementare trebuie evaluate prin următorul filtru:

- mai puțin dashboard;
- mai puțin UI;
- mai puțină platformă;
- mai puține features de tip screener generalist;
- mai mult audit;
- mai mult lineage;
- mai mult source governance;
- mai mult model applicability;
- mai mult sensitivity;
- mai mult memo de research;
- mai multă disciplină a deciziei.

Orice funcționalitate care nu reduce riscul de concluzie falsă trebuie marcată `NOT_NOW`.

## 2. Product Positioning

**Poziționare într-o frază:** *Un motor personal de audit al research-ului de investiții care îți spune cât de robustă e analiza unei companii — ce date lipsesc, dacă modelul se aplică, cât de fragilă e concluzia — înainte să-ți formezi o convingere.*

**Categoria:** Personal Investment Research Audit Engine. Nu screener, nu terminal, nu robo-advisor, nu platformă de scoruri.

**Poziția în stack-ul utilizatorului:**

```
[Idei & context vizual]      TradingView / SWS / Koyfin / Finviz / news
            │  (watchlist CSV, tickere, ipoteze)
            ▼
[AUDIT LAYER — acest produs] data confidence → model applicability →
                             checks + explainability → sensitivity →
                             conclusion risk → red flags → memo
            │  (memo, triage, thesis status, decision journal)
            ▼
[Decizia utilizatorului]     în afara produsului; produsul nu recomandă
```

**Utilizator:** un singur operator (Silvian), uz personal/educațional, local. Fără multi-tenant, fără acces extern, fără monetizare în scopul acestui plan.

---

## 3. What This Product Is / Is Not

**ESTE:**
- Un engine determinist care rulează metodologia publică SWS v3.1 (neschimbată ca default) și adaugă deasupra un strat de audit: data confidence, model applicability, sensitivity, conclusion risk, red flags, explainability.
- Un sistem de disciplină de research: watchlist triage, thesis tracker cu reguli de invalidare, decision journal, memo generator.
- Un sistem cu lineage complet: fiecare număr din output e trasabil la sursă, dată, calitate și clasă de evidență.
- Un produs local, offline-first, cu date reale marcate onest (official/curated vs pragmatic vs manual).

**NU ESTE:**
- Nu este investment advice și nu emite BUY/SELL/HOLD.
- Nu este o clonă TradingView/Koyfin/SWS; nu face charting complex, real-time data, news feed, social sentiment.
- Nu este modelul live Simply Wall St și nu îl folosește ca sursă.
- Nu este un generator de "fair value precis" — dimpotrivă, include un "false precision killer" care afișează intervale, nu puncte.
- Nu este un produs comercial sau expus extern (blocat de legal gate până la review).
- Nu inventează date: lipsa datelor → UNKNOWN, întotdeauna, în orice modul nou.

---

## 4. Strategic Differentiation versus Existing Platforms

| Dimensiune | TradingView / Koyfin / Finviz | Simply Wall St live | **Acest produs** |
|---|---|---|---|
| Scop | idei, charting, screening | scor vizual + narativ | audit al robusteții analizei |
| Tratarea datelor lipsă | ascunsă sau interpolată | ascunsă în mare parte | UNKNOWN explicit + reason_code + lineage |
| Sursa fiecărui input | invizibilă | invizibilă | field-level lineage + source_class E0–E4 |
| Aplicabilitatea modelului | utilizatorul e pe cont propriu | parțial (modele diferite pe bănci/REIT) | Model Applicability Gate explicit + allowed_score_usage |
| Sensibilitate/fragilitate | inexistentă | inexistentă | bear/base/bull, matrice DR×g, reverse DCF, fragility score |
| Disciplina deciziei | inexistentă | inexistentă | thesis tracker, invalidation rules, decision journal, post-mortem |
| Comparabilitate scoruri | implicit "totul e comparabil" | implicit comparabil | comparability warning + do_not_compare |
| Output final | chart/scor | scor/snowflake | memo de research auditabil |

Diferențierea nu e feature parity — este **refuzul deliberat** al feature-urilor care produc încredere falsă, plus construirea celor care o reduc. Platformele existente rămân upstream, ca surse de idei; nu le replicăm.

---

## 5. Current Baseline and Assumed Repository State

Stare confirmată de auditurile Stage 1 + Final (2026-07-08):

**Există și funcționează:**
- Engine complet: 30 Snowflake checks cu contract complet (PASS/FAIL/UNKNOWN + reason_code + source_quality + source_class + inputs + threshold + input_lineage), routing pe company_type (standard / financial HF1–HF6 / loss-making cash-runway), valuation (two_stage_fcf, ddm, excess_returns, affo_dcf + fallbacks), growth A/B/C, portfolio engine.
- Reguli P0 verificate în cod: PB strict din tangible book value; D3/D4 FAIL_BY_DEFAULT sub 10 ani DPS; dividend gate bottom P10 → DIVIDEND_GATE_LOW_YIELD; score_normalized absent din runtime; degradări yfinance vizibile; exact 30 checks (assert în engine).
- `config/assumptions.yaml` cu registrul E1/E2/E3 și snapshot per run; hash assumptions per run.
- Persistență SQLite (instruments, input_snapshots, runs, outputs, checks, averages_snapshots, portfolios, portfolio_runs); batch runner cu izolare per ticker.
- API FastAPI (13 endpoints Faza 5, inclusiv analyze/company-live) + dashboard Streamlit (P1–P5) care accesează doar API-ul.
- Gates CI: pytest offline, ruff, schema validation, no-score_normalized, attribution footer, real-source honesty; legal-scope / source-registry / production-readiness CLI.
- Deployment scaffold: Docker, compose, backup, monitoring, EOD refresh.

**Nu există încă (relevant pentru v4.0):**
- Surse curate populate: universe US/BVB, bond 10Y, ERP — încă template → production-readiness NOT_READY.
- Documentele normative model pack în repo (data_contract.md etc.) — de commit-uit din copiile locale (G4 parțial).
- Orice strat de audit: data confidence score, model applicability gate, sensitivity, conclusion risk, red flags, thesis/decision/memo.
- Adapter SEC/FRED; identifier master; source conflict detector; staleness score.

**Implicație pentru plan:** v4.0 se construiește ca **straturi auxiliare** peste engine-ul înghețat, nu ca refactor. Prima datorie a v4.0 este să închidă restanțele v3.1 care blochează onestitatea (surse curate + docs normative), apoi să construiască audit layer-ul.

---


### 5.1 Gap Snapshot — What Exists / What Does Not Exist Yet

Repository baseline observed:

- Current repository commit observed in planning context: `801a25d feat(ops): real-dashboard-bootstrap workflow (yfinance_pragmatic) + runtime-summary/companies endpoints + offline tests`.

Existing:

| Area | Status |
|---|---|
| Company analysis engine | existent |
| Portfolio engine | existent |
| PASS/FAIL/UNKNOWN checks | existent |
| `output_schema.json` | existent |
| `config/assumptions.yaml` | existent |
| `config/legal_scope.yaml` | existent |
| `config/source_registry.yaml` | existent |
| yfinance pragmatic provider | existent |
| real-dashboard-bootstrap CLI | existent |
| SQLite persistence | existent |
| FastAPI API | existent |
| Streamlit dashboard | existent |
| production-readiness gate | existent |

Not yet implemented as v4.0 audit modules:

| Area | Status |
|---|---|
| Audit Layer v4 | inexistent |
| SEC EDGAR layer | inexistent |
| FRED/Treasury rates loader | inexistent |
| Mature ERP manual curated workflow | parțial / inexistent ca workflow complet |
| Model Applicability Gate | inexistent ca modul separat |
| Data Confidence Layer | inexistent ca modul separat |
| Sensitivity / valuation range audit layer | inexistent |
| Thesis Tracker | inexistent |
| Decision Journal | inexistent |
| Investment Memo Generator | inexistent |

Implication: first implementation must not attempt to build the full v4.0 product. The first implementation slice must create the audit layer foundation over existing persisted outputs.

## 6. Product Principles

1. **Truth over coverage.** Un UNKNOWN corect valorează mai mult decât un PASS pe date inventate. Niciun modul nou nu are voie să reducă vizibilitatea UNKNOWN.
2. **Every number has a passport.** Orice valoare afișată poartă: sursă, dată, source_quality, source_class, provider_profile. Fără pașaport → nu se afișează ca fapt.
3. **Model before math.** Înainte de orice scor, întrebarea este: se aplică modelul acestui tip de companie? Dacă nu — scorul e etichetat degraded/audit_only/do_not_compare.
4. **Fragility is a first-class output.** Fair value fără interval și fără sensibilitate = false precision. Se afișează intervale, matrice de sensibilitate și contribuția terminal value.
5. **Separate company quality from data quality.** Un scor slab pe date slabe nu înseamnă companie slabă; produsul le raportează pe axe separate.
6. **Additive, never destructive.** Extensiile de audit sunt scheme auxiliare și module noi; engine-ul, formulele și `output_schema.json` rămân neschimbate ca default. Orice excepție trece prin secțiune de impact + backward compatibility.
7. **Discipline over signals.** Produsul structurează procesul (triage, thesis, journal, memo); nu produce recomandări.
8. **Offline-first, reproducible.** Orice run e reproductibil din input_snapshot + assumptions_hash + engine_version; CI nu depinde de internet.
9. **Legal scope is a feature.** Gate-urile legale nu se relaxează; produsul refuză să ruleze în afara scopului declarat.
10. **No silent anything.** No silent fallback, no silent conflict resolution, no silent assumption change, no silent override expiry.

---

## 7. Non-negotiable Governance Rules

Preluate din model pack v3.1 și extinse pentru v4.0 — toate devin gates CI (vezi §38):

| # | Regulă | Enforcement |
|---|---|---|
| G-01 | Fiecare check păstrează contractul: PASS/FAIL/UNKNOWN + reason_code + source_quality + source_class + input_lineage | contract test existent + test pe orice check nou |
| G-02 | `score_normalized` nu apare în runtime; dacă va exista vreodată, e separat, etichetat experimental, niciodată primar | gate CI existent (grep) — se extinde la modulele noi |
| G-03 | UNKNOWN nu se ascunde, nu se agregă în tăcere, nu se normalizează | test "UNKNOWN never hidden" pe fiecare suprafață nouă (audit summary, memo, portfolio audit) |
| G-04 | provider_profile enum rămâne {sws_public_faithful_manual_inputs, yfinance_pragmatic}; degradarea yfinance vizibilă în orice output derivat | gate + test de propagare a warnings în audit layer |
| G-05 | Fără date inventate; template/synthetic marcate; fără redenumire sample→curated | real-source honesty gate existent |
| G-06 | `output_schema.json` nu se modifică; extensiile sunt scheme auxiliare separate, versionate | schema gate + review obligatoriu la orice PR care atinge schemas/ |
| G-07 | Formulele valuation/growth/portfolio nu se schimbă ca default; sensitivity engine rulează *copii parametrizate*, nu modifică base | test determinism: run base identic înainte/după sensitivity |
| G-08 | legal_scope rămâne internal_personal_educational; flags comerciale/externe false; orice relaxare cere legal_review_completed=true | legal gate existent — devine blocking în CI |
| G-09 | Atribuire CC BY-NC-SA + "not investment advice" pe fiecare suprafață (dashboard, memo, API meta) | attribution gate — se extinde la memo/tear sheet |
| G-10 | Dashboard accesează date exclusiv prin API | test existent — rămâne |
| G-11 | Orice explicație generată (inclusiv AI-assisted) trebuie legată de reason_code + inputs reale; nimic "narativ liber" prezentat ca fapt | template-driven explainer + test snapshot |
| G-12 | Manual overrides au expiry obligatoriu; override expirat → UNKNOWN, nu valoare veche | test override expiry |
| G-13 | Conflictele între surse nu se rezolvă silențios; se raportează + regulă explicită de precedență din source_registry | source conflict test |
| G-14 | Live tests skipped by default; CI 100% offline | marker pytest existent |

---

## 8. Target User Workflows

Workflow-urile pe care produsul trebuie să le facă posibile cap-coadă (fiecare devine criteriu de acceptare de fază):

**W1 — Company Audit (zilnic/ad-hoc):**
Ticker (venit din TradingView/SWS) → `audit-company` → utilizatorul vede: score_raw + coverage, data_confidence, model_applicability, conclusion_risk, top limitations, red flags, UNKNOWN clusters → decide: merită research profund / date insuficiente / model greșit.

**W2 — Watchlist Triage (săptămânal):**
CSV watchlist → `audit-watchlist` → 4 găleți: Researchable Now / Data Limited / Needs Different Model / Ignore for Now + manual review queue → utilizatorul își alocă timpul de research pe găleata 1.

**W3 — Deep Dive + Memo:**
Companie triată → sensitivity (bear/base/bull, DR×g, reverse DCF) → red flags + accounting quality + capital allocation → `generate-memo` → memo Markdown salvat, cu lineage, limitări și counter-thesis.

**W4 — Thesis Lifecycle:**
Utilizatorul scrie thesis YAML (bull/bear case, watch metrics, invalidation rules) → fiecare run ulterior evaluează thesis status: ON_TRACK / WATCH / BROKEN / UNKNOWN → alertă la BROKEN.

**W5 — Decision + Post-mortem:**
La o decizie (în afara produsului), utilizatorul o înregistrează: decision journal capturează thesis, data_confidence și conclusion_risk *la data deciziei* → la review date, post-mortem structurat.

**W6 — Portfolio Audit (lunar):**
Holdings CSV → weighted data confidence, weighted conclusion risk, concentrări sector/factor/thesis, unknown exposure → portfolio memo.

**W7 — Run Comparison (la orice re-rulare):**
`compare-runs` → ce checks și-au schimbat rezultatul, ce inputuri s-au schimbat, ce assumptions s-au schimbat (hash diff) → "ce s-a schimbat de data trecută" fără arheologie manuală.

---


### 8.1 Core Workflow Set v0 — Minimum Workflows Before Expansion

Before implementing advanced modules, the product must support five compact workflows.

#### Workflow 1 — Company Audit

Input: ticker or latest persisted run.

Output:

- `score_raw`
- `coverage_pct`
- `data_confidence`
- `model_applicability`
- `conclusion_risk`
- `critical_missing_inputs`
- `UNKNOWN clusters`
- `provider degradation`
- `top red flags`
- `manual review items`

Acceptance: user can tell whether the analysis is robust, not only whether the score is high.

#### Workflow 2 — Watchlist Audit

Input:

```csv
ticker,idea_source,priority
AAPL,TradingView,high
MSFT,Koyfin,high
JPM,manual,medium
O,SimplyWallSt,medium
```

Output buckets:

- `Researchable Now`
- `Data Limited`
- `Needs Different Model`
- `Ignore for Now`
- `Manual Review Required`

Acceptance: each ticker has a reason for its bucket.

#### Workflow 3 — Sensitivity / Valuation Range

Output:

- bear/base/bull
- discount rate x terminal growth
- ERP sensitivity
- FCF margin sensitivity
- terminal value contribution
- reverse DCF

Acceptance: current price can be interpreted against assumption fragility.

#### Workflow 4 — Thesis Tracking

Input: local thesis YAML.

Output:

- `ON_TRACK`
- `WATCH`
- `BROKEN`
- `UNKNOWN`

Acceptance: unevaluable thesis rules degrade status; they are not ignored.

#### Workflow 5 — Portfolio Audit Minimal

Input: local holdings CSV.

Output:

- weighted data confidence
- weighted conclusion risk
- sector concentration
- factor concentration
- macro sensitivity
- unknown exposure
- single thesis concentration

Acceptance: portfolio audit shows how much of the portfolio depends on weak data or shared assumptions.

## 9. Core Product Capabilities

Cele 10 capabilități-nucleu (detaliate pe module în §10 și pe faze în §42):

| # | Capabilitate | Întrebarea la care răspunde | Prioritate |
|---|---|---|---|
| C1 | Data Confidence Layer | Cât de bune sunt datele din spatele acestui output? | P0 |
| C2 | Model Applicability Gate | Se aplică modelul standard acestei companii? Pot compara scorul? | P0 |
| C3 | Explainability Layer | De ce e acest check PASS/FAIL/UNKNOWN, în limbaj uman, legat de reason_code? | P0 |
| C4 | SEC-first Data Layer | Care date vin din filing oficial vs yfinance vs manual? | P0/P1 |
| C5 | Sensitivity & Valuation Range | Cât de fragil e fair value? Ce presupune piața (reverse DCF)? | P1 |
| C6 | Conclusion Risk Layer | Cât de probabil e ca această concluzie să fie falsă? | P1 |
| C7 | Red Flags + Accounting Quality + Capital Allocation | Ce ar trebui verificat manual înainte de orice decizie? | P1 |
| C8 | Watchlist Audit + Thesis Tracker + Decision Journal | Unde-mi aloc timpul? Teza mai e valabilă? Ce am decis și de ce? | P1/P2 |
| C9 | Investment Memo Generator | Ce memo auditabil pot salva? | P1 |
| C10 | Portfolio Audit Minimal | Ce parte din portofoliu stă pe date slabe / pe aceeași ipoteză? | P2 |

---

## 10. Capability Map by Module

Toate modulele noi trăiesc în pachete noi (`src/sws_engine/audit/`, `src/sws_engine/sec/`, `src/sws_engine/sensitivity/`, `src/sws_engine/research/`), consumă output-ul validat pe `output_schema.json` + input_snapshot + DB, și scriu în scheme auxiliare (§ Data Models). Zero modificări în `checks/`, `valuation/`, `growth/`, `portfolio/`.

### A. Audit Core (`src/sws_engine/audit/`)

| Modul | Scop | Input | Output | UNKNOWN handling |
|---|---|---|---|---|
| `data_confidence.py` | Scor + hartă a calității datelor unui run | output JSON (checks: source_quality, reason_code), input_snapshot, field_quality, source_registry | `data_confidence.schema.json`: confidence_grade (A–E), % exact/approximation/assumption/missing per axă, critical_missing_inputs[], stale_fields[], conflicts[] | UNKNOWN-urile sunt *materia primă*; nu se re-scorează, se clasifică pe cauze (MISSING_INPUT, PROVIDER_LIMITATION, GATE) |
| `model_applicability.py` | Gate de aplicabilitate model per company_type | identifier_master, company_type, output (valuation_model/variant), heuristici de clasificare | `model_applicability.schema.json`: classification, status (applicable/degraded/not_applicable), reason_code, recommended_model, allowed_score_usage | Clasificare incertă → status=UNKNOWN + allowed_score_usage=audit_only |
| `conclusion_risk.py` | Riscul de concluzie falsă | data_confidence + model_applicability + sensitivity summary + red flags | `conclusion_risk.schema.json`: risk_grade (LOW/MEDIUM/HIGH/UNKNOWN), drivers[], manual_review_items[] | Orice componentă lipsă → risk_grade nu scade sub MEDIUM; componenta lipsă apare ca driver "COMPONENT_UNAVAILABLE" |
| `audit_summary.py` | Agregatorul: un singur obiect per run | toate cele de mai sus + output original | `audit_summary.schema.json` cu linkuri run_id/input_snapshot_id/assumptions_hash | Agregare fără mascare: fiecare sub-raport rămâne accesibil integral |
| `audit_report.py` | Randare Markdown/JSON a audit summary | audit_summary | fișier `out/audit/<TICKER>/...` | secțiune dedicată "What we don't know" obligatorie |

Acceptare A: pentru un run existent (demo fixture), `audit-company` produce audit_summary valid pe schema auxiliară, cu toate UNKNOWN-urile din output regăsibile 1:1 în critical_missing_inputs sau unknown_clusters; test de non-pierdere.

### B. Data Source Governance (`src/sws_engine/sources/` — extindere)

- **source_registry field-level rules:** extinderea `config/source_registry.yaml` cu mapare câmp→sursă permisă→calitate maximă permisă (ex.: `intangible_assets: allowed_sources=[sec_companyfacts, manual_curated]; yfinance→approximation cap`). Backward compatible: câmpurile noi sunt opționale.
- **field-level lineage:** deja există `input_lineage` per check; se adaugă un *lineage index* per run (câmp → sursă, as_of, quality, override_id) persistat, interogabil.
- **source conflict detector:** când două surse dau valori diferite pentru același câmp (ex. SEC vs yfinance revenue), emite `source_conflict.schema.json` record: field, values per source, delta%, precedence_rule_applied, resolved_value_source. Fără regulă de precedență definită → câmpul devine UNKNOWN + conflict raportat. **Niciodată medie/blend silențios.**
- **data staleness score:** per câmp: age_days vs TTL din registry (prices EOD, financials 7d/1q, averages 1d, rates 30d) → stale flag; agregat per run în data_confidence.
- **official vs pragmatic flag:** fiecare sursă din registry primește `source_tier: official_filing / curated / pragmatic / manual / synthetic`; tier-ul se propagă în lineage index.
- **manual override registry + expiry:** `data/overrides/overrides.yaml`: field, ticker, value, source_note, created_at, expires_at (obligatoriu), owner. Override expirat → ignorat, câmp UNKNOWN, warning `OVERRIDE_EXPIRED`.
- **no silent fallback policy:** orice fallback (sursă secundară, nivel de averages, variantă de valuation) emite warning + apare în lineage. Test dedicat.

### C. SEC-first Data Layer (`src/sws_engine/sec/`)

- `companyfacts_adapter.py`: fetch + cache local `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (rate-limited, User-Agent conform SEC fair access; offline în CI prin fixture-uri înregistrate).
- `cik_resolver.py`: ticker→CIK din `company_tickers.json` SEC, versionat local.
- `xbrl_tag_resolver.py`: mapare us-gaap tags → câmpuri engine, cu listă de tag-uri candidate per câmp (ex. Revenues / RevenueFromContractWithCustomerExcludingAssessedTax) și regulă de selecție explicită; tag lipsă → câmp UNKNOWN + `XBRL_TAG_MISSING`, **niciodată alt tag "apropiat" nedeclarat**.
- `statement_snapshot.py`: snapshot normalizat (balance sheet, income, cashflow) per fiscal period, cu unit normalization (USD, milioane→unități) și capex sign normalizer (capex întotdeauna negativ-outflow intern, documentat).
- `ttm_builder.py`: TTM din 4 trimestre; lipsă trimestru → TTM UNKNOWN (nu 3/4 anualizat silențios).
- `reconciliation.py`: annual vs sum-of-quarters, toleranță configurabilă; depășire → conflict record.
- `fiscal_period_validator.py`: perioade suprapuse/lipsă/duplicate → erori explicite.
- `sec_mapping_report.py`: raport câmp-cu-câmp SEC→engine: mapped/unmapped/conflicted, per ticker.

Efect asupra provider_profile: **nu se adaugă enum nou în output_schema** (regula G-06). SEC alimentează payload-uri prin merge tool-ul existent; când câmpurile critice sunt din SEC/manual curated → profil `sws_public_faithful_manual_inputs`; altfel rămâne `yfinance_pragmatic`. Tier-ul real per câmp trăiește în lineage index (auxiliar), care e mai granular decât enum-ul de profil.

### D. Rates / ERP / Macro (`src/sws_engine/rates/` — extindere)

- FRED/Treasury 10Y loader: fetch DGS10 (sau export CSV manual) → `bond_yields_10y_curated.csv` cu manifest (source, fetched_at, series_id); media 5 ani calculată de engine-ul existent.
- ERP manual curated loader: `erp_curated.json` per țară, cu câmpuri obligatorii: value, source_note (ex. "Damodaran Jan-2026, citit manual"), reviewed_by, review_date, `review_status: draft/reviewed/expired`, expires_at.
- Operator review workflow: CLI `validate-erp-curated` refuză status≠reviewed pentru rulări non-demo; expired → UNKNOWN discount rate → valuation UNKNOWN (onest).
- `sensitivity_required: true` flag pe ERP: orice fair value calculat cu ERP curated cere sensitivity run înainte de a apărea în memo (gate în memo generator).
- Macro assumption lineage: risk_free/ERP/savings_rate/cpi intră în lineage index cu tier=curated/manual, niciodată "exact".

### E. Identifier Master (`data/real_sources/reference/identifier_master.csv` + `src/sws_engine/reference/`)

Câmpuri: ticker, exchange, country, currency, CIK, FIGI, ISIN, CUSIP, LEI, primary_listing (bool), security_type (common/adr/fund/etf/reit_unit/pref), company_type (motorul de routing există deja), is_adr, is_foreign_issuer, sursă per identificator + as_of.
Reguli: FIGI/ISIN/CUSIP/LEI sunt *opționale* și pot rămâne UNKNOWN fără a bloca (licențe: CUSIP e proprietar — nu se scrape-uiește; se completează manual doar dacă utilizatorul are drept de acces). Fund/ETF → excluse din Snowflake (regulă existentă) și marcate în applicability. Duplicate ticker cross-exchange → eroare explicită, nu ghicire.

### F. Model Applicability (detaliu clasificare)

Clase: standard_industrial, bank, insurance, reit, utility, commodity_cyclical, saas, pharma, loss_making, adr_foreign, fund_etf_excluded.
Surse de clasificare (în ordine de precedență): identifier_master (manual curated) → SEC SIC code → heuristici pe payload (deposits present→bank; affo/ffo→reit; negative earnings window→loss_making) → UNKNOWN.
Output per companie: `allowed_score_usage ∈ {rankable, display_only, audit_only, do_not_compare}` + comparability warning text. Ex.: bank cu HF checks complete → rankable *în cohorta bănci*, do_not_compare cross-sector; REIT fără AFFO → audit_only.
**Nu schimbă routing-ul de checks existent** (care rămâne pe company_type din payload); gate-ul doar etichetează și avertizează. Divergență între clasificarea gate-ului și company_type din payload → warning `APPLICABILITY_MISMATCH` + manual review item.

### G. Sensitivity and Valuation (`src/sws_engine/sensitivity/`)

- `scenario_runner.py`: rulează engine-ul de valuation existent (nemodificat) pe grile de parametri: bear/base/bull (definiți ca deltas configurabile în `config/sensitivity.yaml`), matrice discount_rate × terminal_growth, ERP ±, risk-free ±, FCF margin ±, revenue growth ±. Base run = byte-identic cu run-ul normal (test G-07).
- `terminal_value_contribution.py`: % din fair value provenit din TV; >75% → warning `TV_DOMINATED`.
- `reverse_dcf.py`: dat prețul curent, rezolvă growth-ul implicit (sau FCF margin implicit) care ar justifica prețul, pe modelul two_stage existent; output: market-implied expectations + comparație cu analyst/historical growth.
- `fragility_score.py`: dispersia fair value pe grilă normalizată la base (ex. (P90−P10)/base) → fragility LOW/MEDIUM/HIGH; intră în conclusion_risk.
- **False precision killer:** orice afișare de fair value în audit/memo e obligatoriu interval [bear, bull] + fragility, nu punct; punctul apare doar ca "base" în interiorul intervalului. Gate în memo generator.
- UNKNOWN: dacă valuation base e UNKNOWN (inputs lipsă), sensitivity nu rulează și raportează SENSITIVITY_UNAVAILABLE cu cauza; nu se seed-uiește cu valori inventate.

### H. Business Quality (`src/sws_engine/audit/business_quality.py`) — P2

Metrici informative (nu checks noi în Snowflake): revenue durability (volatilitate/trend 5–10y), margin stability, operating leverage, FCF conversion (FCF/NI), ROIC trend, cyclicality score (corelație cu ciclu, doar dacă date suficiente — altfel UNKNOWN), cash conversion cycle, quality deterioration alert (deteriorare ≥N metrici între runs). Toate cu contract-lite: value/UNKNOWN + lineage + quality. Nu intră în Snowflake score (G-01/G-06).

### I. Balance Sheet / Solvency (`src/sws_engine/audit/solvency.py`) — P2

Net debt trend, interest coverage trend, debt service stress (rate +200bp pe datoria variabilă doar dacă split-ul fix/variabil există — altfel UNKNOWN), cash-to-debt, goodwill-to-assets, share dilution 5y, dividend coverage by FCF, liquidity runway (refolosește logica loss-making existentă), solvency confidence = data confidence restrâns la câmpurile de bilanț.

### J. Capital Allocation (`src/sws_engine/audit/capital_allocation.py`) — P1/P2

Din cashflow statements (SEC-first): dividends paid, buybacks, share count discipline (net dilution vs buyback spend), debt issuance/repayment net, capex intensity (capex/revenue vs istoric), acquisition intensity, goodwill growth vs equity growth, SBC dilution monitor (SBC/revenue + share count), owner earnings approximation (NI + D&A − maintenance capex proxy, **marcat E2/approximation întotdeauna**), red flags de alocare (buyback pe datorie la P/E extrem etc. — praguri configurabile, nu hardcodate).

### K. Watchlist and Research Workflow (`src/sws_engine/research/watchlist.py`)

Triage per ticker pe baza audit_summary: `researchable_now` (confidence≥B, applicability=applicable) / `data_limited` / `needs_different_model` / `ignore_for_now` (fund/etf, do_not_compare fără interes declarat). + research queue rank (sortare pe confidence×interes, fără scor de "atractivitate"), idea source tracking (câmp liber: tradingview/sws/manual), holding vs watchlist mode, quarterly review calendar (next_review_date per ticker).

### L. Thesis Tracker (`data/theses/<TICKER>.yaml` + `src/sws_engine/research/thesis.py`)

Structură YAML: ticker, created_at, bull_case[], bear_case[], watch_metrics[] (metric, source_field, direction, threshold), invalidation_rules[] (regulă mașină-evaluabilă pe câmpuri din output/audit: ex. "H_score_raw < 3 două runs consecutive", "revenue_growth < 0 TTM"), review_cadence.
Evaluare per run: fiecare invalidation rule → triggered/not/UNKNOWN (câmp lipsă). Status: ON_TRACK (nicio regulă triggered, toate evaluabile), WATCH (≥1 watch metric în derivă sau ≥1 regulă neevaluabilă), BROKEN (≥1 invalidation triggered), UNKNOWN (majoritatea regulilor neevaluabile). **Regulile neevaluabile nu se sar: degradează statusul.**

### M. Decision Journal (`data/decisions/decisions.jsonl` + `src/sws_engine/research/journal.py`)

Câmpuri per intrare: decision_id, date, ticker, decision_type (research_deeper/pass/add_watch/remove_watch/personal_action_external), thesis_snapshot_ref, expected_outcome (text), data_confidence_at_decision, conclusion_risk_at_decision, run_id_at_decision, review_date, post_mortem (completat ulterior: outcome, what_data_was_wrong, what_assumption_was_wrong). Produsul **nu** înregistrează ordine/tranzacții; decision_type e despre procesul de research.

### N. Portfolio Audit Minimal (`src/sws_engine/audit/portfolio_audit.py`) — P2

Weighted data confidence (pe greutăți), weighted conclusion risk, sector concentration (HHI simplu), factor concentration doar dacă există clasificare curated — altfel UNKNOWN (nu proxy-uri slabe de corelație — risc #29), macro sensitivity map (ce poziții depind de aceleași assumptions: ERP, risk-free, un anumit growth), unknown exposure (% din valoare cu confidence D/E), single thesis concentration (poziții legate de aceeași teză), attribution lite (contribuție la return, refolosind portfolio engine existent), portfolio memo.

### O. Explainability and Reporting (`src/sws_engine/explain/` + `src/sws_engine/reporting/` extindere)

- `reason_code_dictionary.yaml`: fiecare reason_code existent + nou → template de explicație (analyst mode + plain English mode), variabile permise = doar câmpuri din check.inputs/threshold/lineage. **Explainer-ul e template-driven, nu free-text LLM** — elimină riscul #26/#27 by design. AI-assisted rewriting e permis doar ca post-procesare opțională, cu gate: textul final trebuie să conțină reason_code-ul și valorile din inputs (test).
- check explainer: pentru fiecare FAIL și UNKNOWN — explicație obligatorie; PASS — la cerere.
- top 5 risks / top 5 manual review items: derivate din conclusion_risk drivers, nu generate liber.
- counter-thesis generator: pentru fiecare bull_case item din thesis → ce check/red flag/sensitivity îl contrazice (mapare pe date, nu speculație); bull/bear debate mode = redare față în față a acestora.
- memo formats: investment audit memo (complet), one-page tear sheet, analyst mode, plain English mode, board pack mode (P3).

---

## 11. Target Architecture

```
                        ┌──────────────────────────────────────────┐
  surse externe         │  INGESTION & GOVERNANCE                  │
  ────────────          │  sec/ (CompanyFacts, CIK, XBRL)          │
  SEC EDGAR ──────────► │  rates/ (FRED/Treasury, ERP curated)     │
  FRED/Treasury ──────► │  providers/yfinance_live (există)        │
  yfinance ───────────► │  manual overrides + expiry               │
  CSV manual (TV) ────► │  source_registry field rules             │
                        │  conflict detector · staleness · lineage │
                        └───────────────┬──────────────────────────┘
                                        │ payload (data_contract, neschimbat)
                        ┌───────────────▼──────────────────────────┐
                        │  ENGINE v3.1 — ÎNGHEȚAT                  │
                        │  checks(30) · valuation · growth ·       │
                        │  portfolio · assumptions snapshot        │
                        └───────────────┬──────────────────────────┘
                                        │ output_schema.json (neschimbat)
                        ┌───────────────▼──────────────────────────┐
                        │  AUDIT LAYER (nou, auxiliar)             │
                        │  data_confidence · model_applicability   │
                        │  sensitivity/reverse_dcf · red_flags     │
                        │  accounting_quality · capital_allocation │
                        │  conclusion_risk · audit_summary         │
                        └───────────────┬──────────────────────────┘
                                        │ scheme auxiliare *.schema.json
                        ┌───────────────▼──────────────────────────┐
                        │  RESEARCH WORKFLOW                       │
                        │  watchlist triage · thesis tracker ·     │
                        │  decision journal · memo generator ·     │
                        │  run comparison                          │
                        └───────────────┬──────────────────────────┘
                                        │ API only
                        ┌───────────────▼──────────────────────────┐
                        │  API (FastAPI, extins) → Dashboard sobru │
                        │  CLI (extins) → fișiere out/             │
                        └──────────────────────────────────────────┘
```

Principii arhitecturale: engine read-only pentru audit layer; audit layer idempotent per run_id (re-rulare = același rezultat pe același snapshot); toate persistate cu chei (run_id, ticker, valuation_date); dashboard fără DB direct (G-10).

---

## 12. Data Architecture

- **Sursa de adevăr:** output JSON validat + input_snapshot JSON, în SQLite (existente). Audit layer adaugă tabele/artefacte auxiliare, cu FK logic pe run_id.
- **Tabele/artefacte noi:** audit_summaries(run_id, json), data_confidence(run_id, json + coloane extrase: grade, pct_exact, pct_missing), model_applicability(ticker, as_of, json), conclusion_risk(run_id, json), sensitivity_runs(run_id, scenario_grid_hash, json), red_flags(run_id, json), source_conflicts(run_id, field, json), lineage_index(run_id, field, source_id, tier, as_of, quality, override_id), theses (fișiere YAML, indexate), decisions (JSONL append-only), memos (fișiere + memo_manifest).
- **Immutabilitate:** decisions.jsonl e append-only; post-mortem = intrare nouă legată de decision_id, nu editare. Memo-urile generate nu se suprascriu (versiuni datate).
- **Retenție:** totul local; backup-ul existent (ops/backup.sh) se extinde cu directoarele noi.
- **Identitate:** cheia canonică devine (ticker, exchange) validată contra identifier_master; ambiguitate → refuz explicit.

## 13. Source Strategy

| Tier | Surse | Rol | Reguli |
|---|---|---|---|
| official_filing | SEC EDGAR CompanyFacts/XBRL | statements US: sursa preferată pentru bilanț/income/cashflow | cache local, fixture-uri în CI, fair-access rate limit, User-Agent identificat |
| curated | FRED/Treasury DGS10, ERP manual (stil Damodaran, introdus manual), universe CSV curat, FX EOD curat | rates, macro, universuri | versionate în repo/data, cu manifest + review_status |
| pragmatic | yfinance | prețuri, completare non-US, dividende, ce nu are SEC | **rămâne vizibil degradat**: profile yfinance_pragmatic, quality cap approximation, banner permanent |
| manual | overrides (AFFO/FFO/NAV, bank NPL/deposits, analyst estimates), TradingView **doar export CSV manual** | câmpuri pe care niciun provider gratuit nu le are onest | expiry obligatoriu; TradingView fără scraping/API neoficial |
| synthetic | fixtures demo | doar teste/demo | marcate; honesty gate le blochează din producție |

Interdicții: fără modelul live SWS ca sursă; fără scraping TradingView; fără provideri plătiți nemarcați ca "unreviewed license" în registry.


### 13.1 Data Source Feasibility Inventory — Free-first Update

A supplementary data-source inventory confirms that the v4.0 strategy is feasible for internal/personal/educational use with a free-first source stack.

**Feasibility verdict:** the product is feedable with real data. The historical/core axes are largely covered by free official or pragmatic sources, while some forward-looking and specialty fields remain manual or UNKNOWN by design.

| Domain | Primary free source | Tier | Feasibility | Product implication |
|---|---|---|---|---|
| US financial statements | SEC EDGAR CompanyFacts / Frames / Submissions | official_filing | high | core statements, averages, CIK/SIC, partial bank fields |
| US rates / CPI / savings | FRED / Treasury Fiscal Data | curated | high | risk-free, macro, production-readiness inputs |
| ERP / country risk | Damodaran manual curated | manual/curated | feasible with operator review | ERP remains assumption, not objective data |
| EOD prices / dividends | yfinance + Stooq fallback | pragmatic | feasible with cache | yfinance remains degraded; Stooq becomes resilience task |
| FX | ECB / BNR primary, yfinance fallback | curated/pragmatic | high | portfolio FX should prefer official daily reference rates |
| Identifier master | SEC CIK/SIC, GLEIF LEI, OpenFIGI optional | curated | high for functional needs | CUSIP remains licensed/manual-only |
| Analyst estimates / forward FCF | manual overrides or paid providers | manual / UNKNOWN | limited free coverage | route A remains manual/UNKNOWN; route B/C historical still works |
| REIT AFFO/FFO/NAV | manual supplemental review | manual | partial | REITs remain degraded unless user curates fields |
| Bank deposits/NPL/charge-offs | SEC partial + FFIEC Call Reports P2 | official/curated | partially automatable | bank fields can be upgraded over time |
| Market/industry averages | SEC Frames + price provider | official/pragmatic | high | averages builder is feasible without paid vendor |

**Backlog deltas from source inventory:**

1. Add **Stooq** as P1 secondary EOD price provider to reduce yfinance fragility.
2. Add **SEC Frames API** to the averages builder; this is more scalable than per-ticker fetching for US market/industry averages.
3. Extend the SEC XBRL resolver with bank-specific tags such as deposits and allowance/credit-loss fields; this can move part of bank-specific inputs from `missing/manual` toward `official_filing`.
4. Set **ECB/BNR** as primary FX reference sources, with yfinance only as pragmatic fallback.
5. Keep Finnhub/FMP as P2 experimental only with `license_status=unreviewed` until terms are reviewed.
6. Mark CUSIP as licensed/manual-only; do not scrape or derive it automatically.
7. Document explicitly that SWS-style weighted analyst estimates and forward FCF estimates are not available honestly for free at scale; they remain manual or UNKNOWN.

**Operator effort assumption:** the plan assumes approximately 1-2 hours/month of manual curation for ERP, selected analyst estimates, selected REIT metrics, and universe maintenance. This is acceptable for a personal research workflow and must be captured through lineage, review status, and expiry.

## 14. Source Registry Strategy

`config/source_registry.yaml` se extinde (backward compatible) cu:
- per sursă: `tier`, `license_status (reviewed/unreviewed/na)`, `ttl_days`, `allowed_fields[]` sau `field_quality_caps{}`;
- per câmp critic (listă din data_contract): `allowed_sources` în ordine de precedență + `conflict_policy: report_and_prefer_first / report_and_unknown`;
- `production_ready` rămâne cum e; production-readiness CLI existent capătă verificarea câmpurilor noi.
Gate: sursă plătită cu license_status=unreviewed nu poate fi production_ready (Legal Stop Condition L4).

## 15. Data Confidence Layer

**Scop:** un grade A–E + hartă, per run, care separă calitatea datelor de calitatea companiei.

Calcul (E2/E3, configurabil în `config/audit_policies.yaml`, NU în assumptions.yaml al modelului — separare de registre):
- pondere per câmp = criticitate (din data_contract: câmpuri care alimentează multe checks/valuation au pondere mai mare);
- scor per câmp: exact=1.0, approximation=0.6, assumption=0.3, missing=0; penalizare staleness (× factor sub TTL); penalizare conflict nerezolvat (=0);
- grade: A ≥0.85, B ≥0.7, C ≥0.5, D ≥0.3, E <0.3 (praguri configurabile, documentate ca E2).
Outputs: grade global + per axă + critical_missing_inputs map (câmp → checks afectate → cum se remediază: "completați override X / sursa Y îl are"), stale list, conflicts list, official/pragmatic/manual split.
UNKNOWN handling: grade-ul NU maschează UNKNOWN — e o funcție de ele. Afișat mereu lângă coverage_pct, niciodată în locul lui.
Acceptare: pe fixture-ul yfinance_degraded existent, grade-ul scade demonstrabil față de fixture-ul complet, iar fiecare câmp scos apare în critical_missing_inputs.

## 16. Model Applicability Gate

Detaliat în §10.F. Adaug aici regulile de produs:
- Gate-ul rulează **înainte** de interpretare, nu înainte de engine (engine-ul rulează oricum, cu routing-ul lui existent); rezultatul gate-ului etichetează output-ul.
- `allowed_score_usage` guvernează UI/API: `do_not_compare` → screener-ul refuză să pună compania în ranking cross-sector; `audit_only` → scorul apare doar în pagina de audit cu banner; `display_only` → fără sortare.
- Cazuri fixate: bank/insurance → comparabil doar intra-cohortă; REIT fără AFFO/FFO → audit_only + recommended_model=affo_dcf cu inputuri manuale; fund/ETF → exclus (există deja în portfolio); ADR → warning valută/duble listări; loss_making → recomandă interpretare pe cash runway, valuation marcat fragil.
- Acceptare: JPM (bank) și O (REIT) din golden fixtures primesc clasificare corectă + usage corect; un ETF e exclus cu reason_code.

## 17. SEC-first Financial Data Layer

Detaliat în §10.C. Decizii de produs:
- SEC e **preferat** pentru statements US, dar nu obligatoriu: absența CIK (non-US) → fallback declarat la yfinance (warning `NON_SEC_FALLBACK`), nu eroare.
- CI: 100% pe fixture-uri CompanyFacts înregistrate (AAPL, MSFT, NVDA, JPM, O, XOM); live tests marker `live`.
- Scopul primului slice: doar câmpurile care alimentează checks existente + capital allocation (revenue, NI, equity, assets, liabilities, intangibles explicit, cash+STI, OCF, capex, dividends paid, buybacks, shares outstanding, interest expense, debt).
- Non-scop: full XBRL taxonomy, footnotes parsing, 10-K text NLP — Not Now.

## 18. Rates / ERP / Macro Assumption Layer

Detaliat în §10.D. Decizii de produs:
- ERP nu e "date", e **ipoteză curated**: review_status lifecycle (draft→reviewed→expired), expiry 6 luni default, sensitivity_required=true.
- Risk-free: DGS10 din FRED CSV (fetch sau export manual), media 5y calculată de modulul rates existent; manifest cu source+fetched_at.
- Orice fair value din memo care depinde de ERP/risk-free afișează valorile folosite + as_of + review_status (lineage vizibil).

## 19. Identifier Master

Detaliat în §10.E. Decizii de produs: fișier CSV curated versionat + loader cu validare (duplicate, exchange necunoscut, currency mismatch cu payload → erori); identificatorii licențiați (CUSIP) opționali și doar manual; FIGI permis (OpenFIGI are API gratuit — dar integrarea automată e P3/Not Now; manual la început).

## 20. Explainability Layer

Detaliat în §10.O. Reguli dure:
- Sursa unică de explicații = `reason_code_dictionary.yaml`; dicționar incomplet = test failure (fiecare reason_code din enum trebuie să aibă intrare).
- Două registre de limbaj: analyst (termeni tehnici) și plain English (fără jargon), ambele generate din același template + aceleași valori.
- Orice FAIL/UNKNOWN fără explicație randabilă = bug (test).
- AI rewriting: opțional, offline-optional, și gate-uit: output-ul trebuie să conțină verbatim reason_code + valorile numerice din inputs; altfel se folosește template-ul brut. (Mitigare riscuri #26/#27.)

## 21. Red Flag Engine

`src/sws_engine/audit/red_flags.py` — reguli deterministe, fiecare cu: id, condition (pe câmpuri output/statements), severity (INFO/WARN/CRITICAL), evidence (valori + lineage), UNKNOWN dacă inputurile lipsesc.
Set inițial (P1, ~15 reguli): TV_DOMINATED (>75% din FV), NEGATIVE_FCF_POSITIVE_NI persistent, RECEIVABLES_OUTPACE_REVENUE, GOODWILL_SPIKE, DILUTION_HIGH (>3%/an), DIVIDEND_NOT_COVERED_BY_FCF, INTEREST_COVERAGE_DETERIORATING, AUDIT_DATA_CONFLICT_PRESENT, STALE_CRITICAL_DATA, PROVIDER_ONLY_PRAGMATIC_ON_CRITICAL_FIELDS, OVERRIDE_EXPIRING_SOON, APPLICABILITY_MISMATCH, DPS_HISTORY_SHORT, LOSS_MAKING_RUNWAY_LOW, ERP_REVIEW_EXPIRED.
Red flags ≠ checks Snowflake: nu intră în score (G-01), trăiesc în `red_flags.schema.json`.

## 22. Accounting Quality Module

P2. Metrici informative din SEC statements: accruals ratio (NI−OCF)/assets, revenue vs receivables divergence, inventory build, capitalizare vs expensare (capex vs D&A trend), one-off frequency (doar dacă datele permit separarea — altfel UNKNOWN), SBC/revenue trend. Fiecare metric cu lineage + quality; fără "scor de fraudă" agregat (false precision) — doar liste de semnale cu evidence.

## 23. Capital Allocation Module

Detaliat în §10.J. P1 pentru subsetul dividende/buybacks/dilution/capex (alimentează red flags), P2 pentru restul.

## 24. Valuation Range and Sensitivity Engine

Detaliat în §10.G. Livrabile: `sensitivity_summary.schema.json` cu: base FV + interval [bear,bull], grila DR×g (matrice ≤ 5×5), ERP±100bp, rf±100bp, FCF margin ±20% relativ, revenue growth ±20% relativ, TV contribution %, fragility grade. Determinism: grila e hash-uită; același input+grilă → același output (test).

## 25. Reverse DCF / Market-implied Expectations

Detaliat în §10.G. Output: implied growth (sau implied margin) + delta față de analyst/historical + verdict text template-driven ("prețul curent presupune X% growth 5y; estimările analiste sunt Y%"). UNKNOWN dacă modelul companiei nu e two_stage_fcf (bank/REIT → reverse pe modelul lor e Not Now, marcat explicit).

## 26. Conclusion Risk Layer

Combinator determinist (E2, configurabil):
```
inputs: data_confidence.grade, model_applicability.status,
        sensitivity.fragility, red_flags (max severity, count),
        unknown_clusters pe checks critice
output: risk_grade LOW/MEDIUM/HIGH/UNKNOWN + drivers[] + manual_review_items[]
reguli exemplu (config): confidence ∈ {D,E} → ≥HIGH;
  applicability ∈ {not_applicable, UNKNOWN} → ≥HIGH;
  fragility=HIGH sau TV_DOMINATED → ≥MEDIUM;
  orice componentă indisponibilă → nu sub MEDIUM + driver COMPONENT_UNAVAILABLE
```
Nicio medie ponderată opacă: reguli lexicografice max(), enumerabile în output. Fiecare driver e explicabil (dicționar).

## 27. Watchlist Audit

Detaliat în §10.K. CLI `audit-watchlist` + pagina 5 dashboard. Acceptare: pe un watchlist de 10 tickere mixte (2 bănci, 1 REIT, 1 ETF, 6 standard), gălețile ies corect și fiecare încadrare are reason.

## 28. Thesis Tracker

Detaliat în §10.L. + `thesis.schema.json` pentru validarea YAML-ului; editare = fișier local (dashboard-ul doar vizualizează în P1 slice; editor în dashboard e P3).

## 29. Decision Journal

Detaliat în §10.M. Append-only, snapshot-uri de context obligatorii (confidence + risk + run_id la data deciziei). Fără decision types care implică ordine de tranzacționare generate de produs.

## 30. Investment Memo Generator

`generate-memo`: compune din artefacte existente (audit_summary, sensitivity, red flags, thesis, explainer) un Markdown cu secțiuni fixe:
1) Header + lineage block (run_id, input_snapshot_id, engine_version, assumptions_hash, source_registry_hash, provider_profile) 2) Verdict de audit (nu de investiție): conclusion_risk + allowed_score_usage 3) Snowflake cu coverage 4) What the data says (checks cheie explicate) 5) **What we don't know** (UNKNOWN-uri + cauze + remedii) 6) Valuation range + sensitivity + reverse DCF 7) Red flags 8) Counter-thesis 9) Manual review checklist 10) Footer: atribuire CC BY-NC-SA + not investment advice.
Reguli: memo-ul nu conține nicio afirmație fără sursă în artefacte (test snapshot pe fixture); interval, nu punct (false precision killer); memo fără sensitivity când ERP e folosit → refuz (gate D).
Formate: full / one-page tear sheet / plain English; board pack P3.

## 31. Portfolio Audit Minimal

Detaliat în §10.N. P2. Explicit **minimal**: fără VaR, fără corelații estimate din prețuri (risc #29), fără optimizer.

## 32. Dashboard Scope

Re-scope: dashboard sobru de audit, Streamlit (stack existent), API-only. Paginile existente P1–P5 rămân; se adaugă/transformă:

| Pagina | Conținut | Prioritate |
|---|---|---|
| 1. Company Audit | ticker selector; score_raw+coverage_pct; data_confidence grade+hartă; model_applicability+usage; conclusion_risk+drivers; top limitations; red flags; UNKNOWN clusters; provider degradation banner; drill-down lineage per câmp | P0 |
| 2. Data Confidence | mix quality/class; critical missing; stale; conflicts; official/pragmatic/manual split | P0 |
| 3. Model Applicability | clasificare; status+reason; recommended model; allowed usage; comparability warning | P0 |
| 4. Sensitivity | interval bear/base/bull; matrice DR×g; ERP sensitivity; TV contribution; reverse DCF; fragility | P1 |
| 5. Watchlist Audit | 4 găleți + manual review queue | P1 |
| 6. Thesis Tracker | viewer YAML; watch metrics; invalidation; status | P2 (viewer), P3 (editor) |
| 7. Decision Journal | listă decizii + context la data deciziei + post-mortem | P2 |
| 8. Portfolio Audit | weighted confidence/risk; concentrări; macro sensitivity; unknown exposure | P2 |
| 9. Memo Generator | buton generate + preview + download; moduri analyst/plain | P1 |
| 10. Source/Data Health | source registry; runs; freshness; legal scope; production readiness; validation links (extinde P4/P5 existente) | P0 |

Reguli UX nenegociabile (extind 6.2 din planul vechi): UNKNOWN niciodată ascuns; warnings vizibile ne-colapsate; source_quality/class/provider_profile vizibile; degradarea yfinance banner permanent; zero BUY/SELL/HOLD; vocabular: "research view", "conclusion risk", "manual review required"; footer persistent atribuire+disclaimer; API-only.


### 32.1 Dashboard Scope Control

The full master plan lists 10 possible dashboard pages. For the first usable audit dashboard, the maximum is 8 pages.

Initial dashboard pages:

1. Company Audit
2. Data Confidence
3. Model Applicability
4. Sensitivity
5. Watchlist Audit
6. Thesis Tracker
7. Decision Journal
8. Source/Data Health

Merged or deferred:

- Memo Generator is initially a CLI/report output, not a full dashboard page.
- Portfolio Audit remains P2 and should not be part of the first dashboard release.
- Board Pack / Plain English / Analyst mode split remains P3.

## 33. API Scope

Extensii FastAPI (nu se ating endpoint-urile existente). Fiecare răspuns derivat păstrează: run_id, input_snapshot_id, output_schema_version, engine_version, assumptions_hash, source_registry_hash. UNKNOWN behavior comun: componentă indisponibilă → câmp cu status=UNAVAILABLE + cauză, niciodată 500, niciodată omisă.

| Endpoint | Purpose | Input | Output | Persist | Tests |
|---|---|---|---|---|---|
| GET /companies | listă instruments cunoscute + last run | filtre query | listă {ticker, exchange, last_run, applicability.usage} | citește DB | contract |
| GET /companies/{t}/latest | output existent (există deja) | ticker | output_schema JSON + run meta | — | existent |
| GET /companies/{t}/audit | audit_summary complet | ticker[, run_id] | audit_summary.schema | citește audit tables | contract + UNKNOWN-preservation |
| GET /companies/{t}/data-confidence | doar componenta | idem | data_confidence.schema | idem | contract |
| GET /companies/{t}/model-applicability | idem | idem | model_applicability.schema | idem | contract |
| GET /companies/{t}/sensitivity | idem | idem | sensitivity_summary.schema | idem | determinism |
| GET /companies/{t}/red-flags | idem | idem | red_flags.schema | idem | contract |
| GET /companies/{t}/memo | ultimul memo + manifest | idem | memo_manifest + link fișier | citește memos | snapshot |
| POST /audit/company | rulează audit pe ultimul run sau run nou | {ticker, run_mode} | audit_summary | scrie audit tables | e2e offline |
| POST /audit/watchlist | triage | {watchlist_id sau CSV ref} | găleți + reasons | scrie | e2e offline |
| POST /audit/portfolio | portfolio audit | {holdings ref} | portfolio audit | scrie | e2e offline |
| GET /watchlists, GET /watchlists/{id}/audit | listare + ultimul triage | id | triage JSON | citește | contract |
| GET/POST /theses/{t} | citire/validare thesis + status | YAML body la POST (validat pe thesis.schema) | thesis + status | fișier + index | schema validation |
| GET/POST /decisions | journal | entry la POST | listă/entry | JSONL append-only | append-only test |
| GET /meta/runtime-summary | versiuni+hash-uri active | — | meta | — | contract |
| GET /meta/source-health | registry + freshness | — | raport | — | contract |
| GET /meta/legal-scope | legal scope report | — | raport | — | existent-style |
| GET /meta/production-readiness | gate combinat | — | raport | — | existent-style |

Auth: API key existent; CORS doar dashboard; bind localhost (scope intern).

## 34. CLI Scope

Toate sub `python -m sws_engine.cli`. Comune: exit 0 succes, 2 gate/not-ready, 1 eroare; `--continue-on-error` pe batch-uri (izolare per ticker, raport final PASS/FAIL/SKIPPED); offline tests pe fixture-uri; live tests marker `live` skipped by default.

### 34.1 CLI Implementation Priority

For Sprint P0.1, the only real CLI to implement is:

```bash
python -m sws_engine.cli audit-company \
  --ticker AAPL \
  --db data/sws.db \
  --output out/audit/AAPL
```

All other CLIs in this section are roadmap candidates and must remain P1/P2 unless explicitly promoted by a later implementation prompt.

Do not implement `audit-watchlist`, `refresh-sec-financials`, `refresh-rates-fred`, `generate-memo`, `compare-runs`, `portfolio-audit` or `thesis-status` in the same branch as P0.1.


| Comandă | Purpose | Parametri cheie | Output | Failure behavior | Acceptare |
|---|---|---|---|---|---|
| `audit-company --ticker AAPL --db … --output out/audit/AAPL` | audit summary per companie | --run-id opțional; --refresh | JSON+MD în out/ | run lipsă → exit 1 mesaj clar; componente lipsă → summary cu UNAVAILABLE, exit 0 | rulează pe demo fixture, schema-valid, UNKNOWN-uri conservate |
| `audit-watchlist --watchlist core.csv …` | triage | --continue-on-error default on | raport găleți | ticker eșuat → SKIPPED, restul continuă | 10 tickere mixte triate corect |
| `refresh-sec-financials --tickers AAPL,MSFT --output data/real_sources/sec --refresh` | fetch+normalize SEC | --live (altfel doar cache) | snapshots + mapping report | rețea picată → cache sau exit 2, fără date parțiale nemarcate | fixture-based offline test; live test skipped |
| `refresh-rates-fred --series DGS10 --output …/bond_yields_10y_curated.csv --requires-review` | rates | — | CSV + manifest review_status=draft | idem | manifest corect; production-readiness rămâne NOT_READY până la review |
| `validate-erp-curated --input erp_curated.json` | validare ERP | — | raport | status≠reviewed → exit 2 | testele de lifecycle |
| `enrich-identifiers --input universe_US_curated.csv --output identifier_master.csv` | identifier master | --cik-map local | CSV validat | duplicate/ambiguu → exit 1 cu listă | duplicate detectate |
| `generate-memo --ticker AAPL --db … --output out/memos/AAPL.md` | memo | --mode full/tearsheet/plain | MD + manifest | ERP fără sensitivity → exit 2 (gate) | snapshot test |
| `compare-runs --ticker AAPL --from-run R1 --to-run R2` | diff | — | diff checks/inputs/assumptions | run inexistent → exit 1 | diff detectează schimbare sintetică |
| `portfolio-audit --holdings holdings.csv --db … --output out/portfolio_audit` | audit portofoliu | — | JSON+MD | poziții fără run → listate ca UNKNOWN exposure | fixture test |
| `thesis-status --ticker AAPL` | evaluare thesis | — | status+reguli | YAML invalid → exit 1 cu erori schema | reguli neevaluabile degradează status |

## 35. Persistence and Data Model

Vezi §12. Migrații: aditive (CREATE TABLE IF NOT EXISTS), fără ALTER pe tabelele existente; script `init-db --upgrade` idempotent; test că o DB v3.1 existentă se deschide și funcționează după upgrade (backward compat).

## 36. Reporting Outputs

- `out/audit/<TICKER>/audit_<run_id>.{json,md}`
- `out/memos/<TICKER>_<date>.md` + `memo_manifest.json`
- `out/watchlist_audit/<name>_<date>.{json,md}`
- `out/portfolio_audit/<date>.{json,md}`
- `out/diffs/<TICKER>_<r1>_<r2>.md`
- Toate cu footer atribuire+disclaimer (gate) și lineage block.

---

## 37. Testing Strategy


### 37.1 P0 Minimum Test Pack

Before SEC/FRED/Sensitivity/Watchlist modules are implemented, P0 must pass the following tests:

| Test | Purpose |
|---|---|
| `test_data_confidence_high_medium_low_unknown` | determinism confidence |
| `test_data_confidence_yfinance_degraded` | yfinance degradation visible |
| `test_critical_missing_inputs` | missing FCF / ERP / bank fields |
| `test_model_applicability_bank_degraded` | JPM-like bank handling |
| `test_model_applicability_reit_degraded` | REIT handling |
| `test_model_applicability_etf_not_applicable` | fund / ETF exclusion |
| `test_conclusion_risk_high_when_unknown_many` | risk driven by missing data |
| `test_audit_summary_preserves_unknown` | no hidden UNKNOWN |
| `test_audit_report_contains_warnings_lineage` | Markdown compliance |
| `test_audit_company_cli` | end-to-end offline |

Golden fixtures required for P0:

- AAPL — standard mega-cap equity
- MSFT — standard quality compounder
- NVDA — high-growth sensitivity candidate
- JPM — bank / degraded
- O — REIT / degraded
- XOM — commodity cyclical

P0 is not complete until these tests pass offline.

**Niveluri:**
1. **Unit tests** — fiecare modul nou (confidence calc, applicability rules, conflict detector, XBRL resolver, thesis evaluator, red flag rules) pe cazuri sintetice cu valori cunoscute.
2. **Contract tests** — fiecare schemă auxiliară: exemple valide/invalide; fiecare endpoint nou: shape + meta obligatoriu (run_id, hashes).
3. **Schema validation tests** — output_schema existent rămâne gate; schemele auxiliare validate în CI pe artefacte demo.
4. **Golden company fixtures** — AAPL, MSFT, NVDA (standard), JPM (bank), O (REIT), XOM (commodity cyclical): payload + CompanyFacts fixture + expected audit_summary snapshot. **Notă onestitate:** fixture-urile sunt înregistrări reale datate (SEC/yfinance capturi) sau, până la populare, sintetice marcate DEMO_FIXTURE_ONLY — niciodată sintetic redenumit curated (G-05).
5. **Bank degraded model test** — JPM prin model standard forțat → applicability=not_applicable/degraded + do_not_compare.
6. **REIT degraded model test** — O fără AFFO → audit_only + recommended_model.
7. **yfinance degradation visible test** — există; se extinde: degradarea trebuie să apară și în data_confidence și în audit_summary (propagare, nu doar în warnings).
8. **UNKNOWN never hidden test** — pentru fiecare suprafață nouă (audit summary, memo, watchlist, portfolio audit): numărul de UNKNOWN la intrare == numărul reprezentat la ieșire.
9. **No fake data injected test** — honesty gate extins la data/real_sources/sec și overrides.
10. **Source conflict detector test** — două surse divergente pe revenue → conflict record + policy aplicată + fără blend.
11. **SEC raw-to-normalized test** — CompanyFacts fixture → snapshot normalizat cu valori exacte așteptate.
12. **XBRL missing tag test** — tag absent → câmp UNKNOWN + XBRL_TAG_MISSING, fără substituție.
13. **FRED rates missing source test** — CSV absent → discount rate UNKNOWN → valuation UNKNOWN (nu default silențios).
14. **ERP review status test** — draft/expired → gate blochează memo; reviewed → trece.
15. **Sensitivity matrix deterministic test** — același snapshot+grilă → hash identic al rezultatului; base scenario == run normal byte-identic.
16. **Reverse DCF test** — pe gold AMZN: implied growth rezolvat înapoi din FV cunoscut, toleranță ±0.1pp.
17. **Memo generation snapshot test** — fixture → memo MD stabil (snapshot), conține reason_codes, interval nu punct, footer.
18. **Dashboard smoke tests** — import + randare pagini noi pe date mock (pattern existent).
19. **API contract tests** — TestClient pe toate endpoint-urile noi.
20. **CI governance tests** — toate gate-urile din §38 au test care verifică că gate-ul însuși pică pe input rău (test-the-gate).

Plus: **override expiry test**, **append-only journal test**, **backward-compat DB upgrade test**, **thesis UNKNOWN degradation test**, **allowed_score_usage enforcement test** (screener refuză do_not_compare).

## 38. CI and Governance Gates

Extinderea `ci.yml` existent (toate offline):

| Gate | Nou/Existent | Comportament |
|---|---|---|
| pytest offline | existent | + testele noi |
| ruff | existent | + module noi |
| output_schema validation | existent | neschimbat |
| auxiliary schemas validation | **nou** | validează artefacte demo pe fiecare *.schema.json |
| no score_normalized primary usage | existent | extins la audit layer (grep pe src/, dashboard/) |
| attribution footer check | existent | extins la memo/tear sheet templates |
| no fake real data | existent | extins la sec/, overrides/, theses/ |
| legal_scope not loosened | **nou (blocking)** | diff pe config/legal_scope.yaml: flags true fără legal_review → fail |
| live tests skipped by default | existent | neschimbat |
| source_registry required fields | **nou** | tier/ttl/license_status prezente pentru toate sursele |
| UNKNOWN/warnings/lineage preservation | **nou** | testul de propagare §37.8 rulat ca gate |
| dashboard API-only | existent | extins la paginile noi |
| explainer completeness | **nou** | fiecare reason_code din enum are intrare în dictionary |
| base-formula immutability | **nou** | sensitivity base == run normal (G-07) |
| override expiry enforcement | **nou** | fixture cu override expirat → UNKNOWN |

Release gate: gold tests + audit snapshots + validation report nou per release (pattern existent).

## 39. Legal / Licensing / Use-scope Controls

- Scope: **internal / personal / educational only**; `commercial_use_enabled=false`, `external_access_enabled=false`, `legal_review_completed=false` — neschimbate de acest plan.
- **Not investment advice** — pe fiecare suprafață: dashboard footer (există), memo footer (nou, gate), API descriere (există), CLI banner.
- Fără deployment extern fără legal review (gate existent, devine blocking în CI).
- Fără modelul live SWS ca sursă de date sau metodologie (NOTICE existent; rămâne).
- Atribuire CC BY-NC-SA: footer + NOTICE + memo-uri (BY); NC respectat prin scope; SA relevant doar dacă se publică derivate — Not Now.
- Third-party licensing review: yfinance = pragmatic, nu production curated (există); SEC/FRED/Treasury = surse publice guvernamentale, candidate official/curated; ERP = ipoteză manual curated cu citare sursă, nu redistribuire de dataset; TradingView = **doar export CSV manual al utilizatorului**, fără scraping/API neoficial; CUSIP/ISIN comerciale — doar introduse manual de utilizator dacă are drept.

**Legal Stop Conditions (produsul BLOCHEAZĂ execuția/promovarea):**
- L1: external_access_enabled=true fără legal_review_completed=true → legal gate fail (există).
- L2: commercial_use_enabled=true fără review → idem (există).
- L3: memo/dashboard/raport fără atribuire → attribution gate fail.
- L4: source_registry conține provider plătit cu license_status=unreviewed marcat production_ready → source gate fail (nou).
- L5: fișier sample/synthetic redenumit *curated* → honesty gate fail (există, extins).
- L6: yfinance folosit ca sursă de tier official_filing pentru un câmp (field-level rules violate) → registry gate fail (nou).

## 40. Security and Local Deployment

Reutilizare scaffold existent (Docker, compose, .env, API key, bind localhost, ops/security.md). Adăugiri v4.0: directoarele noi (theses/, decisions/, memos/, sec cache) intră în volume + backup.sh; fișierele de decizie/teză pot conține raționamente personale → rămân locale, excluse din orice publicare de repo (gitignore); niciun secret în theses/decisions (lint simplu). Fără expunere publică; fără telemetrie.

## 41. Operational Runbook

Extinde runbook-ul existent:
- **Zilnic (opțional):** EOD refresh existent → batch watchlist → `audit-watchlist` → verifică Source/Data Health.
- **Săptămânal:** triage review; `thesis-status` pe holdings; verifică OVERRIDE_EXPIRING_SOON.
- **Lunar:** `portfolio-audit`; `refresh-rates-fred` + review manual; verifică ERP review_status.
- **Trimestrial:** `refresh-sec-financials` post-earnings pe holdings; re-run + `compare-runs`; post-mortem pe deciziile scadente.
- **La orice schimbare assumptions/audit_policies:** snapshot + diff vizibil (no silent changes) + re-run gold + audit snapshots.
- **Incidente:** production-readiness NOT_READY → nu se promovează nimic; conflict nerezolvat pe câmp critic → manual review item obligatoriu.

---

## 42. Product Roadmap by Phases

> Fiecare fază: Goal / Why / Componente / Fișiere / CLI / API / Dashboard / Inputs / Outputs / Source quality / UNKNOWN / Tests / Acceptance / Dependencies / Risks / Anti-patterns / DoD / Complexity / Priority. Fazele sunt secvențiale ca dependențe, dar 7–10 pot rula parțial în paralel.

### Faza 0 — Product Reframing & Governance Baseline  [P0, Low]
- **Goal:** repoziționare documentată + închiderea restanțelor v3.1 care blochează onestitatea.
- **Why:** fără docs normative în repo și fără surse curate reale, orice strat de audit ar audita pe fundație incompletă.
- **Componente:** commit `data_contract.md`, `check_engine_contract.md`, `test_suite.md`, `implementation_decisions.md`, `risk_register.md`, `runbook.md` din copiile locale (G4); acest plan în repo ca `PLAN-Produs-Audit-Engine-v4.0.md`; `docs/product_positioning.md`; `config/audit_policies.yaml` (schelet, gol funcțional); gate CI legal-scope-not-loosened.
- **CLI/API/Dashboard:** —.
- **Inputs:** copii locale model pack. **Outputs:** repo complet normativ.
- **UNKNOWN:** n/a. **Tests:** gate nou are test.
- **Acceptance:** production-readiness raportează aceleași blocking issues, dar toate docs referite există; CI verde.
- **Deps:** —. **Risks:** copiile locale pierdute → se marchează FILE_NOT_FOUND permanent și se rescriu doar cu aprobare explicită (nu silențios).
- **Anti-pattern:** a rescrie docs normative "din memorie" fără marcaj.
- **DoD:** repo self-contained normativ; plan v4.0 committed.

### Faza 1 — Audit Layer Foundation  [P0, Medium]
- **Goal:** scheletul audit layer: scheme auxiliare + audit_summary + audit-company CLI + pagina Company Audit minimă.
- **Why:** creează contractul pe care toate modulele următoare îl populează.
- **Componente:** `audit/` pachet; `schemas/aux/audit_summary.schema.json`, `data_confidence.schema.json` (v0), `model_applicability.schema.json` (v0), `conclusion_risk.schema.json` (v0); tabele DB aditive; lineage_index v0 (din input_lineage existent).
- **CLI:** `audit-company`. **API:** GET /companies/{t}/audit, POST /audit/company. **Dashboard:** pagina 1 (varianta minimă: score+coverage+warnings+UNKNOWN clusters+lineage).
- **Inputs:** run-uri existente. **Outputs:** audit_summary per run.
- **Source quality:** propagare 1:1 din output. **UNKNOWN:** test de non-pierdere din prima zi.
- **Tests:** contract + preservation + API + smoke dashboard.
- **Acceptance:** demo fixture → audit_summary valid; fiecare UNKNOWN din checks apare în unknown_clusters; DB v3.1 upgrade-abilă.
- **Deps:** F0. **Risks:** scheme prea rigide → versionare v0 explicită.
- **Anti-pattern:** a pune logica de scoring în agregator; agregatorul doar compune.
- **DoD:** W1 rulează cap-coadă în formă minimă.

### Faza 2 — Data Confidence + Model Applicability  [P0, Medium/High]
- **Goal:** cele două componente-cheie ale auditului, complete.
- **Componente:** `data_confidence.py` complet (criticality weights, staleness, split tiers); `model_applicability.py` cu clasificatoare + allowed_score_usage; extensie source_registry (tier, ttl, field rules v0); staleness score; `config/audit_policies.yaml` populat (praguri E2 documentate).
- **CLI:** parametri noi pe audit-company. **API:** GET data-confidence, GET model-applicability. **Dashboard:** paginile 2 și 3.
- **Inputs:** output+snapshot+registry. **Outputs:** grade A–E, applicability status, usage.
- **UNKNOWN:** clasificare incertă → UNKNOWN+audit_only; grade nu maschează coverage.
- **Tests:** yfinance_degraded vs complet; JPM/O/ETF; enforcement usage în screener.
- **Acceptance:** pe fixtures, grade-urile diferă corect; screener refuză do_not_compare cross-sector.
- **Deps:** F1. **Risks:** praguri arbitrare → toate în audit_policies cu owner+rationale (registru separat de assumptions model).
- **Anti-pattern:** confidence ca medie opacă; trebuie descompozabil pe câmpuri.
- **DoD:** W2 posibil manual (fără triage automat încă).
- **Priority/Complexity:** P0, High.

### Faza 3 — SEC-first Financial Statements  [P0/P1, High]
- **Goal:** statements US din filing oficial, normalizate, cu mapping report.
- **Componente:** tot §10.C; fixtures CompanyFacts pentru cele 6 golden; merge în payload prin tooling manual_inputs existent; conflict detector v1 (SEC vs yfinance).
- **CLI:** `refresh-sec-financials`. **API:** — (alimentează payload). **Dashboard:** split official/pragmatic în pagina 2 devine real.
- **UNKNOWN:** tag lipsă/trimestru lipsă/non-US → UNKNOWN marcat, fără substituție.
- **Tests:** §37.11–12 + conflict + reconciliation.
- **Acceptance:** AAPL payload cu statements tier=official_filing; mapping report complet; data_confidence AAPL crește demonstrabil vs yfinance-only.
- **Deps:** F2 (pentru a vedea efectul în confidence). **Risks:** XBRL tag drift; unit errors → reconciliation + teste exacte.
- **Anti-pattern:** "tag apropiat" nedeclarat; TTM din 3 trimestre anualizat.
- **DoD:** 6 golden au SEC snapshots fixture-izate; live fetch funcțional dar skipped în CI.

### Faza 4 — Rates, ERP, Macro Assumptions and Identifier Master  [P0/P1, Medium]
- **Goal:** deblocarea production-readiness (bond 10Y, ERP, universe) + identitate solidă.
- **Componente:** §10.D + §10.E; populare reală `bond_yields_10y_curated.csv`, `erp_curated.json` (reviewed), `universe_US_curated.csv`, `identifier_master.csv`.
- **CLI:** `refresh-rates-fred`, `validate-erp-curated`, `enrich-identifiers`. **Dashboard:** Source/Data Health arată readiness real.
- **Acceptance:** `production-readiness` → **PASS** pentru internal daily run (prima dată în istoria produsului); ERP lifecycle testat; duplicate tickers detectate.
- **Deps:** F0. **Risks:** ERP tratat ca adevăr → sensitivity_required + review lifecycle.
- **Anti-pattern:** a automatiza ERP "de pe net" fără review manual.
- **DoD:** rulare zilnică internă pe date reale permisă de gates.
- **Priority/Complexity:** P0 (rates/universe) / P1 (identifier extins), Medium.

### Faza 5 — Explainability, Reason Codes and UNKNOWN Narratives  [P0, Medium]
- **Goal:** fiecare FAIL/UNKNOWN explicat, template-driven, bilingv-registru (analyst/plain).
- **Componente:** `reason_code_dictionary.yaml`; `explain/`; integrare în audit_report, dashboard pagina 1, memo (mai târziu).
- **Tests:** completeness gate; snapshot pe fixture; AI-rewrite gate (dacă se activează).
- **Acceptance:** pe demo fixture, toate cele N FAIL/UNKNOWN au explicații cu valori reale interpolate; dicționar 100% acoperitor.
- **Deps:** F1. **Risks:** #26/#27 → template-driven by design.
- **Anti-pattern:** explicații generate liber de LLM prezentate ca fapt.
- **DoD:** "de ce e UNKNOWN?" are răspuns pe orice check, în UI și CLI.

### Faza 6 — Sensitivity, Valuation Range and Conclusion Risk  [P1, High]
- **Goal:** fragilitatea concluziei devine output de prim rang.
- **Componente:** §10.G complet + `conclusion_risk.py` complet + `config/sensitivity.yaml`.
- **CLI:** flag `--with-sensitivity` pe audit-company. **API:** GET sensitivity. **Dashboard:** pagina 4.
- **Tests:** §37.15–16 + base-immutability gate + reverse DCF pe gold AMZN.
- **Acceptance:** interval+matrice+TV%+reverse DCF pe AAPL fixture; conclusion_risk cu drivers enumerabili; base run byte-identic.
- **Deps:** F1–F2 (risk consumă confidence+applicability). **Risks:** #28 (modificarea formulelor) → runner pe copii de payload, gate.
- **Anti-pattern:** medii ponderate opace în conclusion risk.
- **DoD:** W3 (fără memo) complet.

### Faza 7 — Red Flags, Accounting Quality and Capital Allocation  [P1/P2, Medium/High]
- **Goal:** semnalele de "verifică manual".
- **Componente:** red_flags v1 (~15 reguli, §21) [P1]; capital allocation subset dividende/buyback/dilution/capex [P1]; accounting quality [P2]; solvency [P2]; business quality [P2].
- **API:** GET red-flags. **Dashboard:** secțiune în pagina 1.
- **Tests:** fiecare regulă pe fixture sintetic pozitiv+negativ+UNKNOWN.
- **Acceptance:** XOM/JPM/O fixtures produc flag-urile așteptate; zero flags fără evidence+lineage.
- **Deps:** F3 (statements). **Risks:** prag hardcodat → toate în audit_policies.
- **Anti-pattern:** scor agregat de "calitate contabilă".
- **DoD:** manual review checklist populat automat.

### Faza 8 — Watchlist Audit, Thesis Tracker and Decision Journal  [P1/P2, Medium]
- **Goal:** disciplina de proces.
- **Componente:** §10.K/L/M; `thesis.schema.json`, `decision_journal.schema.json`.
- **CLI:** `audit-watchlist`, `thesis-status`; journal prin API/fișier. **API:** watchlists, theses, decisions. **Dashboard:** paginile 5 [P1], 6–7 [P2].
- **Tests:** triage pe watchlist mixt; invalidation UNKNOWN degradation; append-only.
- **Acceptance:** W2, W4, W5 complete.
- **Deps:** F2 (triage consumă confidence+applicability). **Risks:** thesis rules prea vagi → doar reguli mașină-evaluabile pe câmpuri existente.
- **Anti-pattern:** decision journal care sugerează acțiuni.
- **DoD:** un ciclu complet thesis→run→status→decizie→post-mortem demonstrat pe fixture.

### Faza 9 — Investment Memo Generator and Reporting Layer  [P1, Medium]
- **Goal:** livrabilul uman final.
- **Componente:** §30; template-uri MD; memo_manifest.schema.json.
- **CLI:** `generate-memo`. **API:** GET memo. **Dashboard:** pagina 9.
- **Tests:** snapshot; interval-not-point gate; ERP-sensitivity gate; attribution gate extins.
- **Acceptance:** memo AAPL din fixtures: complet, stabil, fără afirmații fără sursă, "What we don't know" nevid pe fixture degradat.
- **Deps:** F5, F6, F7 (parțial ok fără F7 — secțiunea red flags devine UNAVAILABLE).
- **Risks:** #26 → compunere din artefacte, nu generare.
- **DoD:** W3 complet.

### Faza 10 — Portfolio Audit Minimal  [P2, Medium]
- **Goal:** vederea agregată a fragilității.
- **Componente:** §10.N. **CLI:** `portfolio-audit`. **API:** POST /audit/portfolio. **Dashboard:** pagina 8.
- **Acceptance:** W6 pe holdings fixture; poziții fără run → unknown exposure, nu excluse silențios.
- **Deps:** F2, F6. **Risks:** #29 → fără proxy-uri de corelație.
- **DoD:** portfolio memo generat.

### Faza 11 — Dashboard Re-scope  [P1, Medium]
- **Goal:** consolidarea celor 10 pagini + reguli UX; curățarea a ce nu mai e central (radar rămâne, dar sub audit header).
- **Acceptance:** fiecare pagină smoke-testată; UX rules gate-uite (attribution, UNKNOWN vizibil, API-only); zero vocabular BUY/SELL.
- **Deps:** fazele care produc datele fiecărei pagini. **Complexity:** Medium (Streamlit existent).

### Faza 12 — API/CLI/Productization  [P1, Low/Medium]
- **Goal:** completarea suprafeței API/CLI (§33–34), meta endpoints, exit codes uniforme, help/docs.
- **Acceptance:** toate endpoint-urile/CLI-urile din plan implementate sau marcate explicit deferred; API docs (/docs) actualizate.

### Faza 13 — CI, Validation, Governance and Release  [P0 continuu, Low]
- **Goal:** gate-urile din §38 complete + validation report v4.0.
- **Acceptance:** CI verde cu toate gate-urile noi; test-the-gate pentru fiecare; `validation_report_v4.0.md` cu verdict.

### Faza 14 — Local Deployment, Backup and Operations  [P2, Low]
- **Goal:** volume/backup/monitoring extinse la artefactele noi; runbook v4 (§41).
- **Acceptance:** backup include theses/decisions/memos/sec cache; restore testat o dată.

### Faza 15 — Future Extensions / Not Now List  [P3/Won't]
Explicit amânate: charting complex; real-time data; news/social sentiment; NLP pe 10-K; multi-user/auth avansat; mobile; optimizer de portofoliu; VaR/corelații; reverse DCF pe DDM/excess returns; OpenFIGI auto; editor thesis în dashboard; board pack mode; orice monetizare; orice expunere externă; score_normalized (rămâne interzis ca primar); scoruri compozite noi de "atractivitate".

---


## 42.1 Sprint P0.1 — Execution Slice

The master roadmap must not be implemented in one branch. The first implementation slice is deliberately narrow.

### Scope

Implement only:

1. Product Strategy Document
2. Audit Package Skeleton
3. Data Confidence v1
4. Critical Missing Inputs Map
5. Model Applicability v1
6. Conclusion Risk v1
7. Audit Summary
8. Audit Markdown Report
9. CLI `audit-company`
10. Docs Audit Methodology
11. Governance Gate: No Audit Hides UNKNOWN
12. Dashboard Minimal Company Audit Panel

### Explicitly out of scope for Sprint P0.1

- SEC CompanyFacts adapter
- FRED/Treasury live loader
- ERP curated workflow
- full identifier master
- source conflict detector
- sensitivity matrix
- reverse DCF
- red flag engine
- accounting quality
- capital allocation
- watchlist audit
- thesis tracker
- decision journal
- portfolio audit
- memo generator
- production-readiness PASS
- complex dashboard pages

### P0.1 Backlog

| Item | Objective | Proposed files | Tests | Definition of Done |
|---|---|---|---|---|
| P0.1.1 Product Strategy Document | Oficializează pivotul la Research Audit Engine | `docs/product_strategy_v4.md`, `docs/audit_engine_principles.md` | docs existence | documentul explică ce este / ce nu este produsul |
| P0.1.2 Audit Package Skeleton | Creează structura audit layer | `src/sws_engine/audit/__init__.py` | import test | package importabil |
| P0.1.3 Data Confidence v1 | Calculează HIGH/MEDIUM/LOW/UNKNOWN din output existent | `src/sws_engine/audit/data_confidence.py` | fixtures AAPL/JPM/yfinance | output cu source mix, missing inputs, warnings |
| P0.1.4 Critical Missing Inputs Map | Separă lipsuri minore de lipsuri critice | `src/sws_engine/audit/missing_inputs.py` | missing FCF, missing ERP, missing bank fields | critical list deterministă |
| P0.1.5 Model Applicability v1 | Returnează STANDARD_OK/DEGRADED/NOT_APPLICABLE/UNKNOWN | `src/sws_engine/audit/model_applicability.py` | bank, REIT, insurer, ETF | JPM/O degraded |
| P0.1.6 Conclusion Risk v1 | Returnează LOW/MEDIUM/HIGH/UNKNOWN | `src/sws_engine/audit/conclusion_risk.py` | high UNKNOWN, model degraded, yfinance | conclusion risk reason_codes |
| P0.1.7 Audit Summary | Agregă Data Confidence, Applicability, Risk | `src/sws_engine/audit/audit_summary.py` | snapshot JSON | `audit_summary.json` valid |
| P0.1.8 Audit Markdown Report | Raport citibil | `src/sws_engine/audit/audit_report.py` | Markdown snapshot | include UNKNOWN/warnings/lineage |
| P0.1.9 CLI `audit-company` | Rulează audit pe ultimul output persistat | `src/sws_engine/cli.py` | integration offline | JSON + MD generate |
| P0.1.10 Docs Audit Methodology | Explică metodologia audit | `docs/audit_methodology.md` | docs test | enumeră thresholds, UNKNOWN policy, limitations |
| P0.1.11 Governance Gate | Previne cosmetizarea UNKNOWN | `scripts/ci/check_audit_unknown_preserved.py` | CI test | eșuează dacă audit report nu include UNKNOWN |
| P0.1.12 Minimal Company Audit Panel | Afișare minimală UI | dashboard page/component | smoke | data_confidence/model_applicability/conclusion_risk vizibile |

### P0.1 Acceptance Criteria

Sprint P0.1 is complete only if:

- AAPL/MSFT/JPM/O fixtures can be audited offline.
- UNKNOWN is visible in JSON and Markdown.
- yfinance degradation is visible.
- JPM/O are marked DEGRADED.
- `audit_summary.json` is generated.
- `audit_report.md` is generated.
- `pytest` offline is green.
- Existing `checks/valuation/growth/portfolio` are not modified.
- `output_schema.json` is not modified.

## 43. Phase-by-phase Acceptance Criteria (sinteză verificabilă)

| Faza | Criteriu de acceptare verificabil (comandă/test) |
|---|---|
| 0 | repo conține toate docs normative; CI verde; gate legal-not-loosened activ |
| 1 | `audit-company --ticker DEMO` → audit_summary schema-valid; preservation test verde |
| 2 | confidence(complete) > confidence(degraded) pe fixtures; screener blochează do_not_compare |
| 3 | mapping report AAPL fără unmapped critice; conflict test verde; CI offline |
| 4 | `production-readiness` exit 0 pentru internal daily run |
| 5 | explainer completeness gate verde; snapshot explicații stabil |
| 6 | base-immutability gate verde; reverse DCF gold ±0.1pp; sensitivity determinist |
| 7 | 15 red flag rules cu triple-test (pos/neg/UNKNOWN) |
| 8 | ciclu thesis→status→decision→post-mortem pe fixture; journal append-only test |
| 9 | memo snapshot stabil; interval-not-point gate; ERP gate |
| 10 | portfolio audit cu unknown exposure corect pe fixture |
| 11 | 10 pagini smoke + UX gates |
| 12 | contract tests pe toată suprafața API nouă |
| 13 | toate gate-urile §38 + test-the-gate |
| 14 | backup+restore demonstrat |

---

## 44. Risk Register (v4.0, 32 riscuri)

Sev: C=critical, H=high, M=medium, L=low. Prob: H/M/L. Owner: model_owner (MO), engineering_owner (EO), data_owner (DO), operator (OP).

| # | Risc | Sev | Prob | Mitigare | Detection/Gate | Owner | Faze |
|---|---|---|---|---|---|---|---|
| 1 | False precision în fair value | C | H | interval obligatoriu + fragility + TV% | interval-not-point gate (memo/dashboard) | MO | 6,9,11 |
| 2 | Hidden UNKNOWN în straturile noi | C | M | propagare 1:1, test count-preservation | UNKNOWN-preservation gate | EO | 1–11 |
| 3 | yfinance tratat ca sursă oficială | C | M | field-level quality caps + tier | registry gate L6 | DO | 2,3 |
| 4 | Model aplicat pe tip greșit de companie | C | M | applicability gate + allowed_score_usage | JPM/O/ETF tests | MO | 2 |
| 5 | Bancă evaluată cu FCF standard | H | M | routing existent + APPLICABILITY_MISMATCH warning | bank degraded test | MO | 2 |
| 6 | REIT fără AFFO/FFO/NAV | H | M | audit_only + recommended_model | REIT degraded test | MO | 2 |
| 7 | ERP tratat ca dată obiectivă | H | H | review lifecycle + sensitivity_required | ERP status test + memo gate | DO | 4,6,9 |
| 8 | Terminal value domină valuarea nesemnalat | H | H | TV contribution + TV_DOMINATED flag | test TV% | MO | 6,7 |
| 9 | Date stale neflagate | H | M | TTL per sursă + staleness score | stale test + Source Health | DO | 2 |
| 10 | Manual override care nu expiră | H | M | expires_at obligatoriu | override expiry gate | DO | 2 |
| 11 | Conflict de surse rezolvat silențios | C | M | conflict detector + policy explicită sau UNKNOWN | conflict test | EO | 3 |
| 12 | Scor comparat cross-sector necomparabil | H | H | do_not_compare + screener enforcement | usage enforcement test | MO | 2,11 |
| 13 | Dashboard care induce gândire BUY/SELL | H | M | vocabular controlat + zero recomandări | grep gate vocabular + review UX | OP | 11 |
| 14 | Încălcare licență provider plătit | C | L | license_status în registry + L4 | source gate | OP | 4 |
| 15 | Scraping TradingView | H | L | doar CSV manual; interdicție documentată | code review + fără dependențe TV | EO | 13 |
| 16 | Legal scope drift | C | L | gate blocking legal-not-loosened | CI diff gate | OP | 0,13 |
| 17 | assumptions.yaml drift silențios | H | M | hash per run + diff dashboard (există) + audit_policies separat | compare-runs + gate | MO | toate |
| 18 | Breaking change în output_schema | C | L | G-06: doar scheme auxiliare | schema gate + PR review | EO | toate |
| 19 | CI dependent de internet | H | M | fixtures pentru SEC/FRED/yfinance | live marker + offline CI | EO | 3,4,13 |
| 20 | SEC XBRL tag mismatch | H | H | candidate list explicită + XBRL_TAG_MISSING | missing tag test + mapping report | DO | 3 |
| 21 | Eroare de normalizare unități | H | M | unit normalizer testat + reconciliation | raw-to-normalized exact test | DO | 3 |
| 22 | Currency mismatch | H | M | identifier_master currency vs payload validare | validare la load | DO | 3,4 |
| 23 | ADR mapping error | M | M | is_adr flag + primary_listing + warning | identifier tests | DO | 4 |
| 24 | Duplicate ticker / exchange ambiguity | M | M | cheie (ticker,exchange) + refuz pe ambiguu | enrich-identifiers exit 1 | DO | 4 |
| 25 | Overbuilding UI în loc de audit layer | M | M | dashboard sobru, faza 11 după 1–9 | roadmap gating + MoSCoW | OP | 11 |
| 26 | Memo generator halucinând dincolo de date | C | M | compunere din artefacte, nu generare | snapshot test + no-claim-without-source | EO | 9 |
| 27 | Explicație AI nelegată de reason_code | H | M | template-driven + AI gate (reason_code+valori verbatim) | explainer gate | EO | 5 |
| 28 | Sensitivity engine modifică formulele de bază | C | L | runner pe copii; base byte-identic | base-immutability gate | EO | 6 |
| 29 | Risc de portofoliu supraevaluat cu proxy slab de corelație | M | M | fără corelații estimate; doar concentrări declarate/UNKNOWN | scope review F10 | MO | 10 |
| 30 | Utilizatorul confundă audit-ul cu investment advice | C | M | disclaimer persistent + vocabular + decision journal ca proces, nu semnal | attribution/vocabular gates | OP | toate |
| 31 | Fixtures "golden" sintetice percepute ca date reale | H | M | DEMO_FIXTURE_ONLY marker + honesty gate | gate existent extins | DO | 3,13 |
| 32 | Audit layer devine el însuși un "scor magic" (conclusion_risk ca număr unic opac) | H | M | grade + drivers enumerabili, reguli lexicografice, fără medie opacă | design rule + test drivers nevid | MO | 6 |

---

## 45. Open Decisions

| # | Decizie | Opțiuni | Recomandare | Blochează |
|---|---|---|---|---|
| OD1 | Unde trăiesc pragurile de audit (confidence grades, risk rules) | assumptions.yaml vs registru nou | **`config/audit_policies.yaml` separat** — nu contaminăm registrul modelului SWS | F2 |
| OD2 | Fixtures golden: capturi reale datate vs sintetice marcate | real dated captures / synthetic | capturi reale SEC (public domain) + yfinance recorded, datate; sintetic doar unde captura nu e posibilă | F3 |
| OD3 | Reverse DCF: rezolvă growth sau margin | growth / margin / ambele | growth întâi (comparabil direct cu ruta A/B); margin P3 | F6 |
| OD4 | AI rewriting în explainer | on/off | **off by default**; template-only în v4.0 | F5 |
| OD5 | Persistență theses/decisions | fișiere vs DB | fișiere (YAML/JSONL) + index în DB — editabile uman, diff-abile în git | F8 |
| OD6 | Extindere `provider_profile` enum pentru SEC | da/nu | **nu** (G-06); tier per câmp în lineage index | F3 |
| OD7 | Universe BVB | acum / defer | defer P2 — US-first (SEC-first strategy) | F4 |
| OD8 | score_normalized | niciodată / experimental separat | **niciodată în v4.0** | — |

---

## 46. First 30 / 60 / 90 Day Plan

**Zile 1–30 — P0 Audit Foundation:**

Deliverables:

- `docs/product_strategy_v4.md`
- `docs/audit_methodology.md`
- `src/sws_engine/audit/data_confidence.py`
- `src/sws_engine/audit/model_applicability.py`
- `src/sws_engine/audit/conclusion_risk.py`
- `src/sws_engine/audit/audit_summary.py`
- `src/sws_engine/audit/audit_report.py`
- CLI `audit-company`
- `tests/audit/*`

Acceptance:

- AAPL/MSFT/JPM/O fixtures audited offline.
- UNKNOWN visible.
- yfinance degradation visible.
- JPM/O degraded.
- `audit_summary.json` generated.
- `audit_report.md` generated.
- pytest offline green.

**Zile 31–60 — Data and Sensitivity P1 Preparation:**

Deliverables:

- SEC raw CompanyFacts cache prototype.
- CIK resolver.
- minimal XBRL mapper.
- FRED DGS10 loader.
- ERP curated validator.
- `sensitivity_summary` v1.
- valuation range.
- reverse DCF prototype.

Acceptance:

- AAPL revenue/CFO/capex can be populated from SEC fixture.
- rates CSV supports review workflow.
- ERP requires `review_status`.
- sensitivity is deterministic.
- fair value is shown as range, not false precision.

**Zile 61–90 — Research Workflow:**

Deliverables:

- watchlist audit CLI.
- memo generator.
- dashboard Company Audit page.
- dashboard Watchlist Audit page.
- dashboard Source/Data Health.
- initial Thesis Tracker YAML schema.

Acceptance:

- watchlist split into 4 buckets.
- memos generated for AAPL/MSFT/JPM/O.
- dashboard consumes API only.
- no BUY/SELL/HOLD language.
- source health visible.

**Important:** `production-readiness PASS` remains a P1 milestone, not a dependency for Sprint P0.1. Audit foundation must be useful over existing persisted outputs even before curated real-source population is fully complete.

**Lunile 4–12 (roadmap 12 luni):**
- L4: F6 sensitivity + conclusion risk. L5: F7 red flags + capital allocation subset. L6: F8 watchlist/thesis/journal + F9 memo → **W1–W5 complete**.
- L7: F11 dashboard consolidat + F12 API/CLI. L8: F10 portfolio audit + F13 gates complete + validation report v4.0.
- L9–L12: F14 ops; accounting quality/solvency/business quality (P2); universe BVB (P2); buffer + post-mortems reale pe proces; review anual legal scope. **Fără extensii din F15.**

## 47. MoSCoW Prioritization

**MUST (P0):**

- Product Strategy / Audit Principles docs.
- Audit Summary + auxiliary schemas.
- Data Confidence v1.
- Critical Missing Inputs Map.
- Model Applicability Gate.
- Bank/REIT/ETF detectors.
- Conclusion Risk v1.
- Audit Report Markdown.
- CLI `audit-company`.
- UNKNOWN preservation gate.
- yfinance degradation visible.
- legal scope gate.
- Dashboard Company Audit minimal.

**SHOULD (P1):**

- Watchlist Audit.
- Investment Memo Generator.
- SEC CompanyFacts Adapter.
- SEC Frames API integration in averages builder.
- Stooq EOD price fallback.
- ECB/BNR FX primary source.
- FRED rates loader.
- ERP manual curated validator.
- Sensitivity Matrix.
- Valuation Range.
- Reverse DCF.
- Dashboard Source/Data Health.
- Source Conflict Detector.
- Explainability Layer + reason_code_dictionary if not completed in P0.

**COULD (P2):**

- Thesis Tracker.
- Decision Journal.
- Portfolio Audit Minimal.
- Run Comparison.
- Accounting Quality.
- Capital Allocation.
- Solvency.
- Business Quality.
- Identifier Master extended with FIGI/LEI.
- FFIEC CDR Call Reports for bank-specific fields.
- Universe BVB.
- Board Pack mode.
- Plain English / Analyst mode split.

**WON'T (for now):**

- Real-time data.
- Charting complex.
- News feed.
- Social sentiment.
- Mobile app.
- TradingView API/scraping.
- Commercial deployment.
- Paid subscription model.
- Backtesting strategy engine.
- ML price prediction.
- Auto BUY/SELL/HOLD.
- Public web deployment.
- Multi-user SaaS.
- Broker integration.
- Automated order execution.
- NLP on 10-K / transcripts.
- Portfolio optimizer / VaR / correlation engine.
- Score-normalized primary ranking.

## 48. Implementation Backlog (CORE ROADMAP — 20 capabilități)

| # | Capabilitate | Why it matters | Required inputs | Output | Deps | First slice | Acceptance |
|---|---|---|---|---|---|---|---|
| 1 | Data Confidence Score | separă calitatea datelor de a companiei | output+snapshot+registry | grade+hartă | F1 | grade din source_quality existent, fără staleness | degraded<complete pe fixtures |
| 2 | Critical Missing Inputs Map | spune exact ce lipsește și ce deblochează | data_contract criticality | câmp→checks→remediu | 1 | maparea MISSING_INPUT→checks | fiecare UNKNOWN mapat |
| 3 | Source Conflict Detector | elimină rezolvarea silențioasă | ≥2 surse per câmp | conflict records | SEC layer | SEC vs yfinance pe revenue/NI | test divergență |
| 4 | SEC CompanyFacts Adapter | filing oficial ca fundație | CIK map | raw facts cache | — | fetch+cache AAPL fixture | offline test |
| 5 | XBRL Normalizer | din tags în câmpuri engine | 4 | statement snapshot | 4 | 15 câmpuri critice | exact-values test |
| 6 | Model Applicability Gate | oprește comparații/modele greșite | identifier+payload | status+usage | F1 | bank/reit/fund/standard | JPM/O/ETF |
| 7 | Bank/REIT/Insurance Detectors | clasificare robustă | SIC+heuristici | classification | 6 | heuristici payload | precision pe golden |
| 8 | Valuation Range | ucide punctul unic | engine existent | [bear,base,bull] | F6 | deltas config pe DR și g | interval pe AAPL |
| 9 | Sensitivity Matrix | vede fragilitatea | 8 | matrice DR×g | 8 | 5×5 determinist | hash stabil |
| 10 | Reverse DCF | ce presupune piața | preț+model | implied growth | 8 | two_stage only | gold AMZN ±0.1pp |
| 11 | Terminal Value Contribution | expune dominanța TV | valuation detail | TV% + flag | 8 | % din FV | test >75% flag |
| 12 | Red Flag Engine | checklist de verificare manuală | statements+output | flags cu evidence | 5(SEC) | 5 reguli întâi | triple-test |
| 13 | Accounting Quality Module | semnale de calitate a raportării | SEC statements | metrici+semnale | 5 | accruals ratio | lineage complet |
| 14 | Capital Allocation Module | disciplina managementului | cashflow SEC | metrici+flags | 5 | dividende/buyback/dilution | fixture test |
| 15 | Watchlist Triage | alocă timpul de research | audit summaries | 4 găleți | 1,6 | reguli pe grade+usage | watchlist mixt |
| 16 | Thesis Tracker | disciplina ipotezelor | thesis YAML+runs | status | 1 | schema+evaluator | UNKNOWN degradation |
| 17 | Decision Journal | memorie anti-hindsight | context la decizie | jurnal | 1 | append JSONL+snapshot context | append-only |
| 18 | Investment Audit Memo | livrabilul final | toate artefactele | MD memo | 1,8,12,16 | template full mode | snapshot+gates |
| 19 | Run Comparison | "ce s-a schimbat" | 2 runs | diff structurat | DB existent | diff checks+assumptions hash | schimbare sintetică detectată |
| 20 | Personal Investment Constitution | reguli proprii mașină-verificabile | doc utilizator | `constitution.yaml` + verificare per audit (ex.: "nu research pe confidence<C", "nu compara cross-sector") | 1,6 | 5 reguli verificate în audit-company | încălcare → manual review item |

## 49. Definition of Done (global, per livrabil)

Un livrabil e DONE doar dacă: (1) are schemă/contract validat în CI; (2) are teste unit+contract+UNKNOWN-case; (3) UNKNOWN-preservation demonstrat; (4) lineage complet pe orice valoare afișată; (5) documentat în docs/ cu owner și clase de evidență pentru orice prag; (6) gate-urile relevante trec; (7) zero modificări în engine/schemă de bază (sau secțiune de impact aprobată); (8) apare în validation report-ul fazei; (9) rulează offline; (10) footer/disclaimer unde e suprafață umană.

## 50. Final Recommendation

Vezi verdictul complet mai jos. Pe scurt: **BUILD WITH LIMITATIONS** — direcția e corectă și refolosește masiv v3.1; limitările sunt scope-ul legal (intern, necomercial), dependența de curatarea manuală a surselor (ERP, universuri) și disciplina de a NU construi F15. Cea mai mare amenințare la adresa produsului nu e tehnică, ci scope creep-ul către "încă o platformă".

---

# VERDICT ȘI RECOMANDĂRI FINALE

**1. Verdict strategic: BUILD WITH LIMITATIONS.**
Limitări: (a) uz intern/personal/educațional exclusiv, fără monetizare/expunere fără legal review (CC BY-NC-SA); (b) SEC-first înseamnă US-first — non-US rămâne pragmatic/degradat; (c) ERP și universurile rămân curated manual, cu efort de operator recurent; (d) F15 rămâne închis 12 luni.

**2. Recomandare: CONTINUĂM.** Repoziționarea valorifică exact partea deja construită și greu de replicat (guvernanța onestității) și abandonează competiția pierdută din start (dashboard de scoruri). Oprirea ar arunca o infrastructură de audit funcțională; continuarea pe vechea direcție ar produce un SWS mai slab. Aceasta e a treia cale corectă.

**3. Poziționare într-o frază:** *Un motor personal de audit al research-ului de investiții care verifică dacă analiza unei companii este suficient de robustă — date, model, ipoteze, fragilitate — pentru a merita atenție, înainte de orice convingere.*

**4. Top 10 capabilități de dezvoltat primele:**
1. Audit Summary + scheme auxiliare (fundația contractuală)
2. Data Confidence Score + Critical Missing Inputs Map
3. Model Applicability Gate + allowed_score_usage (cu enforcement în screener)
4. Populare curated rates/ERP/universe → production-readiness PASS
5. Explainability Layer + reason_code_dictionary
6. SEC CompanyFacts Adapter + XBRL Normalizer (slice de 15 câmpuri)
7. Source Conflict Detector + staleness + override expiry
8. Valuation Range + Sensitivity Matrix + TV Contribution
9. Reverse DCF + Conclusion Risk Layer
10. Investment Audit Memo Generator (cu gates de onestitate)

**5. Top 10 lucruri de NU dezvoltat acum:**
1. Charting complex / radar interactiv avansat
2. Real-time market data / intraday
3. News feed / social sentiment
4. NLP pe 10-K/transcripts
5. Optimizer de portofoliu / VaR / corelații estimate
6. Multi-user, auth avansat, expunere externă
7. Integrare automată OpenFIGI/identificatori licențiați
8. score_normalized sau orice scor compozit nou de "atractivitate"
9. Editor de thesis în dashboard (fișier local e suficient)
10. Orice formă de monetizare sau clonare TradingView/Koyfin/SWS

**6. Roadmap 30/60/90:** vezi §46 — 30: F0+F1 (W1 minim); 60: F2+F4 (production-readiness PASS, confidence real); 90: F3+F5 (SEC-first + explainability).

**7. Roadmap 12 luni:** vezi §46 — L4 sensitivity+risk; L5 red flags+capital allocation; L6 workflow+memo (W1–W5 complete); L7 dashboard+API; L8 portfolio+gates+validation v4.0; L9–12 P2-uri, ops, consolidare, review legal anual.

**8. Fișiere/documente de creat ulterior:**
`PLAN-Produs-Audit-Engine-v4.0.md` (acest doc, în repo); `docs/product_positioning.md`; `config/audit_policies.yaml`; `config/sensitivity.yaml`; `config/reason_code_dictionary.yaml`; `schemas/aux/{audit_summary, data_confidence, model_applicability, conclusion_risk, sensitivity_summary, red_flags, thesis, decision_journal, memo_manifest, source_conflict, identifier_master}.schema.json`; `data/overrides/overrides.yaml`; `data/theses/`, `data/decisions/decisions.jsonl`; `docs/sec_mapping.md`; `docs/audit_layer_runbook.md`; `docs/personal_investment_constitution.md` + `config/constitution.yaml`; `validation/validation_report_v4.0_*.md`; plus commit-ul docs normative v3.1 restante (G4).

**9. Primele 5 prompturi de implementare incrementală (după aprobare):**
1. *"Faza 0: commit docs normative model pack din copiile locale + adaugă PLAN-Produs-Audit-Engine-v4.0.md + gate CI legal-scope-not-loosened cu test. Zero modificări în engine/schemas/dashboard. Livrează diff-ul și dovada CI verde."*
2. *"Faza 1 slice 1: creează schemas/aux/audit_summary.schema.json v0 + modulul audit/audit_summary.py care compune, dintr-un run existent, unknown_clusters, warnings, lineage links (run_id, input_snapshot_id, assumptions_hash). Test de UNKNOWN-preservation. Fără logică de scoring."*
3. *"Faza 1 slice 2: CLI audit-company + GET /companies/{ticker}/audit + tabelă audit_summaries aditivă + test contract API. DB v3.1 trebuie să rămână deschizibilă (test upgrade)."*
4. *"Faza 2 slice 1: data_confidence.py cu grade A–E din source_quality existent (fără staleness încă), praguri în config/audit_policies.yaml (E2, documentate), test degraded<complete pe fixtures existente."*
5. *"Faza 2 slice 2: model_applicability.py cu clasificare bank/insurance/reit/fund/loss_making/standard din payload + identifier stub, allowed_score_usage, enforcement în screener (refuz do_not_compare), teste JPM/O/ETF sintetice."*

**10. Confirmare explicită:**
- ✅ no code changed — acest livrabil este exclusiv un document de planificare;
- ✅ no repo modification — nu s-a creat branch, commit sau patch;
- ✅ no output_schema changes proposed as mandatory — toate extensiile sunt scheme auxiliare separate (G-06, OD6);
- ✅ UNKNOWN policy preserved — extinsă, cu gate de preservation pe fiecare strat nou;
- ✅ no fake data — strict mode menținut; honesty gates extinse; fixtures marcate;
- ✅ no investment advice — zero BUY/SELL/HOLD; vocabular de audit; disclaimere pe fiecare suprafață;
- ✅ legal/internal scope preserved — internal_personal_educational; commercial/external false; Legal Stop Conditions L1–L6 definite ca gates.


## Appendix A — Safe Follow-up Prompt Sequence

### Prompt 1 — P0 Audit Layer Implementation Spec

Extinde doar P0 Audit Layer Foundation pentru SWS Snowflake Engine v4.0.

Nu implementa cod încă.
Nu modifica `output_schema.json`.
Nu modifica `checks/valuation/growth/portfolio`.

Livrează specificație de implementare pentru:

- `data_confidence.py`
- `missing_inputs.py`
- `model_applicability.py`
- `conclusion_risk.py`
- `audit_summary.py`
- `audit_report.py`
- CLI `audit-company`
- `tests/audit/*`

Include function signatures, enums, reason_codes, input/output examples, UNKNOWN behavior, yfinance degradation behavior, tests și acceptance criteria.

### Prompt 2 — Implement P0 Audit Layer

Implementează doar P0 Audit Layer Foundation conform specificației aprobate.

Scope strict:

- `src/sws_engine/audit/*`
- `tests/audit/*`
- `docs/audit_methodology.md`
- CLI `audit-company`

Nu modifica `output_schema.json`.
Nu modifica `checks/valuation/growth/portfolio`.
Nu introduce date reale false.
Rulează pytest offline și gate-urile existente.
Livrează raport PASS WITH LIMITATIONS sau FAIL.

### Prompt 3 — SEC/FRED/ERP Data Layer Spec

Definește specificația pentru SEC-first Financial Data Layer + FRED rates + ERP manual curated.

Nu implementa cod.

Include CIK resolver, CompanyFacts raw cache, XBRL normalizer, statement snapshot, FRED DGS10 loader, ERP validator, review_status lifecycle, lineage și teste offline.

### Prompt 4 — Sensitivity and Valuation Range Spec

Definește Sensitivity Engine fără să modifici formulele existente.

Include:

- bear/base/bull
- discount rate x terminal growth
- ERP sensitivity
- FCF margin sensitivity
- terminal value contribution
- reverse DCF
- valuation fragility
- false precision killer
- tests

### Prompt 5 — Watchlist/Memo/Dashboard Re-scope

Definește implementarea Watchlist Audit + Memo Generator + dashboard re-scope.

Dashboard API-only.
UNKNOWN/warnings/source_quality/source_class vizibile.
Fără BUY/SELL/HOLD.

Include endpointuri, CLI, markdown outputs, tests și acceptance criteria.


## Appendix B — Data Source Inventory Reference

A separate source inventory document exists as `Inventar-Surse-Date-v4.0.md`. It should be stored next to this master plan and treated as a supporting planning artifact for source feasibility, free-first prioritization, and provider licensing review. Its operational deltas are already incorporated in §13.1 and §47.

---

*Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St (Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. Acest document este planificare internă, uz personal/educațional. Nu este consultanță de investiții.*
