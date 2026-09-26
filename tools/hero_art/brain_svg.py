"""Turn brain_maps.npz into SVG path data (outline, sulci, depth isolines).

Coordinates: display frame (anterior at left, superior at top), scaled by S and
shifted so the brain's bounding box starts at (0, 0). Writes brain_paths.json.
"""
import json
import numpy as np
from scipy import ndimage as ndi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

S = 3.4          # px per mm
RDP_TOL = 0.35   # mm, polyline simplification

m = np.load("brain_maps.npz")
sil, depth = m["sil"], m["depth"]
disp = lambda a: a.T[::-1, ::-1]           # (row=superior..inferior, col=anterior..posterior)
sil_d = disp(sil).astype(float)
dep = disp(np.nan_to_num(depth, nan=np.nanmax(depth)))


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    n = np.hypot(*ab) or 1e-9
    v = pts - a
    d = np.abs(ab[0] * v[:, 1] - ab[1] * v[:, 0]) / n
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([rdp(pts[:i + 1], eps)[:-1], rdp(pts[i:], eps)])
    return np.vstack([a, b])


def contours(arr, level, min_len=0):
    fig, ax = plt.subplots()
    cs = ax.contour(arr, levels=[level])
    plt.close(fig)
    out = []
    for seg in cs.allsegs[0]:
        if len(seg) < 4:
            continue
        length = np.sum(np.hypot(*np.diff(seg, axis=0).T))
        if length < min_len:
            continue
        out.append(seg)
    return out


def rdp_closed(pts, eps):
    """RDP for a closed loop: split at the point farthest from the start, simplify each half."""
    k = int(np.argmax(np.hypot(*(pts - pts[0]).T)))
    if k in (0, len(pts) - 1):
        return pts
    return np.vstack([rdp(pts[:k + 1], eps)[:-1], rdp(pts[k:], eps)])


def smooth_path(seg, closed=True):
    """Quadratic curves through segment midpoints: smooth, compact SVG."""
    closed = closed and np.allclose(seg[0], seg[-1])
    p = rdp_closed(seg, RDP_TOL) if closed else rdp(seg, RDP_TOL)
    if closed and np.allclose(p[0], p[-1]):
        p = p[:-1]
    if len(p) < 3:
        return ""
    p = p * S
    if closed:
        mids = (p + np.roll(p, -1, axis=0)) / 2
        d = f"M{mids[-1][0]:.1f} {mids[-1][1]:.1f}"
        for i in range(len(p)):
            d += f"Q{p[i][0]:.1f} {p[i][1]:.1f} {mids[i][0]:.1f} {mids[i][1]:.1f}"
        return d + "Z"
    d = f"M{p[0][0]:.1f} {p[0][1]:.1f}"
    for i in range(1, len(p) - 1):
        mid = (p[i] + p[i + 1]) / 2
        d += f"Q{p[i][0]:.1f} {p[i][1]:.1f} {mid[0]:.1f} {mid[1]:.1f}"
    return d + f"L{p[-1][0]:.1f} {p[-1][1]:.1f}"


# Outline: smoothed silhouette, largest contour.
sil_s = ndi.gaussian_filter(sil_d, 2.2)
outline = max(contours(sil_s, 0.5), key=len)
# contour() returns (x=col, y=row) already
xmin, ymin = outline.min(axis=0)
xmax, ymax = outline.max(axis=0)
shift = np.array([xmin, ymin])

# Sulci: local depth, restricted away from the rim.
d = ndi.gaussian_filter(dep, 1.0)
sulc = d - ndi.gaussian_filter(d, 6)
core = ndi.binary_erosion(sil_s > 0.5, iterations=5)
sulc_masked = np.where(core, sulc, -10)
sulci = [s for s in contours(ndi.gaussian_filter(sulc_masked, 0.8), 1.1, min_len=10)]

# Depth isolines for a topographic look (smoothed depth inside the brain).
ds = ndi.gaussian_filter(np.where(sil_s > 0.5, dep, np.nanmax(dep)), 2.5)
inner = np.where(sil_s > 0.5, ds, np.nan)
levels = np.nanpercentile(inner, [15, 35, 55, 75, 90])
iso = {f"{i}": [smooth_path(s - shift) for s in contours(np.where(sil_s > 0.5, ds, ds.max()), lv, min_len=25)]
       for i, lv in enumerate(levels)}

# Mask for point-in-brain sampling (in scaled px), stored as run-length rows.
core_px = ndi.binary_erosion(sil_s > 0.5, iterations=3)

data = {
    "S": S,
    "width": round(float((xmax - xmin) * S), 1),
    "height": round(float((ymax - ymin) * S), 1),
    "outline": smooth_path(outline - shift),
    "sulci": [smooth_path(s - shift) for s in sulci],
    "iso": iso,
    "mask_origin": [float(xmin), float(ymin)],
    "mask": core_px.astype(int).tolist(),
}
json.dump(data, open("brain_paths.json", "w"))
print("size px", data["width"], "x", data["height"], "| sulci", len(sulci),
      "| iso", {k: len(v) for k, v in iso.items()},
      "| outline chars", len(data["outline"]), "| sulci chars", sum(map(len, data["sulci"])))
