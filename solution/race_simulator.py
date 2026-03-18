#!/usr/bin/env python3
import json
import sys

OFFSET = {'SOFT': -1.80671075, 'MEDIUM': 0.0, 'HARD': 1.40746554}
RATE   = {'SOFT': 0.24414119,  'MEDIUM': 0.09241902, 'HARD': 0.03952911}
GRACE  = {'SOFT': 7.37438972,  'MEDIUM': 16.67307627, 'HARD': 26.29423521}
TC     = 0.01436284
TREF   = 53.85510494
FUEL   = {'SOFT': -0.00153841, 'MEDIUM': -0.00335417, 'HARD': 0.00277877}
S2_MAX = 2_000_000.0

TRACK_BONUS = {
    ('Bahrain',     'E', 'SOFT'):    1.000,
    ('Bahrain',     'S', 'HARD'):    1.000,
    ('COTA',        'S', 'HARD'):    0.030,
    ('Monaco',      'S', 'HARD'):    0.050,
    ('Silverstone', 'E', 'SOFT'):   -1.000,
    ('Suzuka',      'S', 'MEDIUM'): -0.031,
}

PERLAP_BONUS = {
    ('Monaco', 'SOFT'): -0.05,
}

DGRACE = {'SOFT': 0.0, 'HARD': 0.0}


def capped_S2(N, s2_max=S2_MAX):
    if N <= 0.0:
        return 0.0
    raw = N * (N + 1) * (2 * N + 1) / 6.0
    return (raw * s2_max) / (raw + s2_max)


def simulate(race_config, strategies,
             offset=None, rate=None, grace=None, fuel=None,
             tc=None, tref=None,
             s2_max=None, track_bonus=None, dgrace=None,
             perlap_bonus=None):
    _offset       = offset       if offset       is not None else OFFSET
    _rate         = rate         if rate         is not None else RATE
    _grace        = grace        if grace        is not None else GRACE
    _fuel         = fuel         if fuel         is not None else FUEL
    _tc           = tc           if tc           is not None else TC
    _tref         = tref         if tref         is not None else TREF
    _s2_max       = s2_max       if s2_max       is not None else S2_MAX
    _track_bonus  = track_bonus  if track_bonus  is not None else TRACK_BONUS
    _dgrace       = dgrace       if dgrace       is not None else DGRACE
    _perlap_bonus = perlap_bonus if perlap_bonus is not None else PERLAP_BONUS

    base       = race_config['base_lap_time']
    pit        = race_config['pit_lane_time']
    temp       = race_config['track_temp']
    total_laps = race_config['total_laps']
    track      = race_config.get('track', '')

    tf = 1.0 + _tc * (temp - _tref)

    driver_times = []
    for pos_key in sorted(strategies.keys(), key=lambda x: int(x.replace('pos', ''))):
        strategy = strategies[pos_key]
        did      = strategy['driver_id']
        grid_pos = int(pos_key.replace('pos', ''))
        stops    = sorted(strategy['pit_stops'], key=lambda s: s['lap'])

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
            mid       = 2 * (start_lap + 1) + stint_len - 1
            t_off     = _offset[compound] * stint_len * (
                1.0 + _fuel[compound] * mid / (2.0 * total_laps)
            )
            grace_eff = _grace[compound] + _dgrace.get(compound, 0.0) * (temp - _tref)
            N         = max(0.0, stint_len - grace_eff)
            t_deg     = _rate[compound] * capped_S2(N, _s2_max)

            total_time += (t_off + t_deg) * tf
            total_time += _perlap_bonus.get((track, compound), 0.0) * stint_len

        starting_compound = stints[0][0]
        ending_compound   = stints[-1][0]
        total_time += _track_bonus.get((track, 'S', starting_compound), 0.0)
        total_time += _track_bonus.get((track, 'E', ending_compound),   0.0)

        driver_times.append((total_time, grid_pos, did))

    driver_times.sort()
    return [did for _, _, did in driver_times]


def main():
    test_case           = json.load(sys.stdin)
    race_id             = test_case['race_id']
    race_config         = test_case['race_config']
    strategies          = test_case['strategies']
    finishing_positions = simulate(race_config, strategies)
    print(json.dumps({'race_id': race_id, 'finishing_positions': finishing_positions}))


if __name__ == '__main__':
    main()
