#!/usr/bin/env python3

import json
import sys

# ── Model parameters ──
OFFSET = {'SOFT': -1.80671075, 'MEDIUM': 0.0, 'HARD': 1.40746554}
RATE   = {'SOFT': 0.24414119, 'MEDIUM': 0.09241902, 'HARD': 0.03952911}
GRACE  = {'SOFT': 7.37438972, 'MEDIUM': 16.67307627, 'HARD': 26.29423521}
TC     = 0.01436284
TREF   = 53.85510494
FUEL   = {'SOFT': -0.00153841, 'MEDIUM': -0.00335417, 'HARD': 0.00277877}

# ── Per-track compound bonuses (seconds added to driver total time) ──
# Key: (track_name, 'S'=start/'E'=end, compound)
TRACK_BONUS = {
    ('Bahrain',     'E', 'SOFT'):   1.000,   # SOFT-ending strategies slower in Bahrain
    ('Bahrain',     'S', 'HARD'):   1.000,   # HARD-starting strategies slower in Bahrain
    ('COTA',        'S', 'HARD'):   0.030,   # HARD-starting slightly slower at COTA
    ('Monaco',      'S', 'HARD'):   0.050,   # HARD-starting slightly slower at Monaco
    ('Silverstone', 'E', 'SOFT'):  -1.000,   # SOFT-ending strategies faster at Silverstone
    ('Suzuka',      'S', 'MEDIUM'): -0.031,  # MEDIUM-starting slightly faster at Suzuka
}


def simulate(race_config, strategies):
    base = race_config['base_lap_time']
    pit  = race_config['pit_lane_time']
    temp = race_config['track_temp']
    total_laps = race_config['total_laps']
    track = race_config.get('track', '')
    tf = 1.0 + TC * (temp - TREF)

    driver_times = []
    for pos_key in sorted(strategies.keys(), key=lambda x: int(x.replace('pos', ''))):
        strategy = strategies[pos_key]
        did = strategy['driver_id']
        grid_pos = int(pos_key.replace('pos', ''))
        stops = sorted(strategy['pit_stops'], key=lambda s: s['lap'])

        # Build stint list: (compound, start_lap_0indexed, length)
        stints = []
        current_tire = strategy['starting_tire']
        prev_lap = 0
        for stop in stops:
            stints.append((current_tire, prev_lap, stop['lap'] - prev_lap))
            current_tire = stop['to_tire']
            prev_lap = stop['lap']
        stints.append((current_tire, prev_lap, total_laps - prev_lap))

        total_time = len(stops) * pit + total_laps * base
        for compound, start_lap, stint_len in stints:
            off = OFFSET[compound]
            rate = RATE[compound]
            grace = GRACE[compound]
            fuel = FUEL[compound]

            # Offset with fuel: off * L * (1 + fuel * mid / (2*tl))
            mid = 2 * (start_lap + 1) + stint_len - 1
            t_off = off * stint_len * (1.0 + fuel * mid / (2.0 * total_laps))

            # Quadratic degradation: rate * S2 where S2 = N(N+1)(2N+1)/6
            N = max(0, stint_len - grace)
            S2 = N * (N + 1) * (2 * N + 1) / 6.0
            t_deg = rate * S2

            # Temperature scales both offset and degradation
            total_time += (t_off + t_deg) * tf

        # Per-track compound bonuses: start compound and end compound
        starting_tire = stints[0][0]
        ending_tire   = stints[-1][0]
        total_time += TRACK_BONUS.get((track, 'S', starting_tire), 0.0)
        total_time += TRACK_BONUS.get((track, 'E', ending_tire),   0.0)

        driver_times.append((total_time, grid_pos, did))

    # Sort by total time, then grid position for ties
    driver_times.sort()
    return [did for _, _, did in driver_times]


def main():
    test_case = json.load(sys.stdin)
    race_id = test_case['race_id']
    race_config = test_case['race_config']
    strategies = test_case['strategies']

    finishing_positions = simulate(race_config, strategies)

    output = {
        'race_id': race_id,
        'finishing_positions': finishing_positions
    }
    print(json.dumps(output))


if __name__ == '__main__':
    main()
