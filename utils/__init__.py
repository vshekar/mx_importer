from math import tan, asin, pi

EV_ANGSTROM_CONSTANT = 12398.42


def distance_from_reso(det_radius, reso, wave, theta):
    try:
        dg2rd = pi / 180.0
        theta_radians = float(theta) * dg2rd
        dx = float(det_radius) / (
            tan(2 * (asin(float(wave) / (2 * float(reso)))) - theta_radians)
        )
        return float("%.2f" % dx)
    except ValueError:
        return 501.0  # a safe value for now


def energy2wave(e, digits=2):
    if float(e) == 0.0:
        return 1.0
    else:
        return float(f"%.{digits}f" % (EV_ANGSTROM_CONSTANT / e))
