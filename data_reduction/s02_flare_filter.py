############ Step 2: Flare Filtering ############
import subprocess
import numpy as np
from astropy.io import fits
from scipy.optimize import curve_fit
import multiprocess as mp
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
import argparse
import time
import logging
import sys
from s01_initialise import run_evtool, run_flaregti


# ---------------------------------------------------------------------------
# Gaussian fitting and sigma clipping
# ---------------------------------------------------------------------------

def gaussian(x, amplitude, mean, stdev):
    return amplitude * np.exp(-((x - mean) ** 2) / (2 * stdev ** 2))


def fit_gaussian(data, bins='auto'):
    bin_heights, bin_borders = np.histogram(data, bins=bins)
    bin_centers = (bin_borders[:-1] + bin_borders[1:]) / 2
    popt, pcov = curve_fit(gaussian, bin_centers, bin_heights,
                           p0=[1., np.mean(data), np.std(data)])
    return popt, pcov, bin_borders


def sigma_clipping(data, popt):
    data_mean = popt[1]
    data_std  = popt[2]
    sigma_threshold = data_std * 3
    if sigma_threshold > 0:
        lower_limit = data_mean - sigma_threshold
        upper_limit = data_mean + sigma_threshold
    else:
        lower_limit = data_mean + sigma_threshold
        upper_limit = data_mean - sigma_threshold
    clipped_data = data[(data >= lower_limit) & (data <= upper_limit)]
    return clipped_data, lower_limit, upper_limit


def threshold_lightcurve(input_data, ff_plots=True, output_dir=None):
    if output_dir is None:
        output_dir = os.path.dirname(input_data)

    lightcurve = fits.open(input_data)
    time_arr   = lightcurve[1].data['TIME']
    rate       = lightcurve[1].data['RATE']
    positive_rate = rate[rate > 0]

    popt_rate, _, rate_borders = fit_gaussian(rate)
    popt_pos,  _, _            = fit_gaussian(positive_rate)
    clipped_data, lower_limit, upper_limit = sigma_clipping(positive_rate, popt_pos)
    popt_clip, _, _ = fit_gaussian(clipped_data, bins=rate_borders)

    if ff_plots:
        plt.rc('font', family='DejaVu Serif', size=11)

        fig, ax = plt.subplots(3, 1, figsize=(8, 7))
        fig.subplots_adjust(hspace=0.4)

        main_color           = 'tab:red'
        clipping_region_color = 'k'

        ax[0].plot((time_arr - time_arr[0]) / 1e3, rate, lw=1.5, color=main_color)
        ax[0].set_ylabel('Rate \n $[\\mathrm{cts\\ s^{-1}\\ deg^{-2}}]$')
        ax[0].set_xlabel('Time [ks]')
        ax[0].axhline(popt_rate[1], color=clipping_region_color, linestyle='--', label='Mean')
        ax[0].axhspan(lower_limit, upper_limit, color=clipping_region_color, alpha=0.3,
                      label='Clipping Region')
        ax[0].legend()

        ax[1].plot(np.arange(0, len(rate)) * 10 / 1e3, rate, lw=1.5, color=main_color)
        ax[1].set_ylabel('Rate \n $[\\mathrm{cts\\ s^{-1}\\ deg^{-2}}]$')
        ax[1].set_xlabel('Time [ks]')
        ax[1].axhline(popt_rate[1], color=clipping_region_color, linestyle='--', label='Mean')
        ax[1].axhspan(lower_limit, upper_limit, color=clipping_region_color, alpha=0.3,
                      label='Clipping Region')
        ax[1].legend()

        x_fit = np.linspace(rate_borders[0], rate_borders[-1], 100)
        ax[2].hist(rate, bins=rate_borders, alpha=0.5, label='Data', color=main_color)
        ax[2].axvspan(lower_limit, upper_limit, color='steelblue', alpha=0.25)
        ax[2].hist(clipped_data, bins=rate_borders, alpha=0.75, label='Clipped Data',
                   color='tab:blue')
        ax[2].plot(x_fit, gaussian(x_fit, *popt_clip), label='Fitted Gaussian (Clipped)',
                   color='tab:red')
        ax[2].set_xlabel('Rate $[\\mathrm{cts\\ s^{-1}\\ deg^{-2}}]$')
        ax[2].set_ylabel('Counts')
        ax[2].legend()

        plot_path = os.path.join(output_dir,
                                 os.path.basename(input_data).replace('.fits', '.png'))
        fig.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

    return upper_limit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_list(path):
    with open(path) as f:
        return np.array([line.strip() for line in f if line.strip()], dtype=object)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(output_dir: str, clean_list=None, lc0_list=None, lc_list=None,
        filtered_list=None, ff_plots: bool = True, ff_proof: bool = False, timebin: str = '20') -> dict:
    """
    Step 2 - Flare Filtering (Steps 2-4).

    Extracts initial lightcurves, calculates per-tile count-rate thresholds
    via Gaussian fitting + 3σ sigma clipping, re-runs flaregti with those
    thresholds, then applies the resulting GTI with evtool.

    Parameters
    ----------
    output_dir    : str - output directory used by Step 1
    clean_list, lc0_list, lc_list, filtered_list :
        array-like or None.  If None, lists are read from the *.list files
        written by s01_initialise in output_dir.
    ff_plots      : bool - save diagnostic lightcurve / Gaussian plots
    ff_proof      : bool - run an extra proof-check pass after filtering

    Returns
    -------
    dict with key: filtered_list
    """
    start_time = time.time()
    timebin = str(timebin)
    plt.rc('ytick', direction='in', right=True)
    plt.rc('axes', linewidth=1.15)
    plt.rc("mathtext", fontset="dejavuserif")

    # --- logging (append to existing log) -------------------------------
    main_log = os.path.join(output_dir, "filtering.log")
    logger = logging.getLogger('erosuite.s02')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(main_log, mode='a')
    ch = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter('%(message)s')
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("\n========================================\n")
    logger.info('Step 2 - Flare Filtering\n')

    # --- load lists if not provided -------------------------------------
    if clean_list    is None: clean_list    = _read_list(f'{output_dir}/clean.list')
    if filtered_list is None: filtered_list = _read_list(f'{output_dir}/filtered.list')

    # Build lc paths using the caller-specified timebin so flaregti writes
    # correctly-named files regardless of what s01 hardcoded.
    n = len(clean_list)
    lc0_list = np.empty(n, dtype=object)
    lc_list  = np.empty(n, dtype=object)
    for i, cl in enumerate(clean_list):
        base = os.path.basename(cl).replace('c010_s01_CleanedEvents.fits', '')
        lc0_list[i] = f'{output_dir}/Lightcurves/{base}c010_s02_LC0_tb{timebin}.fits'
        lc_list[i]  = f'{output_dir}/Lightcurves/{base}c010_s03_LC_tb{timebin}.fits'
    logger.info(f'  Output directory : {output_dir}')
    logger.info(f'  Time bin size    : {timebin} s')
    logger.info(f'  Create FF plots  : {ff_plots}')
    logger.info(f'  Proof-check      : {ff_proof}')
    logger.info(f'  Tiles to process : {n}')

    # --- Step 1: extract initial lightcurves ----------------------------
    logger.info("\n========================================\n")
    logger.info('1) Extracting lightcurves for all tiles:')

    log_s02 = f'{output_dir}/Lightcurves/flaregti_s02.log'
    open(log_s02, 'w').close()

    def _worker_s02(tile):
        with open(log_s02, 'a') as lf:
            run_flaregti(clean_list[tile], lc0_list[tile], timebin=timebin, log_file=lf)

    with mp.Pool() as pool:
        list(tqdm(pool.map(_worker_s02, range(n)), total=n))

    logger.info(f'Log file saved as {log_s02}')

    with open(log_s02) as lf:
        count = sum(1 for line in lf if 'flaregti: DONE' in line)
    if count == 0:
        msg = 'flaregti did not finish successfully for any file.'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)
    elif count < n:
        msg = f'flaregti finished for {count}/{n} files only.'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)
    else:
        logger.info(f'flaregti finished successfully for {count}/{n} files (100%)')

    # --- Step 1.1: calculate thresholds ---------------------------------
    logger.info('\n1.1) Calculating thresholds for flare filtering:')
    lc_plot_dir = f'{output_dir}/Lightcurves/'
    tile_thresholds = np.zeros(n)
    for i in range(n):
        tile_thresholds[i] = threshold_lightcurve(lc0_list[i], ff_plots=ff_plots,
                                                   output_dir=lc_plot_dir)
    if ff_plots:
        logger.info(f'Flare filtering plots saved in {lc_plot_dir}')

    # --- Step 2: run flaregti with thresholds ---------------------------
    logger.info("\n========================================\n")
    logger.info('2) Running flaregti with calculated thresholds:')

    log_s03 = f'{output_dir}/Lightcurves/flaregti_s03.log'
    open(log_s03, 'w').close()

    def _worker_s03(tile):
        with open(log_s03, 'a') as lf:
            run_flaregti(clean_list[tile], lc_list[tile], timebin=timebin,
                         threshold=tile_thresholds[tile], log_file=lf)

    with mp.Pool() as pool:
        list(tqdm(pool.map(_worker_s03, range(n)), total=n))

    logger.info(f'Log file saved as {log_s03}')

    with open(log_s03) as lf:
        count = sum(1 for line in lf if 'flaregti: DONE' in line)
    if count == 0:
        msg = 'flaregti (step 2) did not finish successfully for any file.'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)
    elif count < n:
        msg = f'flaregti (step 2) finished for {count}/{n} files only.'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)
    else:
        logger.info(f'flaregti finished successfully for {count}/{n} files (100%)')

    # --- Step 3: apply GTI with evtool ----------------------------------
    logger.info("\n========================================\n")
    logger.info('3) Running evtool with flare-filtered GTI:')

    log_s04 = f'{output_dir}/evtool_s04.log'
    open(log_s04, 'w').close()

    def _worker_s04(tile):
        with open(log_s04, 'a') as lf:
            run_evtool(clean_list[tile], filtered_list[tile], gti_type='FLAREGTI', log_file=lf)

    with mp.Pool() as pool:
        list(tqdm(pool.map(_worker_s04, range(n)), total=n))

    logger.info(f'Log file saved as {log_s04}')

    with open(log_s04) as lf:
        evtool_count = sum(1 for line in lf if 'evtool: DONE' in line)
    if evtool_count == 0:
        msg = 'evtool (GTI application) did not finish successfully for any file.'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)
    elif evtool_count < n:
        msg = f'evtool (GTI application) finished for {evtool_count}/{n} files only.'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)
    else:
        logger.info(f'evtool finished successfully for {evtool_count}/{n} files (100%)')

    # --- Step 3.1: optional proof check ---------------------------------
    if ff_proof:
        logger.info('\n3.1) Proof checking flare filtering:')
        proof_dir = f'{output_dir}/Lightcurves/Proof_check'
        os.makedirs(proof_dir, exist_ok=True)

        pc_lc_list  = np.empty(n, dtype=object)
        for i in range(n):
            base = os.path.basename(filtered_list[i]).replace('s04_FlareFilteredEvents.fits', '')
            pc_lc_list[i]  = f'{proof_dir}/{base}s041_pcLC.fits'

        log_s041 = f'{proof_dir}/flaregti_s041.log'
        open(log_s041, 'w').close()

        def _worker_s041(tile):
            with open(log_s041, 'a') as lf:
                run_flaregti(filtered_list[tile], pc_lc_list[tile], log_file=lf)

        with mp.Pool() as pool:
            list(tqdm(pool.map(_worker_s041, range(n)), total=n))

        with open(log_s041) as lf:
            count = sum(1 for line in lf if 'flaregti: DONE' in line)
        if count == 0:
            msg = 'proof-check flaregti did not finish for any file.'
            logger.info(f'Error: {msg}')
            raise RuntimeError(msg)
        elif count < n:
            msg = f'proof-check flaregti finished for {count}/{n} files only.'
            logger.info(f'Error: {msg}')
            raise RuntimeError(msg)
        else:
            logger.info(f'flaregti (proof check) finished for {count}/{n} files (100%)')

        for tile in tqdm(range(n)):
            threshold_lightcurve(pc_lc_list[tile], ff_plots=True, output_dir=proof_dir)
        logger.info(f'Proof-check plots saved in {proof_dir}')

    elapsed = time.time() - start_time
    logger.info("\n========================================\n")
    if elapsed < 600:
        logger.info(f'** Flare filtering completed in {elapsed:.2f} seconds **')
    elif elapsed < 3600:
        logger.info(f'** Flare filtering completed in {elapsed / 60:.2f} minutes **')
    else:
        logger.info(f'** Flare filtering completed in {elapsed / 3600:.2f} hours **')
    logger.info("\n========================================\n")

    return {'filtered_list': filtered_list}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Step 2: Flare filtering for eROSITA data reduction.')
    parser.add_argument('output_dir', type=str,
                        help='Output directory used by Step 1 (s01_initialise)')
    parser.add_argument('timebin', type=str, nargs='?', default='20',
                        help='Lightcurve time bin size in seconds (default: 20)')
    parser.add_argument('--ff_plots', action='store_true', default=True,
                        help='Create flare filtering diagnostic plots (default: True)')
    parser.add_argument('--ff_proof', action='store_true', default=False,
                        help='Run a proof-check pass after filtering')
    args = parser.parse_args()
    try:
        run(args.output_dir, ff_plots=args.ff_plots, ff_proof=args.ff_proof,
            timebin=args.timebin)
    except RuntimeError as exc:
        sys.exit(f"Error: {exc}")
