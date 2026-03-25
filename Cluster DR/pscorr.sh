#!/bin/bash
############################################################
# Help                                                     #
############################################################

if [[ $1 == '-h' ]] || [[ $# -ne 0 ]]
then
	echo "   *** pscorr Script ***"
	echo "USAGE: $ ./pscorr.sh"
	echo "Runs fgauss for the cluster inferred from current directory."
	echo "Print this help: $ ./pscorr.sh -h"
	exit
fi

clusname=$(basename "$PWD")
base_dir="/home/asrivast/eRASS1/${clusname}/filtered/PIBsub_0.2-2.3_combinedtiles"
sb_dir="/home/asrivast/eRASS1/${clusname}/filtered/SB"
input_fits="${base_dir}/c010_em01_${clusname}_combined_tiles_0BG0_CLCRBGSUB-single_0.2-2.3keV_NHcorr_corr.fits"
output_fits="${sb_dir}/SM10pix.fits"

if [ ! -f "$input_fits" ]
then
	echo "ERROR: input file not found: $input_fits"
	exit 1
fi

mkdir -p "$sb_dir"

echo "[pscorr] Running fgauss for ${clusname}"
cd "$base_dir" || { echo "ERROR: base_dir does not exist: $base_dir"; exit 1; }
fgauss "$(basename "$input_fits")" "../SB/$(basename "$output_fits")" 5 clobber=yes
echo "[pscorr] Wrote ${output_fits}"

echo "[pscorr] DONE"
