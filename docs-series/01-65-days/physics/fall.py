"""Radial free fall of Earth into the Sun from rest at 1 AU (point-mass Sun, Earth as test particle).
Exact closed form: t(r) = sqrt(r0^3/(2GM)) * [ sqrt(x(1-x)) + arccos(sqrt(x)) ],  x = r/r0.
Outputs table.csv (per day) and fine.json (per hour, used by the renderer)."""
import numpy as np, json, csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
GM = 1.32712440018e20      # m^3/s^2 (IAU)
AU = 1.495978707e11        # m
RS = 6.957e8               # nominal solar radius (IAU 2015), m
RE = 6.371e6
L  = 3.828e26              # nominal solar luminosity W
S0 = L/(4*np.pi*AU**2)     # 1361 W/m^2
ALB = 0.30
DAY = 86400.0
ANG0 = 2*np.degrees(np.arcsin(RS/AU))
k = np.sqrt(AU**3/(2*GM))
def t_of_x(x): return k*(np.sqrt(x*(1-x)) + np.arccos(np.sqrt(x)))
T_TOTAL = t_of_x(0.0)
x_surf = (RS+RE)/AU         # Earth's surface touches the photosphere
T_IMPACT = t_of_x(x_surf)
def x_of_t(t):
    lo, hi = np.zeros_like(t)+1e-12, np.ones_like(t)
    for _ in range(200):
        mid = 0.5*(lo+hi); tm = t_of_x(mid)
        hi = np.where(tm > t, hi, mid); lo = np.where(tm > t, mid, lo)  # t decreasing in x
        # t_of_x decreasing: if t_of_x(mid) > t, the time hasn't been reached -> x smaller
    return 0.5*(lo+hi)
def v_of_x(x): return np.sqrt(2*GM/AU*(1/x - 1))
def state(t):
    x = x_of_t(np.asarray(t, float)); r = x*AU
    v = v_of_x(x)
    ang = 2*np.degrees(np.arcsin(np.minimum(1, RS/r)))
    flux = 1/x**2
    Teq = (S0*flux*(1-ALB)/(4*5.670374419e-8))**0.25   # fast rotator, albedo 0.3, no greenhouse, instant
    Tsurf = 288.0*flux**0.25                            # today's mean scaled (fixed greenhouse), instant equilibrium
    return dict(x=x, r_km=r/1e3, v_kms=v/1e3, ang=ang, flux=flux, Teq=Teq, Tsurf=Tsurf)
# cumulative absorbed sunlight (J) vs energy to boil all oceans
def absorbed_energy(t1, n=400000):
    ts = np.linspace(0, t1, n); s = state(ts)
    P = S0*s['flux']*(1-ALB)*np.pi*RE**2
    return np.trapezoid(P, ts)
M_OCEAN = 1.335e21
E_BOIL = M_OCEAN*(4184*(373-288) + 2.257e6)
if __name__ == "__main__":
    print(f"S0={S0:.1f} W/m2  Sun ang today={ANG0:.4f} deg")
    print(f"t_total(point) = {T_TOTAL/DAY:.3f} d ; t_impact(surface) = {T_IMPACT/DAY:.4f} d")
    vs = v_of_x(x_surf); print(f"impact speed {vs/1e3:.1f} km/s ; escape at surface {np.sqrt(2*GM/RS)/1e3:.1f}")
    rows = []
    for d in range(0, 66):
        t = min(d*DAY, T_IMPACT); s = state(np.array([t]))
        rows.append([d, round(float(s['x'][0]),5), round(float(s['r_km'][0])), round(float(s['v_kms'][0]),2),
                     round(float(s['ang'][0]),3), round(float(s['ang'][0]/ANG0),2), round(float(s['flux'][0]),2),
                     round(float(s['Teq'][0]-273.15)), round(float(s['Tsurf'][0]-273.15)),
                     round(float((AU - s['r_km'][0]*1e3)/AU*100),2)])
    with open(os.path.join(HERE,'table.csv'),'w',newline='') as f:
        w = csv.writer(f); w.writerow(['day','dist_AU','dist_km','speed_kms','sun_diam_deg','sun_diam_x_today','sunlight_x_today','Teq_noGH_C','Tsurf_scaled_C','pct_of_way_fallen'])
        w.writerows(rows)
    for r in rows: print(r)
    # milestones
    def t_at(x): return t_of_x(x)/DAY
    ms = {'Venus orbit 0.723 AU': 0.723332, 'Mercury orbit 0.387 AU (a)': 0.387098, 'Mercury perihelion 0.307': 0.3075,
          'half way 0.5 AU':0.5, 'flux x2': 1/np.sqrt(2), 'flux x10': 1/np.sqrt(10), 'flux x100':0.1, 'flux x1000':1/np.sqrt(1000),
          'Tsurf 100C': (288/373.15)**2, 'Teq(noGH) 100C': (state(np.array([0.]))['Teq'][0]/373.15)**2,
          'Tsurf 60C': (288/333.15)**2, 'Tsurf 50C': (288/323.15)**2,
          'Tsurf 327C (lead melts)': (288/600)**2, 'Tsurf 1000C': (288/1273)**2,
          'Moon Hill r (1:1) 384400km': (384400e3/(AU*(5.972e24/(3*1.989e30))**(1/3))),
          'Moon half-Hill': (2*384400e3/(AU*(5.972e24/(3*1.989e30))**(1/3))),
          'fluid Roche 2.44(rhoS/rhoE)^1/3 RS': 2.44*(1.41/5.51)**(1/3)*RS/AU,
          'Sun 10 deg':RS/AU/np.sin(np.radians(5)), 'Sun 20 deg':RS/AU/np.sin(np.radians(10)),'Sun 45 deg':RS/AU/np.sin(np.radians(22.5)),'Sun 90 deg':RS/AU/np.sin(np.radians(45)),'Sun 120deg':RS/AU/np.sin(np.radians(60))}
    for n_, x in ms.items():
        t = t_at(x); s = state(np.array([t*DAY]))
        print(f"{n_:38s} x={x:.4f} t={t:8.3f} d (day {int(t)+1})  T-minus {(T_IMPACT/DAY-t)*24:8.2f} h  v={s['v_kms'][0]:.1f} km/s ang={s['ang'][0]:.2f} flux={s['flux'][0]:.1f}")
    for d in [30, 32, 40, 50, 60]:
        s = state(np.array([d*DAY])); print(f"day {d}: fallen {100*(1-s['x'][0]):.1f}% ")
    # ocean energy
    print(f"E to boil oceans {E_BOIL:.3e} J; absorbed at today's rate per day {S0*(1-ALB)*np.pi*RE**2*DAY:.3e}")
    for frac_h in [48,24,12,6,3,2,1,0.5,0.25, 0.1]:
        t1 = T_IMPACT - frac_h*3600
        E = absorbed_energy(t1); print(f"T-{frac_h:5.2f} h: cumulative absorbed {E:.3e} J = {E/E_BOIL:.3f} x oceans-boil")
    E = absorbed_energy(T_IMPACT); print(f"at impact: {E/E_BOIL:.3f} x")
    # fine per-hour track for renderer
    hrs = np.arange(0, T_IMPACT/3600+1e-9, 0.25)
    s = state(hrs*3600)
    json.dump(dict(T_IMPACT_h=T_IMPACT/3600, T_TOTAL_h=T_TOTAL/3600, step_h=0.25, x=s['x'].tolist()), open(os.path.join(HERE,'fine.json'),'w'))
