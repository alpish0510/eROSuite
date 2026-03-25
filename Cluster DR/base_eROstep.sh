#!/bin/bash
############################################################
# Help                                                     #
############################################################

if [[ $1 == '-h' ]] || [[ $# -ne 9 ]]
then
	echo "   *** base_eROstep Script ***"
	echo "USAGE: $ ./base_eROstep.sh workdir cluster_name prefix proc_ver ra dec img_size low_ene high_ene"
	echo "workdir: base directory for the target (e.g., /home/asrivast/eRASS1/J023218.3-442048)"
	echo "cluster_name: cluster name (e.g., A3391)"
	echo "prefix: observation name (e.g., sm03, em01)"
	echo "proc_ver: processing version (e.g., c946, c010, c020)"
	echo "ra: right ascension in degrees (e.g., 35.1234)"
	echo "dec: declination in degrees (e.g., -44.5678)"
	echo "img_size: image size in pixels (e.g., 10000)"
	echo "low_ene: lower energy limit in keV (e.g., 0.2)"
	echo "high_ene: upper energy limit in keV (e.g., 2.3)"
	echo "Print this help: $ ./base_eROstep.sh -h"
	exit
fi

workdir=$1
cluster_name=$2
prefix=$3
proc_ver=$4
ra=$5
dec=$6
img_size=$7
low_ene=$8
high_ene=$9

cd "$workdir" || { echo "ERROR: workdir does not exist: $workdir"; exit 1; }
shopt -s nullglob
existing_scripts=("$workdir"/*.py "$workdir"/*.sh)
if [ ${#existing_scripts[@]} -eq 0 ]
then
	echo "[base_eROstep] Unzipping DR pack into $workdir"
	unzip /home/asrivast/eRASS1/Scripts/DR\ pack/dr_pack.zip -d "$workdir" || { echo "ERROR: Failed to unzip dr_pack.zip"; exit 1; }
else
	echo "[base_eROstep] Scripts already present in $workdir; skipping unzip"
fi

echo "[base_eROstep] Running filtering step"
./SH_filtering.sh "$prefix" "$cluster_name" "$proc_ver" "$ra" "$dec" "$img_size" 0

echo "[base_eROstep] Running prep step for TM1"
./SH_prep.sh "$prefix" 1 "$cluster_name" "$proc_ver" "$img_size" "$low_ene" "$high_ene" 0 "$low_ene"
echo "[base_eROstep] Running prep step for TM2"
./SH_prep.sh "$prefix" 2 "$cluster_name" "$proc_ver" "$img_size" "$low_ene" "$high_ene" 0 "$low_ene"
echo "[base_eROstep] Running prep step for TM3"
./SH_prep.sh "$prefix" 3 "$cluster_name" "$proc_ver" "$img_size" "$low_ene" "$high_ene" 0 "$low_ene"
echo "[base_eROstep] Running prep step for TM4"
./SH_prep.sh "$prefix" 4 "$cluster_name" "$proc_ver" "$img_size" "$low_ene" "$high_ene" 0 "$low_ene"
echo "[base_eROstep] Running prep step for TM5"
./SH_prep.sh "$prefix" 5 "$cluster_name" "$proc_ver" "$img_size" 0.8 "$high_ene" 0 "$low_ene"
echo "[base_eROstep] Running prep step for TM6"
./SH_prep.sh "$prefix" 6 "$cluster_name" "$proc_ver" "$img_size" "$low_ene" "$high_ene" 0 "$low_ene"
echo "[base_eROstep] Running prep step for TM7"
./SH_prep.sh "$prefix" 7 "$cluster_name" "$proc_ver" "$img_size" 0.8 "$high_ene" 0 "$low_ene"

echo "[base_eROstep] Running PIBSUB step"
./SH_PIBSUB.sh "$prefix" "$cluster_name" "$proc_ver" "$low_ene" 0.8 "$high_ene"
echo "[base_eROstep] DONE"