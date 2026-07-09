# Manual override workflow

Purpose: reduce `UNKNOWN` results without inventing inputs. Manual overrides are
used when yfinance cannot provide SWS-required fields such as analyst estimates,
forward FCF, AFFO/FFO/NAV or bank NPL/deposits/charge-offs.

## Commands

Validate an input and see likely UNKNOWN checks:

```bash
python -m sws_engine.cli validate-input -i data/inputs/AAPL_yfinance_payload.json --report out/AAPL_input_dry_run.md
```

Merge overrides:

```bash
python -m sws_engine.cli merge-overrides \
  --base data/inputs/AAPL_yfinance_payload.json \
  --override templates/manual_override_template.json \
  --output data/inputs/AAPL_curated_payload.json
```

Run curated payload:

```bash
python -m sws_engine.cli company -i data/inputs/AAPL_curated_payload.json -o out/AAPL_output.json
```

## Templates

- `templates/company_input_template.json`: full company field map.
- `templates/manual_override_template.json`: market averages, rates, analyst/FCF overrides.
- `templates/bank_input_template.json`: bank full input skeleton.
- `templates/bank_manual_override_template.json`: bank-specific override fields.
- `templates/reit_input_template.json`: REIT full input skeleton.
- `templates/reit_manual_override_template.json`: AFFO/FFO/NAV overrides.

## Rules

- Missing data remains missing unless an override declares value, source_quality
  and source_class.
- `provider_profile` should remain `yfinance_pragmatic` unless the curated input
  set is complete enough to justify `sws_public_faithful_manual_inputs`.
- Overrides are lineaged as `provider=manual_override`.
- `source_quality=exact` must mean the field matches the SWS model definition.
