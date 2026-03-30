############ Step 3: Merging ############
import subprocess
import numpy as np
import os
from tqdm import tqdm
import argparse
import time
import logging
import sys
from s01_initialise import run_evtool, run_radec2xy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_list(path):
    with open(path) as f:
        return np.array([line.strip() for line in f if line.strip()], dtype=object)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(output_dir: str, center_ra: str, center_dec: str, filtered_list=None, separate_tm: bool = False) -> None:
    """
    Step 3 - Merging.

    Merges tile event lists into a single merged file, runs radec2xy to add
    pixel coordinates, and optionally splits the merged list by Telescope Module.

    If `filtered_list` is None, the function checks for flare-filtered files
    from Step 2 (output_dir/filtered.list).  If those files are not all present
    on disk it falls back to the clean event list from Step 1
    (output_dir/clean.list), allowing Step 2 to be skipped.

    Parameters
    ----------
    output_dir    : str - output directory used by Step 1 (and optionally Step 2)
    center_ra     : str or float - right ascension of image centre (degrees)
    center_dec    : str or float - declination of image centre (degrees)
    filtered_list : array-like or None
        Explicit list of event files to merge.  If None, resolved automatically
        as described above.
    separate_tm   : bool - split merged file into per-TM files (TM 1-9)

    Returns
    -------
    None
    """
    start_time = time.time()
    center_ra  = str(center_ra)
    center_dec = str(center_dec)

    # --- logging (append to existing log) -------------------------------
    main_log = os.path.join(output_dir, "filtering.log")
    logger = logging.getLogger('erosuite.s03')
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
    logger.info('Step 3 - Merging\n')

    # --- resolve the event list to merge --------------------------------
    if filtered_list is not None:
        # Caller supplied explicit list; write a temporary .list file
        use_list = f'{output_dir}/_merge_input.list'
        with open(use_list, 'w') as f:
            for p in filtered_list:
                f.write(f'{p}\n')
        logger.info('Using caller-supplied event list for merging.')
    else:
        filtered_path = f'{output_dir}/filtered.list'
        clean_path    = f'{output_dir}/clean.list'
        if os.path.exists(filtered_path):
            candidates = _read_list(filtered_path)
            if all(os.path.exists(p) for p in candidates):
                use_list = filtered_path
                logger.info('Using flare-filtered event list for merging (Step 2 output).')
            else:
                logger.info('Filtered files not all present on disk; '
                            'falling back to clean event list from Step 1.')
                use_list = clean_path
        else:
            logger.info('filtered.list not found; using clean event list from Step 1.')
            use_list = clean_path

    logger.info(f'  Output directory : {output_dir}')
    logger.info(f'  Center RA        : {center_ra}')
    logger.info(f'  Center Dec       : {center_dec}')
    logger.info(f'  Separate by TM   : {separate_tm}')

    # --- Step 5: merge tiles --------------------------------------------
    logger.info("\n========================================\n")
    logger.info('Merging tiles event list:')

    merged_file = f'{output_dir}/Merged/Merged_020_s05_TM0_Events.fits'
    log_s05 = f'{output_dir}/Merged/merged_evtool_s05.log'

    with open(log_s05, 'w+') as lf:
        run_evtool(f'@{use_list}', merged_file, log_file=lf)
        run_radec2xy(merged_file, center_ra, center_dec, log_file=lf)
        lf.seek(0)
        log_content = lf.readlines()

    evtool_count = sum(1 for l in log_content if 'evtool: DONE' in l)
    radec_count  = sum(1 for l in log_content if 'radec2xy: DONE' in l)

    if evtool_count == 1 and radec_count == 1:
        logger.info('Merged tiles event list successfully.')
    else:
        msg = 'Merging failed (evtool or radec2xy did not complete).'
        logger.info(f'Error: {msg}')
        raise RuntimeError(msg)

    logger.info(f'Log file saved as {log_s05}')

    # --- Step 5.1: optionally separate by TM ---------------------------
    if separate_tm:
        logger.info('\nSeparating merged event list by TM:')
        TM_list = [1, 2, 3, 4, 5, 6, 7]
        log_sep = f'{output_dir}/Merged/separate_TM_evtool_s05.log'

        with open(log_sep, 'w+') as lf:
            for tm in tqdm(TM_list):
                run_evtool(
                    merged_file,
                    f'{output_dir}/Merged/Merged_{tm}20_s05_TM{tm}_Events.fits',
                    telid=f'{tm}',
                    log_file=lf
                )
            # TM8 = pn-equivalent (MOS-off TMs 1,2,3,4,6)
            run_evtool(merged_file,
                       f'{output_dir}/Merged/Merged_820_s05_TM8_Events.fits',
                       telid='1 2 3 4 6', log_file=lf)
            # TM9 = MOS-equivalent (TMs 5,7)
            run_evtool(merged_file,
                       f'{output_dir}/Merged/Merged_920_s05_TM9_Events.fits',
                       telid='5 7', log_file=lf)
            lf.seek(0)
            log_content = lf.readlines()

        evtool_count = sum(1 for l in log_content if 'evtool: DONE' in l)
        expected = len(TM_list) + 2
        if evtool_count == expected:
            logger.info(f'evtool successfully separated merged file into {evtool_count} TM files.')
        else:
            msg = f'Expected {expected} TM files, got {evtool_count}.'
            logger.info(f'Error: {msg}')
            raise RuntimeError(msg)
        logger.info(f'Log file saved as {log_sep}')

    elapsed = time.time() - start_time
    logger.info("\n========================================\n")
    if elapsed < 600:
        logger.info(f'** Merging completed in {elapsed:.2f} seconds **')
    elif elapsed < 3600:
        logger.info(f'** Merging completed in {elapsed / 60:.2f} minutes **')
    else:
        logger.info(f'** Merging completed in {elapsed / 3600:.2f} hours **')
    logger.info("\n========================================\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Step 3: Merge tiles for eROSITA data reduction.')
    parser.add_argument('output_dir',  type=str, help='Output directory (from Step 1 / Step 2)')
    parser.add_argument('center_ra',   type=str, help='Center RA in degrees')
    parser.add_argument('center_dec',  type=str, help='Center Dec in degrees')
    parser.add_argument('--separate_tm', action='store_true', default=False,
                        help='Separate merged event list by Telescope Module (TM 1-9)')
    args = parser.parse_args()
    try:
        run(args.output_dir, args.center_ra, args.center_dec, separate_tm=args.separate_tm)
    except RuntimeError as exc:
        sys.exit(f"Error: {exc}")
