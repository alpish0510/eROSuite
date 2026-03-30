# eROSuite

A PyQt6 GUI application for running the eROSITA X-ray astronomy data-reduction pipeline.

## Overview

eROSuite provides a step-by-step graphical interface for:

- **Step 1.1 – Initialisation**: locate raw event files, build file lists, run `evtool` to produce clean event files, and optionally generate a survey tile footprint map.
- **Step 1.2 – Flare Filtering**: extract lightcurves, compute per-tile count-rate thresholds via Gaussian fitting and 3σ sigma-clipping, re-run `flaregti`, and apply the resulting GTI with `evtool`.
- **Step 1.3 – Merging**: merge tile event lists into a single file, run `radec2xy` to add pixel coordinates, and optionally split the output by Telescope Module (TM).
- **Step 2.1 – ...**

The active set of steps is controlled by a **profile** (see [profiles/](profiles/)).

## Prerequisites

- Python ≥ 3.10
- A working [eSASS](https://erosita.mpe.mpg.de/dr1/eSASS4DR1/) installation.
- The Python packages listed in [requirements.txt](requirements.txt)

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd eROSuite

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

```bash
python eROSuite.py
```

The GUI will open. Select a **profile** from the drop-down in the toolbar, fill in the required fields, and either run individual steps or click **Run All**.

Each pipeline step can also be run directly from the command line:

```bash
# Step 1
python data_reduction/s01_initialise.py <input_dir> <output_dir> [--no_tile_map]

# Step 2
python data_reduction/s02_flare_filter.py <output_dir> [timebin] [--ff_proof]

# Step 3
python data_reduction/s03_merge.py <output_dir> <center_ra> <center_dec> [--separate_tm]

# Step 4 ...
```

## Profiles

Profiles are JSON files in [profiles/](profiles/) that list which steps to show in the GUI.

| Profile | File | Steps |
|---------|------|-------|
| Cluster Data Reduction | `Cluster.json` | 1.1, 1.2, 1.3 |
| SNR Data Reduction | `SNR.json` | (see file) |
| Custom | `custom.json` | Edit to customize |

The `steps` array contains step IDs that must match keys in [steps_registry.json](steps_registry.json).

## Data Layout

Expected raw data structure under the `input_dir` you provide to Step 1:

```
input_dir/
  <dec_bin>/
    <ra_bin>/
      EXP_010/
        e?01_??????_020_EventList_c010.fits.gz
```

Outputs are written to the `output_dir` you specify:
