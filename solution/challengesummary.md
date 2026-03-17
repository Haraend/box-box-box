# Box Box Box — Challenge Summary (LLM-Optimized Reference)

## Problem in One Sentence
Given a JSON race config + 20 drivers' tire strategies (pit laps + compound choices), output the exact finishing order (1st–20th) determined purely by total race time. Must be a perfect exact match — no partial credit.

---

## Scoring
- 100 test cases, **binary scoring per case** (exact full order or 0 points)
- Score = (exact matches / 100) × 100%
- Milestones: 20-30% basic, 60-70% good, 90-100% excellent

---

## Input Format (stdin, JSON)
```json
{
  "race_id": "TEST_001",
  "race_config": {
    "track": "Monza",
    "total_laps": 53,
    "base_lap_time": 82.5,
    "pit_lane_time": 22.0,
    "track_temp": 32
  },
  "strategies": {
    "pos1": {
      "driver_id": "D001",
      "starting_tire": "SOFT",
      "pit_stops": [
        {"lap": 18, "from_tire": "SOFT", "to_tire": "MEDIUM"},
        {"lap": 38, "from_tire": "MEDIUM", "to_tire": "HARD"}
      ]
    },
    "pos2": { ... },
    ...
    "pos20": { ... }
  }
}
```

## Output Format (stdout, JSON)
```json
{
  "race_id": "TEST_001",
  "finishing_positions": ["D007", "D015", "D003", ..., "D019"]
}
```
- Array must have **exactly 20 driver IDs**
- All drivers D001–D020 present, no duplicates
- Ordered 1st (fastest) → 20th (slowest)

---

## Core Race Mechanics

### Time Model
```
total_race_time = (num_pit_stops × pit_lane_time)
                + (total_laps × base_lap_time)
                + Σ_over_stints [ (offset_effect + degradation_effect) × temp_factor ]
```

### Tire Compounds
| Compound | Speed    | Durability | Lap Time Offset |
|----------|----------|------------|-----------------|
| SOFT     | Fastest  | Lowest     | Negative (faster) |
| MEDIUM   | Moderate | Balanced   | Baseline (0)    |
| HARD     | Slowest  | Highest    | Positive (slower) |

### Tire Degradation Model
- Tires have a **grace period** (laps of peak performance) before degradation kicks in
- After grace period, degradation is **quadratic** (accelerates with age)
- SOFT: shortest grace, fastest degradation
- MEDIUM: moderate grace and degradation
- HARD: longest grace, slowest degradation

### Temperature Effect
- `temp_factor = 1 + TC × (track_temp - T_ref)` where TC and T_ref are fitted constants
- Temperature **multiplicatively** scales BOTH the compound offset AND degradation effects
- Temperature stays constant for the entire race

### Fuel Effect
- Fuel load decreases over the race → car gets lighter → slight lap time improvement
- Applied as a fuel coefficient per compound modifying the offset term
- `offset_effect = OFFSET[c] × stint_len × (1 + FUEL[c] × mid_lap / (2 × total_laps))`

---

## Critical Rules & Regulations

### Race Structure
- **Starting grid position (pos1–pos20) does NOT affect lap times or race outcome** — it is purely used for strategy assignment
- Each car races in an independent "virtual lane" — **zero car-to-car interaction** (no drafting, blocking, overtaking)
- Pure time trial: fastest total time wins
- All cars complete the same number of laps

### Pit Stops
- Pit stop penalty = `pit_lane_time` seconds added to total time (specified per race)
- **Tire change itself is instantaneous** — no extra time beyond the pit lane penalty
- Pit stops occur at the **end** of the specified lap
- After pitting, tire age resets to 0 (fresh set)
- No limit on number of pit stops
- **Mandatory two-compound rule**: each driver must use at least 2 different tire compounds

### Tire Age Tracking
- Tire age **increments BEFORE calculating the lap time** each lap
- First lap on fresh tires = age 1 (NOT age 0)
- On pit stop laps: the pitting lap is driven on the OLD tires (age still increments), then tire changes

### Environment
- No safety cars, no accidents, no weather changes, no mechanical failures
- Track conditions (temp) are constant for the entire race
- **The simulation is fully deterministic** — same inputs always produce the same output

### Precision
- Work in full floating-point precision throughout
- **Do NOT round lap times until the final sort** — rounding mid-simulation causes wrong positions
- In practice, ties in total time don't occur due to floating-point differences

---

## Gotchas & Common Failure Modes

1. **Tire age starts at 1, not 0**: The regulations explicitly state tire age increments before lap time calculation, so lap 1 is at age=1. Off-by-one here breaks many predictions.

2. **Starting position is irrelevant to race time**: pos1 in the input is just labeling, not a speed advantage.

3. **Temperature multiplies BOTH offset and degradation**: Forgetting to apply `temp_factor` to the offset term (not just degradation) is a common miss.

4. **Pit lane time is per stop, not per lap**: Each stop costs exactly `pit_lane_time` seconds regardless of what compound is fitted.

5. **Grace period is compound-dependent and floats**: The grace period is not an integer cutoff; treat it as a continuous threshold for degradation onset.

6. **File naming vs race_id casing**: Test case files are `test_001.json` (lowercase) but the `race_id` inside is `TEST_001` (uppercase). Your output must echo back the exact `race_id` from the input.

7. **Program runs from repo ROOT**: Paths like `data/historical_races/...` are from the repo root. Do NOT use `../data/...` paths.

8. **`solution/run_command.txt` must be a single command line** run from repo root. Evaluated verbatim with stdin piped in.

9. **Exact match or nothing**: Even one driver position wrong = entire test case fails. Floating-point precision in intermediate calculations matters.

10. **Historical data is randomized**: Races in `data/historical_races/` are not sorted by difficulty or any other dimension.

11. **`from_tire` field in pit stops**: This field exists in the data but is redundant — the actual current tire is always traceable from the strategy. Don't rely on it as your source of truth.

12. **Quadratic degradation, not linear**: Degradation accelerates with tire age (sum of squares, not sum), which is easy to implement wrong if using linear approximations.

---

## Data Overview
- **30,000 historical races** in `data/historical_races/races_XXXXX-XXXXX.json` (1000 races per file)
- Each historical record includes `finishing_positions` (ground truth) for validation
- **100 test cases** in `data/test_cases/inputs/test_001.json` through `test_100.json`
- Expected outputs in `data/test_cases/expected_outputs/test_001.json` through `test_100.json`
- Race IDs: historical = `R00001`–`R30000`, test = `TEST_001`–`TEST_100`

---

## Running & Testing

```bash
# Run all 100 test cases
./test_runner.sh

# Test a single case manually
cat data/test_cases/inputs/test_001.json | python solution/race_simulator.py

# Compare with expected
diff <(cat data/test_cases/inputs/test_001.json | python solution/race_simulator.py | jq -S .) \
     <(jq -S . data/test_cases/expected_outputs/test_001.json)
```

---

## Development Environment (Linux)

- **OS**: Linux
- **Package manager**: `micromamba` (aliased to `conda` in the shell)
- **Pre-created conda environment**: `box-box`
- **To activate**: `conda activate box-box` or `micromamba activate box-box`
- **To run with environment**: `conda run -n box-box python solution/race_simulator.py`
- **To install packages**: `conda install -n box-box <package>` or activate first, then `pip install <package>`
- The `solution/run_command.txt` should point to the python inside the environment if custom packages are needed

### Activating in scripts / test_runner.sh context
Since `test_runner.sh` is a bash script and aliases don't expand there, prefer:
```bash
# Option A: Use micromamba run directly (no alias issues)
micromamba run -n box-box python solution/race_simulator.py

# Option B: Use the full path to python in the env
/path/to/envs/box-box/bin/python solution/race_simulator.py
```
Update `solution/run_command.txt` accordingly if environment-specific packages are needed.

---

## Current Solution Architecture (`solution/race_simulator.py`)

Uses a **closed-form per-stint calculation** (no lap-by-lap loop needed):

```
total_time = num_stops * pit_time + total_laps * base_lap_time
           + Σ_stints [ (OFFSET[c] * L * (1 + FUEL[c] * mid / (2*TL))
                       + RATE[c] * S2(max(0, L - GRACE[c])))
                       * temp_factor ]
```

Where:
- `S2(N) = N*(N+1)*(2*N+1)/6` (sum of squares formula for quadratic degradation)
- `mid = 2*(start_lap+1) + stint_len - 1` (mid-point lap for fuel calculation)
- `temp_factor = 1 + TC * (temp - TREF)`
- Parameters (OFFSET, RATE, GRACE, TC, TREF, FUEL) fitted via Differential Evolution on 30K historical races

**Fitted parameters (current best):**
```python
OFFSET = {'SOFT': -1.80671075, 'MEDIUM': 0.0, 'HARD': 1.40746554}
RATE   = {'SOFT': 0.24414119, 'MEDIUM': 0.09241902, 'HARD': 0.03952911}
GRACE  = {'SOFT': 7.37438972, 'MEDIUM': 16.67307627, 'HARD': 26.29423521}
TC     = 0.01436284
TREF   = 53.85510494
FUEL   = {'SOFT': -0.00153841, 'MEDIUM': -0.00335417, 'HARD': 0.00277877}
```

**Current score**: 37/100 on test cases (37%), ~27% on historical races (as of last DE run)

---

## Current Results & Performance Analysis (37/100)

### Passing Tests (37)
`TEST_002 003 005 010 011 015 019 021 023 026 027 028 030 032 035 036 038 039 045 049 051 052 060 063 067 068 069 071 073 078 081 084 087 088 091 092 099`

### Failing Tests (63)
`TEST_001 004 006 007 008 009 012 013 014 016 017 018 020 022 024 025 029 031 033 034 037 040 041 042 043 044 046 047 048 050 053 054 055 056 057 058 059 061 062 064 065 066 070 072 074 075 076 077 079 080 082 083 085 086 089 090 093 094 095 096 097 098 100`

---

### What We Predict Well

**Characteristic**: Pure 1-stop races where all 20 drivers make exactly 1 pit stop.
- **Pass rate: 34/70 = 49%** of all-1-stop races
- When zero drivers use a 2-stop strategy, we're roughly coin-flip accurate
- We capture the broad ordering correctly; errors are usually just 2 adjacent drivers swapped

**Best track: Spa** — 7/12 = 58% pass rate

---

### What We Struggle With

#### 1. Races with any 2-stop strategies (CRITICAL)
This is the biggest failure mode by far:

| Drivers using 2 stops | Pass | Fail | Rate |
|----------------------|------|------|------|
| 0 (all 1-stop)       | 34   | 36   | 49%  |
| 3–4                  | 1    | 6    | 14%  |
| 5–6                  | 1    | 13   | 7%   |
| 7–9                  | 1    | 8    | 11%  |

**27 of 30 races with any 2-stop drivers fail.** The model cannot correctly rank 2-stop strategies against 1-stop strategies. 2-stop compound sequences are diverse (12 different combos: SOFT→MED→HARD, MED→SOFT→HARD, SOFT→HARD→SOFT, etc.), and the quadratic degradation formula likely overestimates or underestimates the benefit of coming in for a second set.

#### 2. Bahrain — catastrophically bad
- **1/13 = 8%** pass rate, worst of all tracks
- Fails even in pure 1-stop races (only 1/8 = 12.5%)
- No clear differentiating config values vs other tracks; parameters may simply not generalize to Bahrain's base_lap_time / pit_lane_time range
- Bahrain has the widest range of race lengths (32–69 laps) and pit times in the test set

#### 3. Close-call 1-stop swaps
Even in 1-stop races we fail, errors are usually small:
- **Min wrong positions: 2** (just 1 pair swapped), **avg: 6.2/20**
- The model gets the overall structure right but wrong on borderline calls between similarly-timed strategies
- Root cause: parameters are slightly off, causing the time gap between nearly-equal strategies to have the wrong sign

#### 4. Temperature extremes (secondary)
- Failing tests span temps 18–42°C; passing only 19–41°C
- Extreme temperatures (≤22°C or ≥38°C) are almost exclusively in the fail pile
- Suggests `TC` and `TREF` parameters need refinement at the tails

---

### Summary of Improvement Opportunities (Prioritized)

1. **Fix 2-stop races** — affects 30% of test cases, near-zero pass rate → biggest ROI
   - The model likely needs a different degradation profile or parameter set for multi-stint races
   - Consider verifying grace period behavior when a driver re-uses the same compound
   - Possible approach: re-run DE specifically targeting 2-stop scenarios

2. **Refine Bahrain parameters** — may be a track-specific calibration issue
   - Check if base_lap_time range for Bahrain in historical data matches test cases

3. **Tighten 1-stop parameter precision** — ~51% fail rate on 1-stop due to swaps
   - More DE iterations or a finer search around current best parameters
   - Focus on the time-gap accuracy between strategies with similar total times
