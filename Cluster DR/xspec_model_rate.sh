#!/usr/bin/env bash
set -euo pipefail

# Source XSPEC environment
source /home/asrivast/eRASS1/Scripts/init.sh

usage() {
  cat <<'USAGE'
Usage:
  xspec_model_rate.sh <clustername> <nH> <kT> <abund> <z> <norm> [exposure] [fake_prefix] [fake_name]

Arguments:
  clustername Cluster folder name under /home/asrivast/eRASS1
  nH          TBabs nH (10^22 cm^-2)
  kT          APEC kT (keV)
  abund       APEC abundance
  z           APEC redshift
  norm        APEC norm

Optional:
  exposure    Exposure time (default: 1.0)
  fake_prefix Fake file prefix (default: faketest)
  fake_name   Fake spectrum file name (default: T1.fak)
USAGE
}

if [[ $# -lt 6 ]]; then
  usage
  exit 1
fi

clustername="$1"
nh="$2"
kt="$3"
abund="$4"
redshift="$5"
norm="$6"
exposure="${7:-1.0}"
fake_prefix="${8:-faketest}"
fake_name="${9:-T1.fak}"

rsp="/home/asrivast/eRASS1/RSP/rsp.fits"

if [[ ! -f "$rsp" ]]; then
  echo "ERROR: RSP not found: $rsp" >&2
  exit 1
fi

log_dir="/home/asrivast/eRASS1/${clustername}/filtered/SB"
mkdir -p "$log_dir"
log_file="${log_dir}/xspec_model_rate_${fake_prefix}.log"
out_file="${log_dir}/xspec_model_rate_${fake_prefix}.txt"
fake_path="${log_dir}/${fake_name}"

# Avoid interactive overwrite prompt.
rm -f "$fake_path"

xspec <<EOF | tee "$log_file" > /dev/null
query yes
abund aspl
model TBabs*apec
$nh
$kt
$abund
$redshift
$norm
fakeit none
$rsp

y
$fake_prefix
$fake_path
$exposure,1.0,1.0
show rate
exit
EOF

rate_line="$(grep -m1 "Model predicted rate" "$log_file" || true)"
if [[ -z "$rate_line" ]]; then
  echo "ERROR: Could not find model predicted rate in XSPEC output." >&2
  echo "Log saved at: $log_file" >&2
  exit 1
fi

rate_value="$(echo "$rate_line" | awk '{print $4}')"
if [[ -z "$rate_value" ]]; then
  echo "ERROR: Failed to parse model predicted rate." >&2
  echo "Line: $rate_line" >&2
  exit 1
fi

echo "$rate_value" > "$out_file"

echo "Saved model predicted rate to: $out_file"
echo "Saved XSPEC log to: $log_file"
