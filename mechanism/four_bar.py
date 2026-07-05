import numpy as np
import json
import math
import argparse
from pathlib import Path

def grashof_condition(a, b, c, d):
    """
    Returns 'Grashof', 'non-Grashof', or 'change-point'.
    a: ground link
    b: input link
    c: coupler link
    d: output link
    """
    links = sorted([a, b, c, d])
    S = links[0]
    L = links[3]
    P = links[1]
    Q = links[2]
    
    if S + L < P + Q:
        return 'Grashof'
    elif S + L > P + Q:
        return 'non-Grashof'
    else:
        return 'change-point'

def compute_theta4(a, b, c, d, theta2_rad):
    K1 = a / d
    K2 = a / b
    K3 = (a**2 + b**2 + d**2 - c**2) / (2 * b * d)
    
    cos2 = math.cos(theta2_rad)
    sin2 = math.sin(theta2_rad)
    
    A = cos2 - K1 - K2 * cos2 + K3
    B = -2 * sin2
    C = K1 - (K2 + 1) * cos2 + K3
    
    disc = B**2 - 4 * A * C
    if disc < 0:
        return None
        
    theta4_1 = 2 * math.atan2(-B + math.sqrt(disc), 2 * A)
    theta4_2 = 2 * math.atan2(-B - math.sqrt(disc), 2 * A)
    
    # Return both branches
    return theta4_1, theta4_2

def transmission_angle(link_ground, link_coupler, link_input, link_output, theta_drive):
    a = link_ground
    b = link_input
    c = link_coupler
    d = link_output
    theta2 = math.radians(theta_drive)
    
    f_sq = a**2 + b**2 - 2*a*b*math.cos(theta2)
    if f_sq <= 0:
        return 0.0
    f = math.sqrt(f_sq)
    
    cos_mu = (c**2 + d**2 - f_sq) / (2 * c * d)
    if cos_mu > 1.0 or cos_mu < -1.0:
        return 90.0
    cos_mu = max(-1.0, min(1.0, cos_mu))
    mu = math.degrees(math.acos(cos_mu))
    return mu

def tip_trajectory(link_ground, link_coupler, link_input, link_output, theta_drive_min, theta_drive_max, num_steps=200):
    a = link_ground
    b = link_input
    c = link_coupler
    d = link_output
    
    x_tips = []
    y_tips = []
    
    thetas = np.linspace(theta_drive_min, theta_drive_max, num_steps)
    for theta2_deg in thetas:
        theta2 = math.radians(theta2_deg)
        t4_vals = compute_theta4(a, b, c, d, theta2)
        if t4_vals is None:
            continue
            
        theta4 = t4_vals[1] # Choose open configuration
        
        # Position of coupler-output joint (C) from origin A
        # Ground is A(0,0) to D(a,0). Output link is from D to C.
        Cx = a + d * math.cos(theta4)
        Cy = d * math.sin(theta4)
        
        x_tips.append(Cx)
        y_tips.append(Cy)
        
    return x_tips, y_tips

def over_center_moment_sign(link_ground, link_coupler, link_input, link_output, theta_drive, theta_toggle=92.0):
    if theta_drive < theta_toggle:
        return -1
    elif theta_drive > theta_toggle:
        return 1
    else:
        return 0

def swept_envelope_radius(tip_x, tip_y):
    radii_sq = [x**2 + y**2 for x, y in zip(tip_x, tip_y)]
    if not radii_sq:
        return 0.0
    return math.sqrt(max(radii_sq))

def parameter_study(output_path):
    ground_links = [20, 25, 30]
    coupler_links = [55, 60, 65]
    input_links = [12, 15, 18]
    output_links = [12, 15, 18]
    
    results = []
    
    for a in ground_links:
        for c in coupler_links:
            for b in input_links:
                for d in output_links:
                    grashof = grashof_condition(a, b, c, d)
                    
                    min_mu = 180.0
                    max_mu = 0.0
                    
                    for theta in range(0, 93, 2):
                        mu = transmission_angle(a, c, b, d, float(theta))
                        if mu > 0:
                            min_mu = min(min_mu, mu)
                            max_mu = max(max_mu, mu)
                            
                    tip_x, tip_y = tip_trajectory(a, c, b, d, 0, 92)
                    max_env = swept_envelope_radius(tip_x, tip_y)
                    
                    oc_sign = over_center_moment_sign(a, c, b, d, 95.0, 92.0)
                    
                    results.append({
                        'ground': a,
                        'coupler': c,
                        'input': b,
                        'output': d,
                        'grashof': grashof,
                        'min_transmission_angle': round(min_mu, 2),
                        'max_transmission_angle': round(max_mu, 2),
                        'max_envelope_radius': round(max_env, 2),
                        'over_center_detect': oc_sign
                    })
                    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        thetas = list(range(0, 93))
        mus = [transmission_angle(25, 60, 15, 15, float(t)) for t in thetas]
        
        plt.figure(figsize=(8, 5))
        plt.plot(thetas, mus, label='Transmission Angle (μ)', color='b')
        plt.axhline(40, color='r', linestyle='--', label='Min Recommended (40°)')
        plt.axhline(140, color='r', linestyle='--', label='Max Recommended (140°)')
        plt.xlabel('Driver Angle (θ) [deg]')
        plt.ylabel('Transmission Angle (μ) [deg]')
        plt.title('Four-Bar Linkage: Transmission Angle vs Driver Angle')
        plt.legend()
        plt.grid(True)
        
        plot_path = output_file.parent / 'C1_four_bar_plot.png'
        plt.savefig(plot_path, dpi=150)
        plt.close()
    except ImportError:
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', required=True)
    args = parser.parse_args()
    parameter_study(args.emit)
