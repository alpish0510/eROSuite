############ Step 1: Initialisation ############
import glob
import subprocess
import numpy as np
import multiprocess as mp
import os
import importlib.util
from tqdm import tqdm
import argparse
import time
import logging
import sys


def run_evtool(input_name: str, output_name: str, gti_type: str = 'GTI', flag_type: str = '0xe00fff30', pattern: str = '15',
               emin: str = '0.2', emax: str = '10.0', image: str = 'no', events: str = 'yes', telid: str = '1 2 3 4 5 6 7', log_file=None) -> None:
    subprocess.run(['evtool', 
                    f'eventfiles={input_name}', 
                    f'outfile={output_name}', 
                    f'gti={gti_type}', 
                    f'flag={flag_type}', 
                    f'pattern={pattern}', 
                    f'emin={emin}', 
                    f'emax={emax}',
                    f'image={image}',
                    f'events={events}',
                    f'telid={telid}'
                    ],
                    stdout=log_file,
                    stderr=log_file)
    
def run_flaregti(input_name: str, output_lightcurve: str, pimin: str = '5000', source_size: str = '150', gridsize: str = '26',
                 timebin: str = '20', threshold: str = '-1', log_file=None) -> None:
    subprocess.run(['flaregti', 
                    f'{input_name}', 
                    f'pimin={pimin}', 
                    f'source_size={source_size}',
                    f'gridsize={gridsize}',
                    f'lightcurve={output_lightcurve}',
                    'write_mask=no',
                    f'timebin={timebin}',
                    f'threshold={threshold}'
                    ],
                    stdout=log_file,
                    stderr=log_file)
    
def run_radec2xy(input_name: str, ra: str, dec: str, log_file=None) -> None:
    subprocess.run(
        ['radec2xy',
         f'{input_name}',
         f'ra0={ra}',
         f'dec0={dec}'],
        stdout=log_file,
        stderr=log_file
    )


# -- locate plot_tiles.py next to this script --------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR   = os.path.join(_SCRIPT_DIR, '..', 'Data')

# Default path for the skymap tile catalogue
_DEFAULT_SKYMAP   = os.path.join(_DATA_DIR, 'SKYMAPS_052022_MPE.fits')


def run(input_dir: str, output_dir: str, tile_map: bool = True, skymap: str | None = None) -> dict:
    """
    Step 1 - Initialisation.

    Locates raw event files, creates output directories, builds and writes file
    lists for downstream steps, then runs evtool to produce clean event files.
    Also produces a tile-footprint map (tile_map.png) in *output_dir*.

    Parameters
    ----------
    input_dir  : str  - directory containing raw eROSITA event files
    output_dir : str  - directory where processed data will be written
    tile_map   : bool - generate the survey tile footprint image (default True)
    skymap     : str or None - path to SMAPS catalogue FITS; auto-detected
                 from <script_dir>/Data/ when None

    Returns
    -------
    dict with keys:
        elist, clean_list, filtered_list,
        lc0_list, lc_list
    """
    start_time = time.time()
    timebin = '20'  # hardcoded default; exposed as a parameter in Step 1.2

    # --- output directory and logging -----------------------------------
    os.makedirs(output_dir, exist_ok=True)

    main_log = os.path.join(output_dir, "filtering.log")
    if os.path.exists(main_log):
        os.remove(main_log)

    logger = logging.getLogger('erosuite.s01')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(main_log)
    ch = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter('%(message)s')
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)

    start_datetime = time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(start_time))
    logger.info(f'Start date and time: {start_datetime}')
    logger.info(f'Command used: python {" ".join(sys.argv)}')
    logger.info("\n========================================\n")
    logger.info('Step 1 - Initialisation\n')

    # --- discover event files -------------------------------------------
    elist = glob.glob(f'{input_dir}/???/???/EXP_010/e?01_??????_020_EventList_c010.fits.gz')
    if not elist:
        msg = f'No event files found in {input_dir}'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)

    # --- create output directories --------------------------------------
    for sub in ('', '/Lightcurves', '/Merged'):
        os.makedirs(f'{output_dir}{sub}', exist_ok=True)

    logger.info('Created output directories:')
    logger.info(f'  {output_dir}')
    logger.info(f'  {output_dir}/Lightcurves')
    logger.info(f'  {output_dir}/Merged')

    # --- build file lists -----------------------------------------------
    n = len(elist)
    clean_list    = np.empty(n, dtype=object)
    lc0_list      = np.empty(n, dtype=object)
    gti0_list     = np.empty(n, dtype=object)
    lc_list       = np.empty(n, dtype=object)
    gti_list      = np.empty(n, dtype=object)
    filtered_list = np.empty(n, dtype=object)

    for i, e in enumerate(elist):
        base = os.path.basename(e).replace('EventList_c010.fits.gz', '')
        clean_list[i]    = f'{output_dir}/{base}c010_s01_CleanedEvents.fits'
        lc0_list[i]      = f'{output_dir}/Lightcurves/{base}c010_s02_LC0_tb{timebin}.fits'
        lc_list[i]       = f'{output_dir}/Lightcurves/{base}c010_s03_LC_tb{timebin}.fits'
        filtered_list[i] = f'{output_dir}/{base}c010_s04_FlareFilteredEvents.fits'

    # Write list files for use by downstream scripts
    for fname, flist in [
        ('clean.list',    clean_list),
        ('filtered.list', filtered_list),
        ('lc0.list',      lc0_list),
        ('lc.list',       lc_list),
    ]:
        with open(f'{output_dir}/{fname}', 'w') as f:
            for path in flist:
                f.write(f'{path}\n')

    logger.info('\nParameters:')
    logger.info(f'  Input directory : {input_dir}')
    logger.info(f'  Output directory: {output_dir}')
    logger.info(f'  Time bin size   : {timebin} s')
    logger.info(f'  Tiles found     : {n}')
    logger.info(f'  Generate tile map: {tile_map}')

    # --- run evtool in parallel -----------------------------------------
    logger.info("\n========================================\n")
    logger.info('Creating clean event list for all tiles:')

    log_s01 = f'{output_dir}/evtool_s01.log'
    open(log_s01, 'w').close()

    def _worker(tile):
        with open(log_s01, 'a') as lf:
            run_evtool(elist[tile], clean_list[tile], log_file=lf)

    with mp.Pool() as pool:
        list(tqdm(pool.map(_worker, range(n)), total=n))

    logger.info(f'\nLog file saved as {log_s01}')

    with open(log_s01) as lf:
        evtool_count = sum(1 for line in lf if 'evtool: DONE' in line)

    if evtool_count == 0:
        msg = 'evtool did not finish successfully for any file.'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)
    elif evtool_count < n:
        msg = f'evtool finished for {evtool_count}/{n} files only.'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)
    else:
        logger.info(f'evtool finished successfully for {evtool_count}/{n} files (100%)')

    # --- tile footprint visualisation -----------------------------------
    _skymap = skymap or _DEFAULT_SKYMAP

    tile_map_path = os.path.join(output_dir, 'tile_map.png')
    if tile_map:
        if _skymap and os.path.isfile(_skymap):
            logger.info("\n========================================\n")
            logger.info('Generating tile footprint map:\n')
            try:
                _spec = importlib.util.spec_from_file_location(
                    'plot_tiles',
                    os.path.join(_SCRIPT_DIR, '..', 'utils', 'plot_tiles.py')
                )
                _pt = importlib.util.module_from_spec(_spec)
                _spec.loader.exec_module(_pt)
                _pt.plot(_skymap, list(elist), tile_map_path,
                         logger=logger)
            except Exception as _exc:
                logger.info(f'Warning: tile map could not be generated: {_exc}')
        else:
            logger.info(f'Skipping tile map (skymap not found: {_skymap})')
    else:
        logger.info('Skipping tile map generation (disabled by user).')

    elapsed = time.time() - start_time
    logger.info("\n========================================\n")
    if elapsed < 600:
        logger.info(f'** Initialisation completed in {elapsed:.2f} seconds **')
    elif elapsed < 3600:
        logger.info(f'** Initialisation completed in {elapsed / 60:.2f} minutes **')
    else:
        logger.info(f'** Initialisation completed in {elapsed / 3600:.2f} hours **')
    logger.info("\n========================================\n")

    return {
        'elist':         elist,
        'clean_list':    clean_list,
        'filtered_list': filtered_list,
        'lc0_list':      lc0_list,
        'lc_list':       lc_list,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Step 1: Initialise eROSITA data reduction.')
    parser.add_argument('input_dir',  type=str, help='Input directory containing raw data')
    parser.add_argument('output_dir', type=str, help='Output directory for processed data')
    parser.add_argument('--no_tile_map', action='store_true', default=False,
                        help='Skip generating the survey tile footprint image')
    args = parser.parse_args()
    try:
        run(args.input_dir, args.output_dir, tile_map=not args.no_tile_map)
    except RuntimeError as exc:
        sys.exit(f"Error: {exc}")
