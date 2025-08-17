# KNOWN_ISSUES — CartoZen v1.0.0 (2025-08-12)

A living list of known limitations and expected behaviours in the first stable release.

## Inset mini‑labels — offset & alignment
- **Symptom:** In certain builds, *Inset label offset X/Y (px)* and *align* may not visibly change mini‑inset labels.
- **Status:** Under review for consistent application across all environments.
- **Workarounds:**
  - Increase the offset magnitude (e.g., ±12 px or more) to verify.
  - Temporarily disable mini‑labels and rely on cluster counts on the main map.

## Latitude axis direction
- **Symptom:** Some deployments don’t expose a **Descending** latitude toggle.
- **Status:** Feature is trivial to add; may be held back to keep parity with older beta configs.
- **Workaround:** None in UI; flip `ax.set_ylim(ax.get_ylim()[::-1])` in code if required for print layouts.

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

## Tight bbox is intentionally disabled when any inset exists
- **Symptom:** Export size may feel larger than expected when insets are on.
- **Design:** This is **by design** to preserve full page frames during export.

---

If you hit an issue not listed here, please file it with a screenshot, a description of your data columns, and your environment details (Python version, OS).