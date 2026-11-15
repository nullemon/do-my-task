"""Brightness of each event as seen from Earth: m = M + 5 log10(d / 10 pc). Print: /home/user/ttsenv/bin/python science.py
Sources (rounded): core-collapse SN peak M_V ~ -17 (Type II-P typical, Richardson+ 2014); kilonova AT2017gfo peak M ~ -15.8
(Coulter+ 2017; Kasen+ 2017); GRB 080319B peak V = 5.3, z = 0.937, ~7.5 Gly light-travel (Racusin+ 2008); SGR 1806-20
giant flare 27 Dec 2004: initial spike ~0.2 s, fluence ~1 erg/cm^2 (Hurley+ 2005, Palmer+ 2005), distance ~8.7 kpc
(Bibby+ 2008); 3C 273: V = 12.9, z = 0.158, M_V ~ -26.7 (luminosity distance ~ 750 Mpc); galactic centre 8.0 kpc (26,000 ly).
Lethal ranges (why each is placed where it is): SN ~ 25-50 ly (ozone; X-rays to ~160 ly); kilonova ~ 36 ly, an on-axis
short GRB jet ~ 300 ly (Perkins+ 2024); GRBs: kpc-scale if beamed at us; giant flare ~ a few ly."""
import math
LY_PC = 3.26156
M_SUN, M_VENUS, M_MOON = -26.74, -4.6, -12.7


def m_at(M, ly): return M + 5 * math.log10(ly / LY_PC / 10)
def fmt(m): return ("−" if m < 0 else "") + f"{abs(m):.1f}"


SN = dict(M=-17.0, ly=1000.0); SN["m"] = m_at(SN["M"], SN["ly"])
KN = dict(M=-15.8, ly=500.0); KN["m"] = m_at(KN["M"], KN["ly"])
GRB = dict(m=5.3, ly=7.5e9)
QSO = dict(m=12.9, M=-26.7, ly=2.4e9)
QGC = dict(M=QSO["M"], ly=26000.0); QGC["m"] = m_at(QGC["M"], QGC["ly"])
# magnetar: peak gamma-ray flux vs the full Moon's total irradiance (~ Sun / 4.2e5)
MAG_FLUENCE, MAG_SPIKE = 1.0e-3, 0.2            # J/m^2 (= 1 erg/cm^2), s
F_MOON = 1361.0 * 10 ** (-0.4 * (M_MOON - M_SUN))

if __name__ == "__main__":
    def x(m, ref): return 10 ** (-0.4 * (m - ref))
    print(f"supernova  1,000 ly: m = {SN['m']:.2f}  = {x(SN['m'], M_VENUS):.0f}x Venus, {x(SN['m'], M_MOON):.3f}x full Moon")
    print(f"kilonova     500 ly: m = {KN['m']:.2f}  = {x(KN['m'], M_VENUS):.0f}x Venus, {x(KN['m'], M_MOON):.3f}x full Moon")
    print(f"GRB 080319B 7.5 Gly: m = 5.3 (naked-eye limit ~6 in a dark sky; invisible in a lit city)")
    print(f"magnetar flare: peak flux ~{MAG_FLUENCE / MAG_SPIKE * 1e3:.0f} mW/m^2 vs full Moon {F_MOON * 1e3:.1f} mW/m^2 -> {MAG_FLUENCE / MAG_SPIKE / F_MOON:.1f}x (gamma rays)")
    print(f"3C 273 at 2.4 Gly: m = 12.9; at the galactic centre: m = {QGC['m']:.2f} = {x(QGC['m'], M_MOON):.2f}x full Moon; "
          f"the Sun is {x(M_SUN, QGC['m']):,.0f}x brighter (dust ignored: ~30 mag of extinction really hides the centre)")
