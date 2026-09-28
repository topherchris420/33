import csv
import json

import yaml
import argparse
from pathlib import Path

# Density table in kg/m^3
DENSITIES = {
    'PLA': 1240,
    'PETG': 1270,
    '7075-T6': 2810,
    'CFRP_quasi_iso': 1550,
    'Ti-6Al-4V': 4430
}

def load_parts(yaml_path):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    return data.get('parts', [])

def compute_mass(volume_cm3, material):
    if material not in DENSITIES:
        raise ValueError(f"Unknown material {material}")
    # volume in cm^3 = volume * 1e-6 m^3
    volume_m3 = volume_cm3 * 1e-6
    return volume_m3 * DENSITIES[material]

def generate_rollup(parts):
    baseline = []
    optimized = []
    
    total_baseline_mass = 0
    total_optimized_mass = 0
    
    for part in parts:
        name = part['name']
        subsystem = part['subsystem']
        vol = part['volume_cm3']
        b_mat = part['baseline_material']
        o_mat = part['optimized_material']
        
        # Parse multiplier like "Fin (x4)"
        multiplier = 1
        if "(x4)" in name:
            multiplier = 4
            
        b_mass = compute_mass(vol * multiplier, b_mat)
        o_mass = compute_mass(vol * multiplier, o_mat)
        
        baseline.append({
            'part': name,
            'subsystem': subsystem,
            'material': b_mat,
            'mass_kg': b_mass
        })
        
        optimized.append({
            'part': name,
            'subsystem': subsystem,
            'material': o_mat,
            'mass_kg': o_mass
        })
        
        total_baseline_mass += b_mass
        total_optimized_mass += o_mass
        
    return baseline, optimized, total_baseline_mass, total_optimized_mass

def export_csv(data, path):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['part', 'subsystem', 'material', 'mass_kg'],
                                lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)


def summarize(parts, b_mass, o_mass):
    """Structured totals. Scope is exactly the parts listed in parts.yaml."""
    return {
        'schema': 'project33.c4.mass_summary/1',
        'generator': 'materials/mass_rollup.py',
        'inputs': 'materials/parts.yaml',
        'units': {'mass': 'kg', 'volume': 'cm^3', 'density': 'kg/m^3'},
        'densities': DENSITIES,
        'parts_included': [p['name'] for p in parts],
        'baseline_total_kg': round(b_mass, 6),
        'candidate_total_kg': round(o_mass, 6),
        'reduction_fraction': round((b_mass - o_mass) / b_mass, 6) if b_mass > 0 else None,
        'not_included': ['electronics', 'servos', 'fasteners and adhesives', 'motor',
                         'wiring and battery', 'manufacturing variation'],
        'basis': 'calculated from authored volumes and handbook densities; no part was weighed',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', nargs=2, metavar=('BASELINE_CSV', 'OPTIMIZED_CSV'), required=True)
    args = parser.parse_args()

    yaml_path = Path(__file__).resolve().parent / "parts.yaml"
    parts = load_parts(yaml_path)

    b_data, o_data, b_mass, o_mass = generate_rollup(parts)

    export_csv(b_data, args.emit[0])
    export_csv(o_data, args.emit[1])
    summary_path = Path(args.emit[0]).parent / "C4_mass_summary.json"
    summary_path.write_text(json.dumps(summarize(parts, b_mass, o_mass), indent=2) + "\n", encoding="utf-8")
