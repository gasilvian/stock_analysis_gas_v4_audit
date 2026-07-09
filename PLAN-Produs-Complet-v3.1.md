# Plan de implementare — Produs complet SWS Snowflake Engine + Dashboard

**Baseline:** engine v3.1 Faza 1+2 (32/32 teste, gold tests calibrate)
**Obiectiv:** produs rulabil zilnic, cu date reale, persistență, API și dashboard, guvernat conform model pack-ului.
**Structură:** 6 faze (3→8), fiecare cu taskuri concrete, criterii de acceptare și dependențe.

---

## Constrângere legală de citit ÎNAINTE de orice altceva

Metodologia sursă este **CC BY-NC-SA 4.0**:

- **NC (non-comercial):** dashboard-ul poate fi folosit personal/educațional/intern. Orice deployment comercial (abonamente, acces plătit, folosire în serviciu de consultanță) necesită review legal ÎNAINTE de a începe Faza 6.
- **BY (atribuire):** footer-ul dashboard-ului și fiecare raport trebuie să conțină atribuirea către Simply Wall St + link la repo-urile publice (există deja în `legal/NOTICE.md`; trebuie propagat în UI).
- **SA (share-alike):** dacă publici documentația derivată, trebuie licență compatibilă.
- Disclaimer "not investment advice" obligatoriu pe fiecare ecran cu scoruri/valori (risc din `risk_register.md`).

**Decizie de luat acum (blochează scoping-ul Fazei 6):** produsul e doar pentru uz propriu, sau va fi expus altora? Dacă doar uz propriu → tot planul de mai jos e valabil fără review legal.

---

## Faza 3 — Data layer real (provideri, medii de piață, rate)

Scop: engine-ul primește acum payload-uri manuale; trebuie să și le poată construi singur din surse reale.

### 3.1 Provider yfinance live (`providers/yfinance_live.py`)

1. **Capability matrix reală** (`providers/capability_matrix.py`): tabel câmp-cu-câmp `data_contract.md` → câmp yfinance → calitate (`exact`/`approximation`/`missing`). Punct de plecare: lista `YFINANCE_UNAVAILABLE_FIELDS` din stub.
2. **Mapper de câmpuri:** `info`, `balance_sheet`, `financials`, `cashflow`, `dividends`, `splits` → payload conform contractului. Reguli stricte:
   - `intangible_assets` din balance sheet doar dacă raportat explicit; altfel `missing` (NU deduce din diferențe) — altfel PB devine `exact` fals (risc P0 din registru).
   - `dps_history_10y`: agregare anuală din seria `dividends`; sub 10 ani calendaristici compleți → lista scurtă (engine-ul aplică deja FAIL_BY_DEFAULT).
   - `eps_history`, `capex_history_3y`, `operating_cash_flow` din statements anuale.
   - `analyst_estimates`/`fcf_estimates`: yfinance NU are FCF forward per an cu număr de analiști → rămân `missing` + `PROVIDER_LIMITATION` (deja implementat în engine). NU improviza din `growth` yfinance.
3. **Normalizare monedă/unitate:** toate valorile în moneda de raportare; atașează `financials_as_of`, `price_as_of` reale în lineage.
4. **Retry + cache local** (vezi 3.5) — yfinance are rate limits informale.
5. **Teste:** fixture-uri înregistrate (răspunsuri yfinance salvate ca JSON, fără rețea în CI); test că fiecare câmp `missing` produce degradare vizibilă în output.

**Acceptare 3.1:** `python -m sws_engine.cli company -i <ticker>.json` unde payload-ul e generat de `build_payload_yfinance("AAPL")`; output valid pe schemă; toate degradările vizibile în warnings; zero câmpuri inventate.

### 3.2 Workflow inputuri curate/manuale (`providers/manual_inputs.py` + tooling)

1. Template-uri de input: `templates/company_input_template.json` cu toate câmpurile din `data_contract.md`, comentate (ce e obligatoriu, ce cade pe UNKNOWN).
2. Validator CLI: `sws-engine validate-input -i file.json` → raport câmpuri lipsă + ce checks vor deveni UNKNOWN (dry-run pe capability).
3. Merge tool: bază yfinance + override manual (estimări analiste, AFFO/FFO/NAV, date bănci) → profil `sws_public_faithful_manual_inputs` doar când override-urile acoperă câmpurile critice; altfel rămâne `yfinance_pragmatic`.

**Acceptare 3.2:** poți completa manual un fișier pentru o bancă (NPL/depozite) și un REIT (AFFO) și obții rulări complete cu variantele corecte de valuation și health.

### 3.3 Industry & market averages builder (`averages/builder.py`)

Cerințe din SPEC §7 — fiecare medie publicată cu: nivel (țară→regiune→global), tip metrică, dată sursă, provider, număr minim de instrumente, excluderi (listări secundare, fonduri, DR-uri).

1. **Definirea universului:** listă de tickere pe piață/industrie (fișier CSV curat versionat; pentru BVB — listă manuală, coverage yfinance validat per ticker conform notei din spec).
2. **Metrici de calculat:**
   - `pe_median_profitable` (piață + industrie): doar companii cu EPS > 0.
   - `pb_average` (industrie): PB din tangible BV unde e calculabil; altfel exclus din agregat, nu aproximat.
   - `eps_growth`, `roa` (industrie), `net_income_growth`, `revenue_growth` ponderate (piață).
   - Percentile yield: `dividend_yield_p10/p25/p75` pe piață.
   - `savings_rate`, `cpi` — tabel curat manual per țară (nu există în yfinance) → `assumption`.
3. **Fallback ierarhic:** industrie-țară → industrie-regiune → industrie-global; sub `min_universe_count` (config, sugestie 10) → nivelul următor + warning.
4. **Persistență:** snapshot zilnic JSON/parquet cu `industry_averages_as_of` (intră direct în lineage).
5. **Teste:** universe sintetic cu valori cunoscute → percentile/mediane exacte; test fallback când universul e sub prag.

**Acceptare 3.3:** `sws-engine build-averages --market US --date 2026-07-08` produce snapshot folosibil direct în payload; V3/V4/V6/P1/P6/F2/F3/D1/D2 trec din UNKNOWN în evaluate pe un ticker real.

### 3.4 Rate și FX (`rates/`)

1. `risk_free_rate_10y_5y_avg`: serie 10Y government bond per țară → medie 5 ani. Sursă: CSV curat (FRED/BNR export manual) versionat în repo; loader cu dată.
2. `equity_risk_premium`: tabel curat per țară (stil Damodaran), versionat, cu dată — deja prevăzut ca assumption/curated în spec.
3. FX EOD: yfinance (`EURUSD=X` etc.) cu cache; folosit de portfolio engine (`fx_as_of` în lineage).

**Acceptare 3.4:** discount rate se calculează automat pentru un ticker US și unul RO fără câmpuri manuale de rate.

### 3.5 Cache & refresh (`data/cache.py`)

- Cache pe disc (parquet/JSON) cu TTL: prețuri/FX = EOD (nu re-fetch intra-day decât forțat); financials = 7 zile; averages = zilnic conform runbook.
- Invalidatoare explicite (`--refresh`); toate fetch-urile logate cu timestamp → intră în `provider_versions`.

**Efort estimat Faza 3:** cea mai mare fază de date; punctele critice sunt capability matrix-ul onest (3.1) și averages builder-ul (3.3) — restul e plumbing.

---

## Faza 4 — Persistență și orchestrare batch

Scop: rulări repetabile, istoric interogabil, fundația pentru API/dashboard.

### 4.1 Schema DB (SQLite pentru început; interfață compatibilă Postgres)

Tabele:

| Tabel | Conținut cheie |
|---|---|
| `instruments` | ticker, exchange, company_type, currency, industry, market |
| `input_snapshots` | payload complet JSON + hash + provider_profile + timestamp |
| `runs` | run_id, valuation_date, assumptions_hash, engine_version, status |
| `outputs` | run_id → output JSON complet (validat pe schemă) + coloane extrase pentru query: fair_value, price, discount_pct, score_raw per axă, coverage per axă |
| `checks` | run_id, axis, id, result, reason_code (pentru filtrare în screener) |
| `averages_snapshots` | market/industry, date, JSON |
| `portfolios` | definiție portofoliu + tranzacții |
| `portfolio_runs` | output portofoliu per dată |

Reguli: output-ul JSON e sursa de adevăr; coloanele extrase sunt doar index de căutare. `assumptions.yaml` se hash-uiește per run (deja există run snapshot — se leagă de `runs.assumptions_hash`).

### 4.2 Batch runner (`orchestration/batch.py`)

1. `sws-engine batch --tickers watchlist.txt --date 2026-07-08` → construiește payload per ticker (provider ales), rulează, scrie în DB + snapshot fișier.
2. Izolarea erorilor: un ticker eșuat nu oprește batch-ul; raport final cu PASS/FAIL/SKIPPED per ticker.
3. Concurență limitată (thread pool mic — yfinance rate limits).

### 4.3 Scheduler și runbook operațional

- Cron/Task Scheduler: (1) EOD prices+FX, (2) averages daily, (3) batch pe watchlist, (4) portfolio run.
- Implementarea regulilor de refresh deja scrise în `runbook.md` — planul doar le automatizează.

**Acceptare Faza 4:** două rulări în zile diferite pentru același ticker sunt interogabile istoric; poți răspunde la "cum a evoluat scorul Health la X în ultimele 30 de zile" cu un SELECT.

---

## Faza 5 — API (FastAPI)

Scop: decuplarea dashboard-ului de engine; contract stabil.

### 5.1 Endpoints

| Metodă | Rută | Rol |
|---|---|---|
| POST | `/analyze/company` | payload → output (rulare on-demand, opțional persist) |
| GET | `/companies/{ticker}/latest` | ultimul output |
| GET | `/companies/{ticker}/history?axis=health` | serii istorice de scoruri |
| GET | `/companies/{ticker}/checks?result=UNKNOWN` | filtrare checks |
| POST | `/analyze/portfolio` | payload portofoliu → output |
| GET | `/portfolios/{id}/latest`, `/history` | istoricul portofoliului |
| GET | `/screener?axis=value&min_score=4&min_coverage=0.8` | screener pe outputs |
| GET | `/averages/{market}/{date}` | snapshot medii |
| GET | `/assumptions/current` | assumptions.yaml activ + hash |
| GET | `/meta/health` | versiune engine, ultima rulare batch |

### 5.2 Reguli de contract

- Response = exact output-ul validat pe `output_schema.json` (fără re-modelare) + metadate run.
- Erorile de input → 422 cu lista câmpurilor lipsă (refolosește `InputContractError`).
- **Screener-ul expune obligatoriu coverage lângă scor** — interzis să sortezi doar după `score_raw` fără coverage vizibil (regula anti-comparabilitate-falsă din runbook §4).
- Auth minim: API key în header (suficient pentru uz propriu); CORS doar pentru originea dashboard-ului.

**Acceptare Faza 5:** dashboard-ul (Faza 6) nu are nevoie de niciun acces direct la DB sau engine; totul trece prin API. Test de contract API în CI.

---

## Faza 6 — Dashboard

### 6.0 Decizie de stack (prima zi a fazei)

| Opțiune | Când o alegi |
|---|---|
| **Streamlit** (recomandat pentru start) | uz propriu, timp scurt, iterare rapidă; poate consuma direct API-ul; livrabil într-o săptămână de lucru efectiv |
| React + FastAPI | dacă vrei UI multi-user, componente custom (radar interactiv), tema proprie; adaugă buildchain și mult timp |

Recomandare: **Streamlit acum**, cu API-ul din Faza 5 ca strat stabil — dacă migrezi ulterior la React, API-ul rămâne neschimbat.

### 6.1 Pagini și componente

**P1. Company view** (pagina centrală)
1. Header: ticker, exchange, provider_profile (badge colorat: verde=faithful, portocaliu=yfinance_pragmatic), valuation_date.
2. **Snowflake radar** (pentagon, 5 axe, 0–6). Regulă de afișare: opacitatea/umplerea axei scalată cu `coverage_pct`; tooltip pe axă = known/unknown counts. NIciodată scor fără coverage vizibil.
3. Valuation card: model + variant + source_class, fair value vs price, discount%; pentru `manual_input`/`nav_fallback` — badge explicit "E3/manual".
4. Tabel checks: 30 rânduri, filtrabil pe result/reason_code; UNKNOWN colorate distinct (gri, nu roșu — nu e FAIL); coloane source_quality și source_class vizibile; expandable → inputs + threshold + input_lineage per check.
5. Panou warnings: întotdeauna vizibil (nu colapsat) când există `PROVIDER_LIMITATION`/`ASSUMPTION_USED`/`DEMO_FIXTURE_ONLY`.
6. Lineage footer: price_as_of, financials_as_of, averages_as_of, assumptions hash.
7. Istoric: linie score_raw per axă în timp (din `/history`).

**P2. Portfolio view**
1. Tabel poziții: weight curent, gain, TR, AYI, CAGR (cu marcaj "suprimat AYI<1" unde e cazul).
2. Split preț vs FX per poziție și total (bar chart stacked).
3. Snowflake portofoliu ponderat + **tabel contributori per axă** (invariantul din SPEC 8.2 afișat: suma contributorilor = scorul axei).
4. Badge ETF-uri excluse din Snowflake.
5. Acțiuni corporative aplicate (log: splits, reinvestiri).

**P3. Screener**
- Filtre: piață/industrie, scor minim per axă, **coverage minim obligatoriu în filtru (default 0.66)**, discount%, result-ul unui check specific.
- Tabel rezultate cu mini-snowflake per rând.

**P4. Run & data health**
- Ultimele batch-uri: PASS/FAIL/SKIPPED per ticker, motive.
- Vârsta datelor: averages_as_of, prices_as_of per piață; alertă vizuală când depășesc TTL-ul din runbook.
- Assumptions active: dump `assumptions.yaml` + hash + diff față de rularea anterioară (regula "no silent changes").

**P5. Assumptions & governance (read-only)**
- Registrul E1/E2/E3 randat din YAML cu owner, confidence, override policy.
- Link la validation report-ul curent.

### 6.2 Reguli UX nenegociabile (derivate din risk register)

1. Disclaimer persistent în footer pe toate paginile + atribuire CC BY-NC-SA.
2. UNKNOWN nu se ascunde și nu se normalizează nicăieri; nu există "score %".
3. Profilul yfinance_pragmatic afișează permanent bannerul de aproximare.
4. Orice valoare cu `source_quality != exact` are marker vizual (asterisc/culoare) — cerință explicită din runbook §4.

### 6.3 Taskuri tehnice Streamlit

1. `dashboard/app.py` + pagini în `dashboard/pages/`; client API subțire (`dashboard/api_client.py`).
2. Radar: `plotly` scatterpolar (suportă opacity per axă); checks table: `st.dataframe` cu column_config; istoric: `plotly` line.
3. Config: `DASHBOARD_API_URL`, `API_KEY` din env.
4. Teste smoke: pornire app + randare P1 pe demo fixture (playwright opțional; minim un test de import și de build al fiecărei pagini cu date mock).

**Acceptare Faza 6:** demo end-to-end: batch pe 10 tickere → deschizi dashboard → company view complet cu radar+coverage, screener funcțional, portfolio view cu invariantul contributorilor vizibil.

---

## Faza 7 — Validare, CI și guvernanță de release

1. **CI (GitHub Actions):** pytest (fără rețea — fixture-uri înregistrate), validare schemă pe demo outputs, lint (ruff), verificare că `score_normalized` nu apare nicăieri în cod (grep gate), verificare atribuire în UI footer.
2. **Gold gate per release:** cele 5 gold tests + testul de seed policy rulează la fiecare tag; orice schimbare de `assumptions.yaml` cere re-rulare și snapshot nou în `validation/`.
3. **Validation report:** completează `validation_report_template.md` o dată, cu rezultatele gold reale (există deja toate numerele) → verdict "PASS with limitations" documentând: seed policy E1, yfinance degradări, averages builder ca sursă proprie.
4. **Versionare:** semver pe engine; `engine_version` scris în fiecare run din DB.

---

## Faza 8 — Deployment & operare

1. **Docker:** imagine unică cu engine+API; Streamlit în container separat; `docker-compose.yml` cu volume pentru DB/cache/snapshots.
2. **Backup:** DB + `validation/snapshots` + `config/` zilnic (simplu rsync/copy).
3. **Monitoring minim:** log rotativ, alertă (email/notificare) când batch-ul are >20% FAIL sau când averages depășesc 3 zile vechime.
4. **Securitate:** dashboard-ul NU se expune public fără auth; dacă e doar local — bind pe localhost.

---

## Ordinea de execuție și dependențe

```
3.1 yfinance live ──┐
3.3 averages ───────┼──> 3.2 merge manual ──> 4 DB+batch ──> 5 API ──> 6 dashboard
3.4 rates/FX ───────┘                                   └──> 7 CI/validare (paralel cu 5-6)
                                                             8 deployment (ultimul)
```

Primele 3 acțiuni concrete de mâine:
1. Scrie capability matrix-ul yfinance câmp-cu-câmp (3.1.1) — decide onest ce e `exact`/`approximation`/`missing`.
2. Alege și fixează universul de tickere pentru averages (3.3.1) — fără el, jumătate din checks rămân UNKNOWN pe date reale.
3. Ia decizia legală de scop (uz propriu vs expunere) — determină dacă Faza 6 are nevoie de review înainte de start.

## Riscuri principale ale acestor faze

| Risc | Impact | Control |
|---|---|---|
| yfinance schimbă API/format | batch-uri picate | capability matrix + fixture-uri înregistrate + cache |
| Averages construite pe univers prea mic | scoruri instabile | `min_universe_count` + fallback ierarhic + warning |
| Coverage scăzut interpretat ca scor slab | decizii greșite | reguli UX 6.2 + screener cu coverage obligatoriu |
| Deployment comercial pe licență NC | risc legal | decizie de scop înainte de Faza 6; review legal dacă e cazul |
| Drift silențios de assumptions | rezultate necomparabile | hash assumptions per run + diff în dashboard P4 |
