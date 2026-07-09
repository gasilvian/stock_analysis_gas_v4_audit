# Validation Report v3.1 — Final Remaining Controls

## 1. Executive conclusion

- Validation date: 2026-07-08
- Version validated: v3.1 final controls candidate (118 passed, 2 skipped)
- Verdict: PASS WITH LIMITATIONS

## 2. Scope validated

This validation covers the remaining productionization controls after F/G/H:

- legal/use-scope gate;
- production source registry;
- real-source population workflow;
- production-readiness CLI;
- source-registry validation;
- final runbook for real data population.

## 3. Important limitation

The system now contains the mechanisms to populate and validate real/curated sources, but the package cannot itself decide legal scope for an external/commercial deployment. It defaults to internal, non-commercial use and blocks external/commercial mode until legal review is explicitly recorded.

The package also does not bundle proprietary or paid datasets. Real universe, rates, ERP and FX files must be supplied as versioned curated exports by the user/operator.

## 4. Controls added

| Control | Status | Notes |
|---|---|---|
| `config/legal_scope.yaml` | PASS | Defaults to internal/non-commercial use. |
| `legal-scope-report` CLI | PASS | Fails if external/commercial use lacks legal review. |
| `config/source_registry.yaml` | PASS WITH LIMITATIONS | Identifies required real/curated sources and template replacements. |
| `source-registry-report` CLI | PASS | Shows required sources that are not production-ready. |
| `production-readiness` CLI | PASS | Combines legal + source readiness. |
| `populate-real-sources` CLI | PASS WITH LIMITATIONS | Uses yfinance live provider where installed/network available. |
| `docs/real_data_population_runbook.md` | PASS | Documents the remaining operational process. |

## 5. Model-risk judgement

- Fit for internal prototype: yes.
- Fit for internal daily pilot: yes, after user supplies real/curated universe/rates/FX files and accepts yfinance limitations.
- Fit for external/commercial deployment: no, unless legal review is completed and recorded.
- Fit as investment advice: no.

## 6. Required operator action

1. Populate `data/real_sources/universe/*_curated.csv` with real validated universes.
2. Populate `data/real_sources/rates/*` and `data/real_sources/fx/*` from curated/versioned sources.
3. Run `production-readiness` before daily operations.
4. Keep UNKNOWN/source_quality/warnings visible in API and dashboard.
