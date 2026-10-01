<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 0. Synk

→ Kjerne: `coordinator-runbook.md` § 0 · Begrunnelser: `runbook-hvorfor.md` § 0

```bash
git fetch origin {{BASE_BRANCH}} && git merge --ff-only origin/{{BASE_BRANCH}}
```
Speil-vennlig: fast-forwarder ekte `{{BASE_BRANCH}}` ELLER en sesjons-speil-branch (tip ==
`origin/{{BASE_BRANCH}}`, fordi `{{BASE_BRANCH}}` er utsjekket i et annet worktree) til
`origin/{{BASE_BRANCH}}`. En divergert branch (lokale commits utenfor delt state) feiler
høyt her — det er korrekt, ikke en regresjon. Working tree ikke ren → rapporter til
mennesket og stopp.

**Hook-aktivering (idempotent, ved sesjonsstart):** har prosjektet `.githooks/` fra
`scaffolding/` (pre-push, pre-commit-delt-checkout-vern), sett `core.hooksPath` — men overstyr
aldri en eksisterende verdi (den kan være satt bevisst):
```bash
[ -d .githooks ] && [ -z "$(git config --get core.hooksPath 2>/dev/null)" ] \
  && git config core.hooksPath .githooks && echo "core.hooksPath satt til .githooks"
```
