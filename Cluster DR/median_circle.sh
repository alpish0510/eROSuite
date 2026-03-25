#!/bin/bash
set -euo pipefail

fits_file="/home/asrivast/eRASS1/J025418.0-585646_T/filtered/PIBsub_0.2-2.3_combinedtiles/NHtot_J025418.0-585646_T_52x52box.fits"
sb_dir="/home/asrivast/eRASS1/J025418.0-585646_T/filtered/SB"
ra_deg=43.5692
dec_deg=-58.9491
r_expr="3.65/0.65"  # arcmin

radius_arcmin=$(python3 - <<PY
expr = "${r_expr}"
print(eval(expr))
PY
)

mkdir -p "${sb_dir}"
reg_file="${sb_dir}/NHtot_025418.0-585646_T_52x52box_circle.reg"

cat > "${reg_file}" <<EOF
# Region file format: DS9 version 4.1
fk5;circle(${ra_deg},${dec_deg},${radius_arcmin}')
EOF

python3 - <<PY
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from regions import Regions

fits_file = "${fits_file}"
reg_file = "${reg_file}"

with fits.open(fits_file) as hdul:
    data = hdul[0].data
    wcs = WCS(hdul[0].header)

region = Regions.read(reg_file, format="ds9")[0]
pix_region = region.to_pixel(wcs)
mask = pix_region.to_mask(mode="center")
cutout = mask.cutout(data)
if cutout is None:
    raise RuntimeError("Region falls خارج data bounds")
masked = cutout[mask.data.astype(bool)]
median = np.nanmedian(masked)
print(f"Median inside circle: {median}")
PY
