# Home page hero art

The home banner rotates two illustrations (`assets/img/hero-brain-1.svg`, trajectories inside; `hero-brain-2.svg`, lifespan) built on a brain
outline and sulcal pattern taken from the **MNI152 T1 template** (public; no participant data).

Rebuild, in order (run from this folder):

1. `python3 mri_brain.py`: needs `MNI152_T1_1mm.nii.gz` and `MNI152_T1_2mm_brain.nii.gz` copied
   here (FSL's standard templates; Jamie has copies in Dropbox). Writes `brain_maps.npz` and a preview PNG.
2. `python3 brain_svg.py`: turns the maps into SVG paths, `brain_paths.json` (committed).
3. `python3 hero_variants.py`: writes the two SVGs into `assets/img/`. Needs only `brain_paths.json`.

To restyle the art, edit `hero_variants.py` and rerun step 3. It also defines three unused styles
(`v2` connectome, `v3` clean line art, `v5` depth map).

Needs Python with numpy, scipy, and matplotlib. The NIfTI files are read with plain numpy, no nibabel.
