# solarquoter

Guide for Claude (interactive sessions and the factory workflow).

## Stack
Python lead-generation pipeline (`src/`, `run_*.py`) over TheLIST WFS spatial data.

## Before you change things, read
- SPEC.md (living spec - amend it, don't create a parallel spec)
- README.md
- config.yaml

## Sensitive areas
Outreach generation (personaliser) - never send real messages; owner/contact data.

## Commands
```sh
# install
pip install -r requirements.txt
# checks (run all before every PR)
python -m compileall -q src run_*.py
# run
python run_solar_scorer.py  (see README.md); no UI - verification = run the affected stage on a small sample and save its output to factory-proof/
```

## Factory
Issues labelled `factory` run through `.claude/factory/BLUEPRINT.md` (triage -> spec -> implement -> verify -> merge risk -> PR).
Skills: `.claude/skills/factory-triage`, `verify-with-proof`, `merge-risk`. Use them in interactive sessions too.

## Verification gotchas
<!-- Append one line per lesson learned while verifying (ports, env vars, logins, flaky selectors). -->
