#!/usr/bin/env bash
# Pull the CLEAN confirmatory E3 (tags p1c_* from server0, p1rl_* from server1) and merge.
# Archives stale local (non-p1) e3_seeded partials first so merge_e3 stays uncontaminated.
# Re-runnable anytime (jobs run detached on the servers): bash own-article/sync_clean_e3.sh
set -u
LOCAL="/c/Users/zergu/repos/greenhouse-control/own-article/results_scenarios"
RRt="greenhouse-control/own-article/results_scenarios/tables"
SSH="ssh -4 -o BatchMode=yes -o ConnectTimeout=10"
SCP="scp -4 -q -o BatchMode=yes"
T="$LOCAL/tables"
mkdir -p "$T/pre_p1_archive"

# 1) move any stale local partials out of the merge set (keep only fresh p1c_*/p1rl_*)
for f in "$T"/e3_seeded_*.csv; do
  [ -e "$f" ] || continue
  b=$(basename "$f")
  case "$b" in
    e3_seeded_p1c_*|e3_seeded_p1rl_*) : ;;
    *) mv "$f" "$T/pre_p1_archive/" 2>/dev/null ;;
  esac
done

# 2) status + pull the p1 partials from both servers
echo "############ CLEAN E3 STATUS  $(date '+%F %H:%M') ############"
for H in server0 server1; do
  $SSH "$H" 'echo "  procs_running=$(pgrep -fc "[r]un_e3_seeds")  p1_partials=$(ls '"$RRt"'/e3_seeded_p1*.csv 2>/dev/null | wc -l)/10"' 2>&1 | grep -viE 'onnx|opcua|warn'
  $SCP "$H:$RRt/e3_seeded_p1*.csv" "$T/" 2>/dev/null
done
echo "pulled p1 partials locally: $(ls "$T"/e3_seeded_p1*.csv 2>/dev/null | wc -l)/20 (10 cheap+oracle + 10 RL)"

# 3) merge (globs e3_seeded_*.csv -> now only the p1 set) + show the confirmatory table
PY="C:/Users/zergu/repos/greenlight/sindylom/.venv/Scripts/python.exe"
if [ -x "$PY" ]; then "$PY" /c/Users/zergu/repos/greenhouse-control/own-article/merge_e3.py; else echo "(run merge_e3.py manually)"; fi
