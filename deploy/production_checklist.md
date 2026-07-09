# Production readiness checklist

Before any shared or production-like deployment:

- [ ] Legal decision recorded: personal/internal use vs external/commercial exposure.
- [ ] API key auth enabled for shared environments.
- [ ] Dashboard not publicly exposed without review.
- [ ] Real universe CSVs populated and coverage validated.
- [ ] Real rates/FX sources versioned and inspected.
- [ ] EOD refresh logs reviewed.
- [ ] Backups scheduled and restore tested.
- [ ] CI release gate green.
- [ ] Validation report updated for the deployed tag.
- [ ] Footer disclaimer and attribution visible.
- [ ] UNKNOWN and coverage remain visible in dashboard and screener.

- [ ] Monitoring alert threshold reviewed: batch/live snapshot failures >20% trigger alert.
- [ ] `.env` created from `.env.example`; real secrets are not committed.
- [ ] Optional live/E2E tests were run only in an environment where network/browser dependencies are allowed.
