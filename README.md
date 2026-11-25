# LunaRadSatOrbits

**Low-thrust orbit transfer, station-keeping and end-of-life disposal analysis for the LunaRadSat lunar CubeSat mission (GMAT)**

*Politecnico di Torino – DIMEAS/STAR · Space Mission System Design 2026 (SMSD2026) · Phase 0/A study*

---

## Abstract

LunaRadSat (LRS) is a 16U CubeSat mission concept to characterise the lunar radiation environment (galactic cosmic rays and solar particle events) at a broad range of altitudes and to correlate it with the response of biological samples. Covering that altitude range requires a **highly elliptical, near-polar low lunar orbit** (≈ 95 × 4000 km altitude) that must be reached, held and finally disposed of using only a **solar-electric low-thrust propulsion system** (1.8 mN, Isp 800 s).

This repository contains the complete orbital-analysis chain for a single spacecraft (`LRS1`) over the 1.5-year (548-day) operational life:

1. **Transfer** from the lunar capture orbit (≈ 800 × 8000 km) to the science orbit using finite burns centred on the apsides.
2. **Station-keeping** of semi-major axis and eccentricity with an energy-based dead-band controller.
3. **Disposal** by a controlled lunar-surface impact at a pre-selected site (Mare Nubium).

The manoeuvre parameters that drive the cost/time trade (the *burn fractions*, i.e. the fraction of each orbital period spent thrusting) are selected by **batch grid search**: a generator produces the GMAT script grid, GMAT runs it, and two analysers rank the results against hierarchical mission criteria.

---

## Table of contents

1. [Mission context](#1-mission-context)
2. [Repository contents](#2-repository-contents)
3. [Common modelling assumptions](#3-common-modelling-assumptions)
4. [Phase 1 – Low-thrust transfer](#4-phase-1--low-thrust-transfer-lrs_lt_transfer_0367_0411script)
5. [Phase 2 – Station-keeping](#5-phase-2--station-keeping-sk_046_046script)
6. [Phase 3 – Disposal](#6-phase-3--disposal-lrs_disposalscript)
7. [Grid-search tooling](#7-grid-search-tooling)
8. [Typical workflow](#8-typical-workflow)
9. [Requirements](#9-requirements)
10. [Known limitations and open points](#10-known-limitations-and-open-points)

---

## 1. Mission context

| Item | Value |
|---|---|
| Study | SMSD2026 – university-level concurrent-engineering study, Phase 0/A |
| Host | Politecnico di Torino, DIMEAS/STAR |
| Stakeholder frame | Requirements framed against agency-level stakeholders (NASA, ESA, JAXA-type) |
| Platform | 16U CubeSat, solar-electric low-thrust propulsion |
| Payloads | **LunaRAY** (radiation-physics instrument) and **LunaCELL** (biological experiment module) |
| Science goal | Radiation environment (GCR, SPE) vs. altitude, correlated with biological response |
| Operational life | 1.5 years (548 days) |
| Disposal driver | Compliance with debris-mitigation and planetary-protection practice (IADC guidelines, COSPAR policy) |

**Why this orbit.** The science objective is a *dose-vs-altitude* profile. A single elliptical orbit sweeps the whole altitude range in every revolution, so one spacecraft samples the full profile without changing orbit. The price is that lunar gravity-field perturbations (mascons) and third-body effects (Earth, Sun) continuously perturb a low, eccentric lunar orbit, so the orbit needs active maintenance and a dedicated disposal budget. That is exactly what the three scripts below quantify.

**Timeline modelled in this repository**

| Phase | Start epoch (UTC) | Duration | Initial orbit (altitude) | Propellant at start |
|---|---|---|---|---|
| Transfer | 09 Nov 2028 12:00 | ≈ 75 days (station-keeping starts 23 Jan 2029) | ≈ 800 × 8000 km, i = 86° | 2.0 kg (24 kg wet) |
| Station-keeping | 23 Jan 2029 18:25 | 548 days | ≈ 95 × 4001 km, i ≈ 84.9° | ≈ 1.455 kg |
| Disposal | 26 Jul 2030 02:17 | few days | ≈ 130 × 4154 km, i ≈ 42.1° | ≈ 0.315 kg |

*(Altitudes are derived from the Keplerian elements in the scripts using R☾ = 1737.4 km.)*

---

## 2. Repository contents

| File | Role |
|---|---|
| `LRS_LT_Transfer_0.367_0.411.script` | GMAT: two-phase low-thrust transfer to the science orbit (reference burn fractions BF₁ = 0.367, BF₂ = 0.411) |
| `SK_0.46_0.46.script` | GMAT: 548-day station-keeping with dead-band control (reference BF_Apo = BF_Per = 0.46) |
| `LRS_Disposal.script` | GMAT: end-of-life disposal to controlled lunar impact |
| `generator/gmat_batch_generator.py` | Generates the burn-fraction grid of GMAT scripts and runs them in batch |
| `analizzatore.py` | Ranks the **transfer** grid search |
| `analizzatoreSK.py` | Ranks the **station-keeping** grid search |

---

## 3. Common modelling assumptions

All three scripts share the same spacecraft and environment model, so results are directly comparable across phases.

- **Spacecraft:** dry mass 22 kg; drag area 0.075 m², SRP area 0.3 m², C_d = 2.2, C_r = 1.8.
- **Propulsion:** solar-electric thruster, constant thrust 1.8 mN, Isp 800 s, 100 % duty cycle, `ConstantThrustAndIsp` model; one thruster object per burn direction (prograde, retrograde, radial). Thrust is applied as **finite burns** (not impulsive), which is mandatory at this thrust level (acceleration ≈ 7.5 × 10⁻⁵ m/s² at 24 kg).
- **Power:** `SolarPowerSystem` with dual-cone shadow model (Earth and Moon), 0.3 kW initial maximum power, 0.5 %/year decay, 5 % margin. An `EclipseLocator` records umbra/penumbra/antumbra events.
- **Force model:** Moon central body with the **LP165P** gravity field (degree/order 8×8, captures the mascon perturbations that dominate low lunar orbits); Earth and Sun as point masses; drag off; SRP off.
- **Propagator:** Runge–Kutta 8(9), accuracy 10⁻¹¹, adaptive step.
- **Frame:** Moon-centred MJ2000 equatorial (`LunaMJ2000Eq`).
- **ΔV accounting:** from the mass depletion of each burn via the rocket equation

$$\Delta V = I_{sp}\, g_0 \ln\frac{m_0}{m_1},\qquad I_{sp}=800\ \mathrm{s},\ g_0 = 9.81\ \mathrm{m/s^2}$$

  accumulated over all burns (`DeltaV`), together with the propellant used (`FuelConsumed`).

---

## 4. Phase 1 – Low-thrust transfer (`LRS_LT_Transfer_0.367_0.411.script`)

**Objective.** Lower apoapsis and periapsis from the capture orbit (≈ 800 × 8000 km) to the science orbit (≈ 100 × 4000 km altitude) with minimum propellant and a duration compatible with the schedule.

**Strategy.** At 1.8 mN a single burn is impossible; the transfer is a sequence of **thrust arcs centred on the apsides**. In each revolution the spacecraft coasts for $T/2 - t_b/2$, thrusts for $t_b = BF\cdot T$ (where $T$ is the current orbital period), then coasts to the next apsis:

$$t_b = BF \cdot T,\qquad t_\text{coast} = \frac{T}{2} - \frac{t_b}{2}$$

The two phases run sequentially:

| Phase | Burn centred at | Effect | Burn fraction | Terminates when |
|---|---|---|---|---|
| 1 | Periapsis | Lowers apoapsis | `BF1` | R_apo ≤ 5738.4 km (≈ 4001 km altitude), or R_per < safety radius |
| 2 | Apoapsis | Lowers periapsis | `BF2` | R_per ≤ 1838.4 km (≈ 101 km altitude), or safety radius reached |

**Rationale.**
- Burning around an apsis changes the *opposite* apsis most efficiently (Gauss's variational equations), so the two apsides are treated one at a time.
- Centring the arc on the apsis maximises the effective velocity change per unit propellant; a longer arc (larger BF) shortens the transfer but spreads thrust away from the apsis (more steering/gravity losses). **BF is therefore the key trade parameter** between duration and propellant, and is the variable swept by the grid search.
- A periapsis **safety radius** terminates a phase before the orbit could intersect the surface during the descent; it is a hard guard, not a target.

**Outputs.** `SummaryFile` (final state and budgets), `Orbite_Target.txt` (orbit history), `EclipseLocator1.txt`, and GMAT plots (SMA, ECC, INC, β-angle, apsis radii, mass, ΔV).

---

## 5. Phase 2 – Station-keeping (`SK_0.46_0.46.script`)

**Objective.** Keep the science orbit inside its design envelope for 548 days with minimum ΔV and propellant.

**Strategy – energy-based dead-band control.** Two controlled quantities, each with a tolerance band around the reference orbit (SMA = 3785.489 km, e = 0.51586):

| Quantity | Reference | Band | Check at | Correction (centred burn) |
|---|---|---|---|---|
| Semi-major axis | 3785.489 km | ± 100 km | Apoapsis | Retrograde if above band, prograde if below |
| Eccentricity | 0.5158587 | ± 0.008 | Periapsis | Prograde or retrograde depending on the sign of the error |

Each revolution the script propagates apoapsis → periapsis → apoapsis, evaluates the bands and fires finite burns of duration $BF\cdot T$ centred on the apsis (`BF_Apo`, `BF_Per`). Every iteration is logged to `SK_Report`. The loop ends at **548 days** or when usable propellant is exhausted (tank ≤ 0.01 kg).

**Rationale.**
- SMA (orbital energy) is checked and corrected at **apoapsis**; eccentricity (orbit shape) is checked and corrected at **periapsis**, so each control loop acts at a fixed, well-defined point of the orbit.
- A dead band (rather than continuous correction) avoids burning for negligible drifts and keeps the propellant use proportional to the real perturbation rather than to the control law.
- The eccentricity band is expressed in *e* because periapsis altitude is very sensitive to it: for a ≈ 3785 km, Δe = 0.008 corresponds to ≈ 30 km of periapsis radius.
- BF_Apo and BF_Per are the only free design parameters and are optimised by grid search (§7).

---

## 6. Phase 3 – Disposal (`LRS_Disposal.script`)

**Objective.** Remove the spacecraft from orbit at end of life by a **controlled impact** at a chosen, scientifically and operationally acceptable lunar site (Mare Nubium), using only the residual propellant (≈ 0.315 kg), to avoid leaving a long-lived lunar-orbit object.

**Sequence**

1. **Coast** 1 day to the disposal geometry.
2. **Short radial burn** (down to 0.20 kg of propellant) to modify the argument of periapsis, and hence where the descent ends.
3. **Coast** to 150 km altitude.
4. **Retrograde disposal burn** (down to 0.01 kg) to lower periapsis below the surface.
5. **Propagate to altitude 0** (impact) and write latitude, longitude, residual fuel and AOP.

**Rationale.** A retrograde burn that lowers periapsis below the surface guarantees impact within a bounded time, and the preceding radial burn shapes the impact location. The sequence is sized on the residual propellant, giving a deterministic, propellant-bounded disposal option for the compliance assessment.

**Outputs.** `Disposal_Report.txt` (time history of altitude, lat/lon, R_per, R_apo, AOP, fuel mass, ΔV), ground-track plot, impact coordinates.

---

## 7. Grid-search tooling

### 7.1 Generator – `generator/gmat_batch_generator.py`

Produces the grid of scripts by changing only the burn fractions and the output file names, so each run writes the CSV that the matching analyser expects. Details and examples in [`generator/README.md`](generator/README.md).

| Mode | Template | Swept variables | Output | Analyser |
|---|---|---|---|---|
| `transfer` | `LRS_LT_Transfer_*.script` | `BF1`, `BF2` | `Risultato_<BF1>_<BF2>.csv` | `analizzatore.py` |
| `sk` | `SK_*.script` | `BF_Apo`, `BF_Per` | `SK_<BF_Apo>_<BF_Per>.csv` | `analizzatoreSK.py` |

Default grid: `0.1:0.1:0.5` on both axes (25 runs per phase).

### 7.2 Transfer analyser – `analizzatore.py`

Reads the final state of every transfer run and ranks them with a **strict lexicographic hierarchy**:

1. **Altitude error** $|h_{apo}-4000|+|h_{per}-100|$ km (reach the science orbit)
2. **Propellant consumed**
3. **ΔV**
4. **Transfer duration**
5. **Angular error** on INC (86°), AOP (270°) and RAAN (0°), computed as **cyclic distance on 360°** (so 359° vs 1° counts as 2°, not 358°)

*Rationale:* a transfer that does not reach the science orbit is worthless whatever its cost, so reaching the target altitudes dominates; among equally successful runs, propellant (the scarce, non-renewable resource) outranks time.

### 7.3 Station-keeping analyser – `analizzatoreSK.py`

Evaluates the **whole time series** (not just the end state) and ranks runs with a weighted, normalised score (lower is better):

| Priority | Criterion | Weight |
|---|---|---|
| 1 | Altitude deviation from 4000 / 100 km (mean 40 %, peak 15 %) | 55 % |
| 2 | Inclination deviation from initial value (mean 22 %, peak 8 %) | 30 % |
| 3 | Total ΔV (8 %) and propellant consumed (7 %) | 15 % |

Each metric is normalised to [0, 1] over the grid before weighting. Results go to an Excel file (`Ranking` and `Top5` sheets).

*Rationale:* science return depends on staying in the right altitude band for the full 548 days, so the **mean and the worst case** both matter; inclination keeps the coverage geometry; propellant is third because it only matters once the first two are acceptable.

---

## 8. Typical workflow

```text
(1) generate   →  gmat_batch_generator.py --mode transfer ...   (25 scripts)
(2) run        →  GmatConsole --run <script>   (or --run in the generator)
(3) analyse    →  python analizzatore.py        →  Excel ranking
(4) pick BF₁/BF₂, update the reference transfer script
(5) repeat (1)–(4) with --mode sk starting from the resulting orbit and mass
(6) disposal   →  LRS_Disposal.script, started from the end-of-SK state
```

The analyser input/output paths are defined at the top of `analizzatore.py` and `analizzatoreSK.py` (`cartella_csv`, `file_excel_finale`); set them to your own folders before running.

---

## 9. Requirements

- **GMAT** (General Mission Analysis Tool, NASA) with the **OpenFrames** plugin (the scripts create `OpenFramesInterface` views) and the LP165P lunar gravity file (`LP165P.cof`) and `aura.3ds` model available to GMAT. *Tested GMAT version: to be specified.*
- **Python ≥ 3.9** with `pandas`, `numpy`, `openpyxl` for the analysers; the generator uses the standard library only.
- For large batches, disable or hide the GUI subscribers (OpenFrames, XY plots) in the generated scripts to cut run time.

---

## 10. Known limitations and open points

These are recorded for transparency and for the next iteration of the study.

- **Single-spacecraft model.** The scripts model one spacecraft (`LRS1`); constellation and inter-satellite effects are not included.
- **Simplified perturbations.** Drag and SRP are switched off; the lunar field is truncated at 8×8.
- **Comments vs. values (transfer script).** The comments next to `TargetRadPer`/`TargetRadApo` do not match their numerical values; the loop conditions use the `Threshold*` variables (R_per 1838.4 km, R_apo 5738.4 km) and the `SafetyAlt` guard.
- **`TotalBurnTime` (SK script).** The accumulator references a variable (`BurnDuration`) that is not declared in that script and a statement is missing its terminating `;`; this quantity is not used by the analyser, but it should be cleaned up.
- **Transfer analyser input.** `analizzatore.py` reads the **first data row** of each `Risultato_*.csv`; make sure the report file contains the final-state row you intend to rank.
- **Angular targets.** The INC/AOP/RAAN targets in the analysers are hard-coded and must be updated if the science orbit is re-baselined.
- **Disposal scenario.** A single deterministic impact case is analysed; dispersion (navigation/execution errors, Monte Carlo) is not yet included.
- **Licence and citation** to be defined before wider reuse.

---

*This work is part of the SMSD2026 educational study and has not been reviewed by any space agency; all values are design-study estimates.*
