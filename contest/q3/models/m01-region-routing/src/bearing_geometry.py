"""Q1 M01 v01: directed bearing wedges, polygon diameter and enclosing disk.

All coordinates are metres, public angles degrees, inequalities A @ x <= b.
This module makes no stochastic noise assumption and no simulator requests.
"""
from dataclasses import dataclass
from itertools import combinations
import numpy as np
from scipy.optimize import linprog


@dataclass
class Region:
    status: str
    vertices: np.ndarray
    max_residual: float = 0.0


def unit(degrees):
    a = np.deg2rad(degrees)
    return np.array([np.cos(a), np.sin(a)])


def bearing(point, sensor):
    d = np.asarray(point) - np.asarray(sensor)
    return float(np.rad2deg(np.arctan2(d[1], d[0])) % 360)


def angle_difference(a, b):
    return (np.asarray(a) - np.asarray(b) + 180) % 360 - 180


def wedge(sensor, angle_deg, epsilon_deg=1.0):
    """Closed, forward wedge; valid for 0 < epsilon < 90 degrees."""
    if not 0 < epsilon_deg < 90:
        raise ValueError("epsilon must lie strictly between 0 and 90 degrees")
    s = np.asarray(sensor, dtype=float)
    lower, upper = unit(angle_deg - epsilon_deg), unit(angle_deg + epsilon_deg)
    A = np.array([[lower[1], -lower[0]], [-upper[1], upper[0]]])
    return A, A @ s


def observations_halfplanes(observations, epsilon_deg=1.0):
    parts = [wedge(o['position'], o['bearing_deg'], epsilon_deg) for o in observations]
    if not parts:
        return np.empty((0, 2)), np.empty(0)
    return np.vstack([p[0] for p in parts]), np.hstack([p[1] for p in parts])


def unique_points(points, tol=1e-7):
    kept = []
    for p in points:
        if not any(np.linalg.norm(p - q) <= tol for q in kept):
            kept.append(p)
    return np.array(kept, dtype=float).reshape(-1, 2)


def halfplane_region(A, b, tol=1e-7):
    """Classify without an artificial clipping box; enumerate bounded vertices.

    Four LP support problems distinguish unbounded sets from bounded polygons.
    Pairwise line intersections cost O(m^3), appropriate for few observations.
    The result is floating point, not interval-arithmetic certification.
    """
    A, b = np.asarray(A, float).reshape(-1, 2), np.asarray(b, float)
    if not len(A):
        return Region('unbounded', np.empty((0, 2)))
    lengths = np.linalg.norm(A, axis=1)
    zero = lengths < 1e-15
    if np.any(b[zero] < -tol):
        return Region('empty', np.empty((0, 2)))
    A, b = A[~zero] / lengths[~zero, None], b[~zero] / lengths[~zero]
    if not len(A):
        return Region('unbounded', np.empty((0, 2)))
    feasible = linprog([0, 0], A_ub=A, b_ub=b, bounds=[(None, None)] * 2, method='highs')
    if feasible.status == 2:
        return Region('empty', np.empty((0, 2)))
    if not feasible.success:
        raise RuntimeError(feasible.message)
    # Translation improves conditioning for noncentral observations.
    origin = feasible.x
    rhs = b - A @ origin
    extrema = []
    for c in [[1, 0], [-1, 0], [0, 1], [0, -1]]:
        sol = linprog(c, A_ub=A, b_ub=rhs, bounds=[(None, None)] * 2, method='highs')
        if sol.status == 3:
            return Region('unbounded', np.empty((0, 2)))
        if not sol.success:
            raise RuntimeError(sol.message)
        extrema.append(sol.x)
    points = []
    for i, j in combinations(range(len(A)), 2):
        rows = A[[i, j]]
        if abs(np.linalg.det(rows)) < 1e-12:
            continue
        x = np.linalg.solve(rows, rhs[[i, j]])
        if np.max(A @ x - rhs) <= tol:
            points.append(x)
    if not points:
        points = extrema  # Degenerate point/segment fallback, never arbitrary box.
    vertices = unique_points(points, tol) + origin
    if len(vertices) > 2:
        center = vertices.mean(axis=0)
        order = np.argsort(np.arctan2(vertices[:, 1] - center[1], vertices[:, 0] - center[0]))
        vertices = vertices[order]
    status = 'point' if len(vertices) == 1 else 'segment' if len(vertices) == 2 else 'polygon'
    return Region(status, vertices, float(max(0.0, np.max(A @ vertices.T - b[:, None]))))


def diameter(vertices):
    p = np.asarray(vertices, float).reshape(-1, 2)
    if not len(p):
        raise ValueError('diameter needs a nonempty bounded region')
    d2 = np.sum((p[:, None] - p[None, :]) ** 2, axis=2)
    i, j = np.unravel_index(np.argmax(d2), d2.shape)
    return float(np.sqrt(d2[i, j])), (int(i), int(j))


def enclosing_circle(vertices, tol=1e-8):
    """Enumerate support disks (2 or 3 points), with a diameter-disk shortcut.

    Exact finite-support algorithm in real arithmetic; O(h^4) worst case.
    Final radius is recomputed from all points, giving a conservative numerical
    covering disk even when tolerance affects the support choice.
    """
    p = np.asarray(vertices, float).reshape(-1, 2)
    D, (i, j) = diameter(p)
    center = (p[i] + p[j]) / 2
    if np.max(np.linalg.norm(p - center, axis=1)) <= D / 2 + tol:
        return center, float(np.max(np.linalg.norm(p - center, axis=1))), [i, j]
    best = (np.inf, None, None)
    for i, j, k in combinations(range(len(p)), 3):
        d = p[[j, k]] - p[i]
        determinant = np.linalg.det(d)
        if abs(determinant) <= 1e-13 * max(1., np.linalg.norm(d[0]) * np.linalg.norm(d[1])):
            continue
        offset = np.linalg.solve(2 * d, np.sum(d * d, axis=1))
        r = np.linalg.norm(offset)
        if r >= best[0] + tol:
            continue
        c = p[i] + offset
        distances = np.linalg.norm(p - c, axis=1)
        if distances.max() <= r + tol:
            best = (float(distances.max()), c, [i, j, k])
    if best[1] is None:
        raise ArithmeticError('Could not construct a covering disk; inspect conditioning')
    return best[1], best[0], best[2]


def summarize_region(region):
    if region.status == 'empty':
        return {'status': 'empty', 'diameter_m': None, 'cover_radius_m': None}
    if region.status == 'unbounded':
        return {'status': 'unbounded', 'diameter_m': 'infinity', 'cover_radius_m': 'infinity'}
    D, pair = diameter(region.vertices)
    c, r, support = enclosing_circle(region.vertices)
    return dict(status=region.status, vertices=region.vertices.tolist(), diameter_m=D,
                diameter_pair=list(pair), cover_center=c.tolist(), cover_radius_m=r,
                support_indices=support, diameter_disk_covers=bool(r <= D / 2 + 1e-7),
                guaranteed_clear_possible=bool(r <= 20 - 1e-6),
                max_halfplane_residual_m=region.max_residual)


def clip_polygon(poly, normal, offset, tol=1e-9):
    """Sutherland-Hodgman clipping; caller must supply a genuine prior polygon."""
    p = np.asarray(poly, float).reshape(-1, 2)
    if not len(p):
        return p
    values = p @ normal - offset
    output = []
    for i in range(len(p)):
        j = (i + 1) % len(p)
        inside_i, inside_j = values[i] <= tol, values[j] <= tol
        if inside_i:
            output.append(p[i])
        if inside_i != inside_j:
            t = values[i] / (values[i] - values[j])
            output.append(p[i] + np.clip(t, 0, 1) * (p[j] - p[i]))
    return np.asarray(output, float).reshape(-1, 2)


def clip_halfplanes(poly, A, b):
    for a, rhs in zip(A, b):
        poly = clip_polygon(poly, a, rhs)
        if not len(poly):
            break
    return poly


def outer_disk(center, radius, sides=360):
    """Circumscribed regular polygon, never an inscribed disk approximation."""
    angles = (np.arange(sides) + .5) * 2 * np.pi / sides
    return np.asarray(center) + radius / np.cos(np.pi / sides) * np.column_stack((np.cos(angles), np.sin(angles)))


def disk_halfplanes(center, radius, sides=360):
    angles = np.arange(sides) * 2 * np.pi / sides
    A = np.column_stack((np.cos(angles), np.sin(angles)))
    return A, radius + A @ np.asarray(center)
