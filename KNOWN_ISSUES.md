# KNOWN_ISSUES — CartoZen v1.1.0 (2025-08-17)

A living list of known limitations and expected behaviours in the stable branch.

## Table legend deferred
- **Symptom:** Aligned table-style legend not available in v1.1.0.
- **Status:** Deferred to v2.0.0 due to placement complexity.
- **Workaround:** Use standard text-box legend (supports bold headers).

## Inset mini-labels — offset & alignment
- **Symptom:** In some environments, *Inset label offset X/Y (px)* and *align* may not visibly change mini-inset labels.
- **Status:** Under review for consistent application across configurations.
- **Workarounds:**
  - Increase the offset magnitude (e.g., ±12 px or more) to verify.
  - Temporarily disable mini-labels and rely on cluster counts on the main map.

## Country/continent extent requires data availability
- **Symptom:** Inset overview stuck at global.
- **Cause:** Missing Natural Earth zip or offline Cartopy cache.
- **Workaround:** Place `assets/ne_10m_admin_0_countries.zip` locally or ensure Cartopy can fetch data.

## Declutter quality varies
- **Symptom:** Label repulsion can be conservative.
- **Cause:** Falls back when `adjustText` is not installed.
- **Workaround:** `pip install adjustText` to improve placement.

## Cluster counts vs. labels
- **Symptom:** When displaying counts, mixing them with representative labels can cause confusion.
- **Guidance:** If **Show cluster counts** is on, prefer **counts** only for clarity. If labels are needed, pull one label using `clusters[cid][0]` logic in your code, not both.

## Export frame
- **Symptom:** Export size may feel larger than expected when insets are on.
- **Design:** Tight bbox is **intentionally disabled** when any inset exists to preserve page framing.

---

If you hit an issue not listed here, please file it with a screenshot, a description of your data columns, and your environment details (Python version, OS).
