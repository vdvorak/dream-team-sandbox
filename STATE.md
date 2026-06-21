# STATE.md — dream-team-sandbox

<!-- ENGINE:STATE START -->
closed_waves: []
<!-- ENGINE:STATE END -->

## Aktualni fokus

Watson setup dokoncen (2026-06-21). Projekt naseedovan: PROJECT-CONSTITUTION.md (vize,
NFR invarianty I1-I11, security pravidla, delivery topologie), project-config.md (status
READY_FOR_SPEC, aktivni agenti, targets). Ceka prvni wave: spec klece (vision-po).

## Open Items

- [ ] vision-po: spec + acceptance criteria (= invarianty I1-I11 jako testovatelna AC)
- [ ] heimdall-security: threat model + controls; Fly spike (Network Policy API, kernel/nftables v microVM, capability drop poradi)
- [ ] ted-architect: architektura 3-vrstvy, overlay-at-deploy build, kontrakt cage<->app
- [ ] alfred-devops: implementace (network-policy applier, Smokescreen ACL, hardened workspace overlay, cage-deploy script)
- [ ] joey-qa + optimus-perf + heimdall: verifikace — acceptance suite = invarianty
