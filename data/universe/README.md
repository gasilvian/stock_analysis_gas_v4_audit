# Universe files

`universe_US-SYN.csv` is the synthetic construction universe used by offline tests.

`universe_US_template.csv` and `universe_BVB_template.csv` are real-market universe
seed templates. They intentionally contain blank metric columns. Use the live
provider and/or manual curation to populate metrics before treating averages as
real. Averages built from blank templates will correctly have missing metrics and
warnings rather than invented values.

Required governance for real use:
- validate coverage with `sws-engine validate-universe`;
- exclude ETFs/funds/DRs/secondary listings via `kind`;
- keep country and region populated for fallback hierarchy;
- version the universe CSV used for each averages snapshot.
