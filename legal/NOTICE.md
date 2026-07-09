# NOTICE — Attribution and Use Restrictions

## Attribution (CC BY-NC-SA 4.0)

This project (`sws-snowflake-engine`, SWS Snowflake Engine v3.1) is a controlled,
independent implementation derived from the **public historical methodology
documentation published on GitHub by Simply Wall St**:

- Company Analysis Model — https://github.com/SimplyWallSt/Company-Analysis-Model
- Portfolio Analysis Model — https://github.com/SimplyWallSt/Portfolio-Analysis-Model

That source methodology is licensed under the
**Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
(CC BY-NC-SA 4.0)** license: https://creativecommons.org/licenses/by-nc-sa/4.0/
A copy of the license text is included in this repository as `LICENSE.markdown`.

Copies of the source methodology documents retained for reference in this
repository (e.g. `MODEL.markdown`, `GROWTH.MARKDOWN`, `industry_averages.markdown`,
`dcf-update-q1-2019.markdown`, `sept_2017_model_updates.markdown`) remain the
work of Simply Wall St under the license above.

## Modifications

This repository does not redistribute the source methodology unmodified: it
implements an engine, tests, API and dashboard **derived from** that public
documentation (model pack v3.1), with documented calibrations (E1), assumptions
(E2, see `config/assumptions.yaml`) and pragmatic implementation decisions (E3).
The derived methodology documentation is shared under the same license terms
(ShareAlike).

## Use restrictions

- **NonCommercial:** the upstream license is NC. This project is scoped for
  internal, personal and educational use only. Any external, commercial or
  paid deployment is blocked by the operational gate in
  `config/legal_scope.yaml` and requires an explicit legal review first.
- **Not investment advice:** all outputs are quantitative exploratory analysis
  of a public historical methodology. They are not investment advice and must
  not be presented as such.
- **Not the live Simply Wall St model:** this implementation reproduces only
  the public GitHub documentation (circa 2017–2019). It is not a replica of,
  and makes no claims about, the current proprietary Simply Wall St platform.
- **No endorsement:** Simply Wall St has not reviewed, endorsed or approved
  this project.

## Propagation

This attribution and the disclaimer above are propagated to user-facing
surfaces: the dashboard footer (`dashboard/components/footer.py`), generated
reports, and engine output `warnings`. Removing them is blocked by the CI gate
`scripts/ci/check_attribution_footer.py`.
