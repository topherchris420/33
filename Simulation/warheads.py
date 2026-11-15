"""Phase 2 warhead bay and terminal-ballistics model (all MODELED).

Everything here is an engineering estimate from published closed-form
relations, at the shared design point. Nothing has been built or detonated.
Relations used, with sources:

- Static margin per loadout: the Phase 1 revision-3 Barrowman model, with the
  constant-mass warhead bay swapped in (design_point.json).
- Gurney velocity for fragment launch (Gurney 1943; cylinder form):
    v0 = sqrt(2E) * sqrt(C / (M + C/2))
  with sqrt(2E) the Gurney energy constant of the explosive (Comp A5 ~2.6
  km/s, Comp B ~2.5 km/s; Cooper, "Explosives Engineering", 1996).
- Fragment velocity decay with drag:
    v(r) = v0 * exp(-k r),  k = rho_air * Cd * A / (2 m)
- Fragment lethal energy criteria: 58 J (incapacitation) and 80 J (NATO
  personnel criteria commonly cited); both are reported.
- HEAT penetration (hydrodynamic jet estimate, Birkhoff et al. 1948):
    P ~ L_jet * sqrt(rho_jet / rho_target)
  with L_jet ~ 1.0-1.5 CD for a well-designed cone; calibrated against the
  widely used P/CD ~ 1.0-2.0 band for charges of this size.
- EFP: velocity from Gurney plate relations (~1.6-2.2 km/s for this mass
  ratio); penetration ~0.5-0.8 CD RHA at standoff (Fong et al. estimates
  for small EFPs; wide scatter, low confidence, stated as such).
"""

import argparse
import json
import math
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'Simulation'))
import static_margin  # noqa: E402

DESIGN_POINT_PATH = REPO_ROOT / 'design_point.json'

RHO_AIR = 1.225
FRAGMENT_Cd = 0.47  # sphere, subsonic
GURNEY_A5 = 2600.0   # m/s, sqrt(2E) Composition A5
GURNEY_COMPB = 2500.0  # m/s, Composition B
RHO_STEEL = 7850.0
RHO_COPPER = 8940.0
RHO_RHA = 7850.0
CD_GP = 0.070       # GP bay charge diameter, m
CD_HEAT = 0.058     # HEAT liner base diameter, m
CD_EFP = 0.055      # EFP liner diameter, m


def loadout_mass_model(dp, loadout):
    """Dry mass and CG with the given warhead loadout installed."""
    bay = dp['warhead_bay']
    comps = [(c['mass_kg'], c['cg_m']) for c in dp['mass_model']['dry_components']]
    # replace the inert Phase 1 ballast with the real warhead bay
    comps = [(m, x) for m, x in comps if m != 0.250]  # drop simulator ballast
    comps.append((bay['bay_total_mass_kg'], bay['bay_cg_m']))
    motor = dp['mass_model']['motor']
    wet = (motor['wet_kg'], motor['cg_m'])
    dry_total = sum(m for m, _ in comps)
    dry_cg = sum(m * x for m, x in comps) / dry_total
    return comps, wet, dry_total, dry_cg


def static_margin_per_loadout(dp, ork_path):
    """SM at ignition and burnout for each loadout (constant-mass bay)."""
    ork_geom = static_margin.parse_ork(ork_path)
    cp, _terms = static_margin.assemble_cp(dp, ork_geom)
    d_ref = ork_geom['d_ref']
    motor = dp['mass_model']['motor']
    results = {}
    for name in dp['warhead_bay']['loadouts']:
        comps, wet, dry_total, dry_cg = loadout_mass_model(dp, name)
        # ignition CG: dry + wet motor
        m_ign = dry_total + wet[0]
        cg_ign = (dry_total * dry_cg + wet[0] * wet[1]) / m_ign
        # burnout CG: dry + spent motor case
        m_bo = dry_total + motor['dry_kg']
        cg_bo = (dry_total * dry_cg + motor['dry_kg'] * wet[1]) / m_bo
        results[name] = {
            'sm_ignition_cal': round((cp - cg_ign) / d_ref, 3),
            'sm_burnout_cal': round((cp - cg_bo) / d_ref, 3),
            'cg_ignition_m': round(cg_ign, 4),
            'wet_mass_kg': round(m_ign, 3),
        }
    return results, cp


def gurney_velocity(gurney_const, charge_kg, case_kg):
    """Cylinder Gurney velocity (m/s)."""
    if charge_kg <= 0 or case_kg <= 0:
        return 0.0
    return gurney_const * math.sqrt(charge_kg / (case_kg + charge_kg / 2.0))


def fragment_lethal_radius(v0, fragment_mass_g, criteria_j):
    """Radius where a fragment's kinetic energy drops to the criterion."""
    m = fragment_mass_g * 1e-3
    d = (6.0 * m / (math.pi * RHO_STEEL)) ** (1 / 3)  # equivalent sphere
    area = math.pi * (d / 2) ** 2
    k = RHO_AIR * FRAGMENT_Cd * area / (2 * m)
    v_needed = math.sqrt(2 * criteria_j / m)
    if v0 <= v_needed:
        return 0.0
    return math.log(v0 / v_needed) / k


def gp_terminal_ballistics(loadout):
    exp = loadout['explosive_kg']
    case = loadout['case_and_fragments_kg']
    v0 = gurney_velocity(GURNEY_A5, exp, case)
    r58 = fragment_lethal_radius(v0, 0.20, 58.0)
    r80 = fragment_lethal_radius(v0, 0.20, 80.0)
    n_frags = int((case * 0.5) / 0.0002)  # ~half the case mass in ~0.2 g fragments
    # Casualty radius: spatial-density limit. Fragments spread over a
    # hemisphere of area 2*pi*r^2; a standing human presents ~0.5 m^2.
    # P(hit) = n*A_p / (2*pi*r^2); the radius where P(hit) = 0.5:
    presented_area = 0.5
    r_spread = math.sqrt(n_frags * presented_area / math.pi)
    # The governing radius is the smaller of the energy and density limits.
    r_casualty = min(r_spread, r58)
    return {
        'gurney_velocity_m_s': round(v0, 0),
        'fragment_class_g': 0.20,
        'lethal_radius_energy_limit_58j_m': round(r58, 1),
        'lethal_radius_energy_limit_80j_m': round(r80, 1),
        'fragment_spread_radius_p50_m': round(r_spread, 1),
        'casualty_radius_m': round(r_casualty, 1),
        'casualty_radius_definition': 'radius where a 0.5 m^2 presented human is hit with >=50% probability AND the striking fragment still carries >=58 J; the smaller of the two limits governs',
        'effective_fragment_count_est': n_frags,
        'assumptions': [
            'Gurney cylinder relation with Comp A5 sqrt(2E) = 2600 m/s',
            'spherical-fragment drag, Cd 0.47, sea-level density',
            'natural fragmentation, ~0.2 g class, half the case mass fragmenting usefully',
            'hemispherical fragment spread, 0.5 m^2 presented area, no terrain masking',
        ],
        'confidence': 'MODERATE: closed-form Gurney, drag, and spread estimates; no arena test performed',
    }


def heat_terminal_ballistics(loadout):
    cd = CD_HEAT
    # Jet length for a well-designed 60 deg copper cone: 1.0-1.5 CD.
    p_low = 1.0 * cd * math.sqrt(RHO_COPPER / RHO_RHA)
    p_high = 1.5 * cd * math.sqrt(RHO_COPPER / RHO_RHA)
    return {
        'liner_cd_mm': cd * 1000,
        'liner_angle_deg': 60,
        'jet_length_cd': [1.0, 1.5],
        'penetration_rha_mm': [round(p_low * 1000, 0), round(p_high * 1000, 0)],
        'optimal_standoff_mm': [round(2.0 * cd * 1000, 0), round(3.0 * cd * 1000, 0)],
        'jet_formation': 'unconfined copper cone, Comp B fill, wave shaper optional',
        'assumptions': [
            'hydrodynamic jet penetration P ~ L_jet * sqrt(rho_jet/rho_target)',
            'jet length 1.0-1.5 liner CD, consistent with the P/CD 1.0-2.0 band for charges this size',
            'RHA target at normal incidence, fuze-initiated at 2 CD standoff',
        ],
        'confidence': 'MODERATE: calibrated closed-form; shaped-charge performance is highly design-sensitive',
        'defeats': 'APC/IFV side and roof armor (~30-50 mm RHA); not MBT frontal armor',
    }


def efp_terminal_ballistics(loadout):
    cd = CD_EFP
    exp = loadout['explosive_kg']
    liner = loadout['liner_kg']
    v0 = 0.85 * GURNEY_A5 * math.sqrt(2.0 * exp / (exp + 2.0 * liner))
    p_low = 0.5 * cd * 1000
    p_high = 0.8 * cd * 1000
    return {
        'efp_velocity_m_s': round(v0, 0),
        'penetration_rha_mm': [round(p_low, 0), round(p_high, 0)],
        'effective_standoff_m': [1.0, 50.0],
        'assumptions': [
            'Gurney plate relation with a dish liner mass ratio giving 1.6-2.2 km/s',
            'penetration 0.5-0.8 liner CD RHA at 1-50 m standoff (small-EFP literature band)',
            'liner: armco iron or OFHC copper dish',
        ],
        'confidence': 'LOW-TO-MODERATE: EFP performance scatters widely with liner fabrication; stated as a band',
        'defeats': 'light-skinned vehicles and APC roofs at standoff; soft targets out to 50 m',
    }


def build_record(ork_path, design_point_path=DESIGN_POINT_PATH):
    dp = static_margin.load_design_point(design_point_path)
    sm_results, cp = static_margin_per_loadout(dp, ork_path)
    bay = dp['warhead_bay']
    loadouts = bay['loadouts']
    record = {
        'schema': 'project33.mil.warheads/1',
        'generator': 'Simulation/warheads.py',
        'design_point_revision': dp.get('revision'),
        'evidence_class': 'MODELED',
        'bay': {
            'total_mass_kg': bay['bay_total_mass_kg'],
            'cg_m': bay['bay_cg_m'],
            'constant_mass_note': 'all loadouts share the 250 g bay total (case, liner, fill, ballast), so mass properties and the Phase 1 static margin hold for every loadout',
        },
        'static_margin_per_loadout': sm_results,
        'static_margin_window_cal': [1.5, 2.0],
        'static_margin_all_loadouts_in_window': all(
            1.5 <= v['sm_ignition_cal'] and v['sm_burnout_cal'] <= 2.0
            for v in sm_results.values()),
        'cp_m': round(cp, 5),
        'terminal_ballistics': {
            'GP_HE_FRAG': gp_terminal_ballistics(loadouts['GP_HE_FRAG']),
            'HEAT': heat_terminal_ballistics(loadouts['HEAT']),
            'EFP': efp_terminal_ballistics(loadouts['EFP']),
        },
        'fuze_summary': {
            'baseline': 'contact point-detonating, crush switch plus accelerometer impact sensing, delay-selectable 0/5/10/20 ms',
            'standoff_option': '5.8 GHz CW Doppler RF proximity module gated 2-6 m for the HEAT loadout optimal standoff',
            'arming': 'dual-event S&A: sustained >=2 g launch acceleration AND canard-deployment confirmation AND motor-burn time gate; no single event or stray signal can arm the fire set',
        },
        'basis': 'closed-form terminal-ballistics estimates at the shared design point; no warhead has been built or detonated',
    }
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ork', required=True)
    parser.add_argument('--emit', required=True)
    args = parser.parse_args()
    record = build_record(args.ork)
    out = Path(args.emit)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print('wrote', out)
    print('SM per loadout:', json.dumps(record['static_margin_per_loadout'], indent=1))
    print('all in window:', record['static_margin_all_loadouts_in_window'])
