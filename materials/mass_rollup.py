import yaml
import csv
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
        writer = csv.DictWriter(f, fieldnames=['part', 'subsystem', 'material', 'mass_kg'])
        writer.writeheader()
        writer.writerows(data)

def generate_evidence_doc(baseline, optimized, b_mass, o_mass, output_dir):
    delta = b_mass - o_mass
    delta_pct = (delta / b_mass) * 100 if b_mass > 0 else 0
    
    doc = [
        "# C4 — Material substitution matrix",
        "",
        "**Paper claim:** Material optimization (quasi-isotropic CFRP, Ti-6Al-4V) yields a 30-40% total mass reduction compared to the baseline 3D printed/aluminum assembly.",
        "",
        "**Recomputed result:**",
        f"Baseline Mass: {b_mass*1000:.1f} g",
        f"Optimized Mass: {o_mass*1000:.1f} g",
        f"Mass Reduction: {delta_pct:.1f}%",
        "",
        "| Part | Baseline Material | Optimized Material | Baseline Mass (g) | Optimized Mass (g) | Delta (g) |",
        "|---|---|---|---|---|---|"
    ]
    
    for b, o in zip(baseline, optimized):
        d = (b['mass_kg'] - o['mass_kg']) * 1000
        doc.append(f"| {b['part']} | {b['material']} | {o['material']} | {b['mass_kg']*1000:.1f} | {o['mass_kg']*1000:.1f} | {d:.1f} |")
        
    doc.extend([
        "",
        "**Artifact paths:**",
        "- `docs/EVIDENCE/C4_mass_baseline.csv`",
        "- `docs/EVIDENCE/C4_mass_optimized.csv`",
        "",
        "*Deterministic computation — no physical measurement*"
    ])
    
    out_path = Path(output_dir) / "C4_delta.md"
    out_path.write_text("\n".join(doc), encoding="utf-8")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', nargs=2, metavar=('BASELINE_CSV', 'OPTIMIZED_CSV'), required=True)
    args = parser.parse_args()
    
    yaml_path = Path(__file__).resolve().parent / "parts.yaml"
    parts = load_parts(yaml_path)
    
    b_data, o_data, b_mass, o_mass = generate_rollup(parts)
    
    export_csv(b_data, args.emit[0])
    export_csv(o_data, args.emit[1])
    
    generate_evidence_doc(b_data, o_data, b_mass, o_mass, Path(args.emit[0]).parent)
