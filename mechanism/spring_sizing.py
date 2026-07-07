import math
import json
import argparse
from pathlib import Path

def compute_k_min(v_egress, c_fin, S_fin, t_deploy, h_fin, m_fin, Cm_alpha_max, damping_ratio=0.7):
    """
    Computes minimum torsion spring rate k (N·m/rad).
    """
    if v_egress <= 0:
        raise ValueError("v_egress must be positive")
    if m_fin <= 0:
        raise ValueError("m_fin must be positive")
    if c_fin <= 0 or S_fin <= 0 or t_deploy <= 0 or h_fin <= 0 or Cm_alpha_max <= 0 or damping_ratio < 0 or damping_ratio >= 1:
        raise ValueError("All physical quantities must be positive, and damping_ratio in [0, 1)")

    rho = 1.225 # kg/m^3
    
    # Aerodynamic hinge moment
    M_aero = 0.5 * rho * (v_egress**2) * S_fin * c_fin * Cm_alpha_max
    
    # Fin inertia (thin rod about end)
    I_fin = (1.0 / 3.0) * m_fin * (h_fin**2)
    
    # Required angular acceleration to reach 90 deg (pi/2 rad) in t_deploy
    # Assuming constant acceleration, theta = 0.5 * alpha * t^2
    # pi/2 = 0.5 * alpha * t_deploy^2
    alpha = math.pi / (t_deploy**2)
    
    # Required spring torque (undamped)
    k_min_undamped = I_fin * alpha + M_aero
    
    # Including damping
    k_min = k_min_undamped / (1 - damping_ratio)
    
    return k_min

def validate_design_margin(k_required, k_supplied):
    margin = (k_supplied - k_required) / k_required if k_required > 0 else float('inf')
    meets_20_pct = margin >= 0.20
    return margin, meets_20_pct

def sensitivity_sweep(output_path):
    v_egress_vals = range(150, 251, 10)
    Cm_alpha_max_vals = [round(0.5 + 0.1 * i, 1) for i in range(8)]
    
    results = []
    
    for v in v_egress_vals:
        for cm in Cm_alpha_max_vals:
            k = compute_k_min(
                v_egress=float(v),
                c_fin=0.120,
                S_fin=0.0216,
                t_deploy=0.050,
                h_fin=0.180,
                m_fin=0.154,
                Cm_alpha_max=cm,
                damping_ratio=0.7
            )
            
            results.append({
                'v_egress_m_s': float(v),
                'Cm_alpha_max': float(cm),
                'k_min_N_m_rad': round(k, 2)
            })
            
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        
        V, CM = np.meshgrid(list(v_egress_vals), Cm_alpha_max_vals)
        K = np.zeros_like(V, dtype=float)
        
        for i in range(V.shape[0]):
            for j in range(V.shape[1]):
                K[i,j] = compute_k_min(
                    v_egress=float(V[i,j]),
                    c_fin=0.120,
                    S_fin=0.0216,
                    t_deploy=0.050,
                    h_fin=0.180,
                    m_fin=0.154,
                    Cm_alpha_max=float(CM[i,j]),
                    damping_ratio=0.7
                )
                
        plt.figure(figsize=(8, 6))
        cp = plt.contourf(V, CM, K, cmap='viridis')
        plt.colorbar(cp, label='Minimum Spring Rate k (N·m/rad)')
        plt.xlabel('Egress Velocity (m/s)')
        plt.ylabel('Max Hinge Moment Coefficient (Cm_alpha)')
        plt.title('Spring Sizing Sensitivity Sweep')
        
        plot_path = output_file.parent / 'C6_spring_sweep_plot.png'
        plt.savefig(plot_path, dpi=150)
        plt.close()
    except ImportError:
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', required=True)
    args = parser.parse_args()
    sensitivity_sweep(args.emit)
