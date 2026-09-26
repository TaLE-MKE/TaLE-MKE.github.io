"""Derive a lateral-view brain outline and sulcal pattern from the MNI152 template.

Inputs (public template files, no participant data; copy them next to this script):
  MNI152_T1_1mm.nii.gz        full-head T1, 1mm
  MNI152_T1_2mm_brain.nii.gz  brain-extracted T1, 2mm (used as the brain mask)
Output: brain_maps.npz with silhouette mask and lateral depth map, plus a preview PNG.
"""
import gzip, struct
import numpy as np
from scipy import ndimage as ndi


def load_nii(path):
    raw = gzip.open(path).read()
    dim = struct.unpack('<8h', raw[40:56])
    dt = struct.unpack('<h', raw[70:72])[0]
    off = int(struct.unpack('<f', raw[108:112])[0])
    dtype = {2: np.uint8, 4: np.int16, 16: np.float32, 64: np.float64}[dt]
    n = dim[1] * dim[2] * dim[3]
    return np.frombuffer(raw[off:off + n * np.dtype(dtype).itemsize], dtype=dtype).reshape(dim[1:4], order='F').astype(np.float32)


t1 = load_nii("MNI152_T1_1mm.nii.gz")            # 182 x 218 x 182
b2 = load_nii("MNI152_T1_2mm_brain.nii.gz")      # 91 x 109 x 91
mask = ndi.zoom((b2 > 0).astype(np.float32), 2, order=1)[:182, :218, :182] > 0.5
mask = ndi.binary_fill_holes(mask)

# Silhouette seen from the left: any brain voxel along x.
sil = mask.any(axis=0)                            # (y, z)

# Tissue (GM/WM) vs CSF inside the mask, from the 1mm T1.
inside = t1[mask]
thr = np.percentile(inside, 30)                   # below ~ CSF / dark sulci
tissue = mask & (t1 > thr)

# Left hemisphere lateral surface: FSL MNI index i increases toward the subject's left,
# so scan from the high-i side and record how deep the first tissue voxel is.
first = np.argmax(tissue[::-1, :, :], axis=0).astype(np.float32)   # depth from the left edge
first[~sil] = np.nan
np.savez("brain_maps.npz", sil=sil, depth=first)

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
d = np.nan_to_num(first, nan=np.nanmax(first))
d = ndi.gaussian_filter(d, 1.0)
sulc = d - ndi.gaussian_filter(d, 6)             # local depth: positive = deeper than surroundings
disp = lambda a: a.T[::-1, ::-1]                 # rows = superior at top, columns = anterior at left
fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
ax[0].imshow(disp(sil), cmap="gray"); ax[0].set_title("silhouette")
ax[1].imshow(disp(np.where(sil, d, np.nan)), cmap="viridis"); ax[1].set_title("lateral depth")
ax[2].imshow(disp(np.where(sil, sulc, np.nan)), cmap="RdBu_r", vmin=-4, vmax=4); ax[2].set_title("sulcal (local depth)")
for a in ax: a.axis("off")
plt.tight_layout(); plt.savefig("brain_preview.png", dpi=70)
print("tissue thr", thr, "sil px", sil.sum())
