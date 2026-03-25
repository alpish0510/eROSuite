#!/usr/bin/env python3
import numpy as np
from astropy.io import fits
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.cosmology import FlatLambdaCDM
cosmo = FlatLambdaCDM(H0=70.0 * u.km / u.s / u.Mpc, Om0=0.3)
from astropy.visualization import simple_norm
from astropy import wcs
from astropy.wcs import WCS
from astropy.convolution import Gaussian2DKernel
from astropy.convolution import convolve
import subprocess
from scipy.ndimage import gaussian_filter
import matplotlib
import matplotlib.pyplot as plt
plt.style.use('default')
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from PIL import Image

import pickle
import os
import math
import argparse
from tqdm import tqdm
import multiprocessing as mp

parser = argparse.ArgumentParser(description="PS detection script using eRASS1 PS catalog")
parser.add_argument("Clus_name", type=str, help="Name of the cluster")
parser.add_argument("--DET_LIKE", type=float, default=6.0, help="Detection likelihood")
default_nproc = 5
parser.add_argument(
    "--nproc",
    type=int,
    default=default_nproc,
    help="Number of processes to use (default: 5)",
)
parser.add_argument(
    "--maxtasksperchild",
    type=int,
    default=25,
    help="Recycle worker processes after this many tasks (default: 25)",
)
args = parser.parse_args()
clusname = args.Clus_name
det_lik = args.DET_LIKE
nproc = max(1, args.nproc)
maxtasksperchild = args.maxtasksperchild


base_dir = f"/home/asrivast/eRASS1/{clusname}/filtered/PIBsub_0.2-2.3_combinedtiles"
sb_dir = f"/home/asrivast/eRASS1/{clusname}/filtered/SB"
ima_file = f"{base_dir}/c010_em01_{clusname}_combined_tiles_0BG0_CLCRBGSUB-single_0.2-2.3keV_NHcorr_corr.fits"
mask_file = f'{clusname}_PSmask.fits'
pts_cat = '/home/asrivast/eRASS1/Catalogs/eRASS1_Main.v1.1.fits'

# eROSITA dr1 source catalog:
# https://erosita.mpe.mpg.de/dr1/AllSkySurveyData_dr1/Catalogues_dr1/MerloniA_DR1/eRASS1_Main.tar.gz

hdulist = fits.open(ima_file)
ima = hdulist[0].data
prihdr = hdulist[0].header
pix2deg = prihdr['CDELT2'] # deg
xsize, ysize = ima.shape
# mask = np.ones_like(ima, dtype=float)

ima_wcs = wcs.WCS(prihdr, relax=False)
ima_racen = ima_wcs.pixel_to_world(ysize / 2 + 0.5, xsize / 2 + 0.5).ra.deg
ima_deccen = ima_wcs.pixel_to_world(ysize / 2 + 0.5, xsize / 2 + 0.5).dec.deg
ima_r = np.max((xsize,ysize)) / 2 * pix2deg # deg
ima_coord = SkyCoord(ima_racen * u.deg, ima_deccen * u.deg, frame = 'icrs')

cat_src = fits.open(pts_cat)[1].data
#cat_src = cat_src[(cat_src.EXT == 0) & (cat_src.DET_LIKE_0 > 8)] # Select high S/N point sources with DET_LIKE>8
cat_src = cat_src[(cat_src.DET_LIKE_0 > det_lik)]
coord_src = SkyCoord(cat_src.RA * u.deg, cat_src.DEC * u.deg, frame = 'icrs')
sep = ima_coord.separation(coord_src).to(u.deg).value
cat_src = cat_src[sep < ima_r + 1/60] # Select sources within the image

ra_src = cat_src.RA
dec_src = cat_src.DEC

# Fix the masking radius to 1arcmin for point sources (EXT==0), otherwise use EXT in arcsec.
ext_src = np.where(cat_src['EXT'] != 0, cat_src['EXT'] / 3600.0, 1/60)

def circle(X, Y):
    x, y = np.meshgrid(X, Y)
    rho = np.sqrt(x * x + y * y)
    return rho


def _init_worker(ra_src, dec_src, ext_src, ima_wcs, x, y, pix2deg):
    global _ra_src, _dec_src, _ext_src, _ima_wcs, _x, _y, _pix2deg
    _ra_src = ra_src
    _dec_src = dec_src
    _ext_src = ext_src
    _ima_wcs = ima_wcs
    _x = x
    _y = y
    _pix2deg = pix2deg


def _mask_indices(j):
    pixim = _ima_wcs.all_world2pix([[float(_ra_src[j]), float(_dec_src[j])]], 0)
    xp = pixim[0][0]
    yp = pixim[0][1]
    rho = circle(_x - xp, _y - yp) * _pix2deg
    ii = np.where(rho <= _ext_src[j])
    return ii


def _region_line(i):
    return f"fk5; circle({_ra_src[i]},{_dec_src[i]},{_ext_src[i]})"

x = np.arange(ysize)
y = np.arange(xsize)
ctx = mp.get_context("fork")
with ctx.Pool(processes=nproc, initializer=_init_worker,
              initargs=(ra_src, dec_src, ext_src, ima_wcs, x, y, pix2deg),
              maxtasksperchild=maxtasksperchild) as pool:
    # Masking is disabled; only create region lines.
    # for ii in tqdm(pool.imap_unordered(_mask_indices, range(len(ra_src))),
    #                total=len(ra_src), desc="Masking sources"):
    #     if len(ii[0]) > 0:
    #         mask[ii] = 0

    lines = list(tqdm(pool.imap_unordered(_region_line, range(len(ra_src))),
                      total=len(ra_src), desc="Writing regions"))

# Full rectangular image mask (no circular edge mask).
from pathlib import Path

Path(sb_dir).mkdir(parents=True, exist_ok=True)
with open(f'{sb_dir}/PScat_{det_lik}.reg', 'w') as f:
    f.write("\n".join(lines) + "\n")

    # hdu.header.update(ima_wcs.to_header())
    # hdulist = fits.HDUList([hdu])

print("done!")