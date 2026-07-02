#!/usr/bin/env bash
# Pull oracle horizon-probe results + logs from server0/server1, print status, merge.
# The probe jobs run DETACHED (nohup) on the servers and write to server disk, so this
# is re-runnable anytime -- even after Claude Code exits. From Git Bash:
#     bash own-article/sync_oracle_probe.sh
set -u
LOCAL="/c/Users/zergu/repos/greenhouse-control/own-article/results_scenarios"
RRt="greenhouse-control/own-article/results_scenarios/tables"
SSH="ssh -4 -o BatchMode=yes -o ConnectTimeout=10"
SCP="scp -4 -q -o BatchMode=yes"
mkdir -p "$LOCAL/tables" "$LOCAL/figures" "$LOCAL/remote_logs"

echo "############ ORACLE PROBE STATUS  $(date '+%F %H:%M') ############"
for H in server0 server1; do
  echo "===== $H ====="
  $SSH "$H" '
    echo "  procs_running=$(pgrep -fc "[r]un_oracle_horizon_probe")"
    cd greenhouse-control/own-article/results_scenarios/tables 2>/dev/null || exit 0
    for f in oracle_horizon_probe_s*.csv; do
      [ -e "$f" ] && echo "  $f: $(grep -c oracle_mpc "$f") oracle row(s)"
    done' 2>&1 | grep -viE 'onnx|opcua|warn'
  $SCP "$H:$RRt/oracle_horizon_probe_s*.csv" "$LOCAL/tables/" 2>/dev/null
  $SCP "$H:~/oraclelogs/*.log"               "$LOCAL/remote_logs/" 2>/dev/null
done

echo "############ pulled to $LOCAL/tables ############"
ls "$LOCAL"/tables/oracle_horizon_probe_s*.csv 2>/dev/null
PY="C:/Users/zergu/repos/greenlight/sindylom/.venv/Scripts/python.exe"
if [ -x "$PY" ]; then
  "$PY" /c/Users/zergu/repos/greenhouse-control/own-article/merge_oracle_probe.py
else
  echo "(venv python not found; run merge_oracle_probe.py manually)"
fi
