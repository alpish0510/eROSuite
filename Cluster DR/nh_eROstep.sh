#!/bin/bash
############################################################
# Help                                                     #
############################################################

if [[ $1 == '-h' ]] || [[ $# -ne 1 ]]
then
	echo "   *** nh_eROstep Script ***"
	echo "USAGE: $ ./nh_eROstep.sh cluster_name"
	echo "cluster_name: cluster name (e.g., J064529.1-541334)"
	echo "Print this help: $ ./nh_eROstep.sh -h"
	exit
fi

clusname=$1

cd "/home/asrivast/eRASS1/$clusname" || { echo "ERROR: workdir does not exist: $workdir"; exit 1; }

echo "[nh_eROstep] Running PY_cut_and_reproject"
./PY_cut_and_reproject.py /home/asrivast/eRASS1/"$clusname"/filtered/PIBsub_0.2-2.3_combinedtiles c010_em01_"$clusname"_combined_tiles_0BG0_CLCRBGSUB-single_0.2-2.3keV_corr "$clusname"

echo "[nh_eROstep] Running PY_query_WillingaleNH2w"
./PY_query_WillingaleNH2w.py /home/asrivast/eRASS1/"$clusname"/filtered/PIBsub_0.2-2.3_combinedtiles AIT_-600_600_cutto"$clusname"_repr.fits "$clusname"

echo "[nh_eROstep] Running PY_simulate_NHlist"
./PY_simulate_NHlist.py /home/asrivast/eRASS1/"$clusname"/filtered/PIBsub_0.2-2.3_combinedtiles NHtot_"$clusname"_52x52box "$clusname" --lo8 0.2 --lo9 0.8 --hi 2.3

echo "[nh_eROstep] Running PY_NH_corr_map for TM1"
./PY_NH_corr_map.py /home/asrivast/eRASS1/"$clusname"/filtered/PIBsub_0.2-2.3_combinedtiles NHtot_"$clusname"_52x52box RESULTS_SIM_TM1_0.2-2.3keV_NH_"$clusname" TM1 --low 0.2 --hie 2.3

echo "[nh_eROstep] Running PY_NH_corr_map for TM5"
./PY_NH_corr_map.py /home/asrivast/eRASS1/"$clusname"/filtered/PIBsub_0.2-2.3_combinedtiles NHtot_"$clusname"_52x52box RESULTS_SIM_TM5_0.8-2.3keV_NH_"$clusname" TM5 --low 0.8 --hie 2.3

echo "[nh_eROstep] Running SH_PIBSUB-NHcorr"
./SH_PIBSUB-NHcorr.sh em01 "$clusname" c010 0.2 0.8 2.3 NHtot_"$clusname"_52x52box_TM1_0.2-2.3keV_CORR_map NHtot_"$clusname"_52x52box_TM5_0.8-2.3keV_CORR_map
echo "[nh_eROstep] DONE"