#!/usr/bin/env bash
# Pull E0-E3 results from server0/server1 to this PC, salvage per-controller results
# from the run logs (so even unfinished jobs' completed work is saved), and print
# status. Idempotent + re-runnable -- run it anytime (e.g. tomorrow) from Git Bash:
#     bash own-article/remote_sync.sh
set -u
LOCAL="/c/Users/zergu/repos/greenhouse-control/own-article/results_scenarios"
RR="greenhouse-control/own-article/results_scenarios"
# -4: force IPv4 (server0's IPv6 link-local is firewalled and breaks the default attempt)
SSH="ssh -4 -o BatchMode=yes -o ConnectTimeout=10"
SCP="scp -4 -q -o BatchMode=yes"
mkdir -p "$LOCAL/tables" "$LOCAL/figures" "$LOCAL/remote_logs"

echo "################ REMOTE STATUS  $(date '+%Y-%m-%d %H:%M') ################"
for H in server0 server1; do
  echo "===== $H ====="
  $SSH "$H" "
    echo \"  jobs_running = \$(pgrep -fc 'run_e3_seeds|run_all_notebooks' 2>/dev/null)\"
    echo \"  e3 partial CSVs = \$(ls $RR/tables/e3_seeded_*.csv 2>/dev/null | wc -l)\"
    echo \"  recipe_frozen = \$(test -f $RR/recipe_frozen.json && echo yes || echo no) | e2_ladder = \$(test -f $RR/tables/e2_ladder.csv && echo yes || echo no)\"
  " 2>&1 | grep -viE 'onnx|opcua|warn'
  # fetch logs + any written partials
  $SCP "$H:~/e3logs/*.log"            "$LOCAL/remote_logs/"  2>/dev/null
  $SCP "$H:$RR/tables/e3_seeded_*.csv" "$LOCAL/tables/"       2>/dev/null
done

# E0-E2 artifacts (server0 is authoritative for those)
$SCP "server0:$RR/tables/e0_*.csv" "server0:$RR/tables/e1_*.csv" "server0:$RR/tables/e2_*.csv" "$LOCAL/tables/" 2>/dev/null
$SCP "server0:$RR/recipe_frozen.json" "server0:$RR/protocol.json" "$LOCAL/" 2>/dev/null
$SCP "server0:$RR/figures/*.png" "$LOCAL/figures/" 2>/dev/null

# Salvage completed (controller,seed) results from the logs -> CSV. This captures
# results that finished but whose job has not yet written its e3_seeded_*.csv.
SALV="$LOCAL/tables/e3_salvage_from_logs.csv"
echo "method,seed,epi,viol,secs" > "$SALV"
grep -hoE 'seed [0-9]+ [a-z_]+ EPI=[-0-9.eEnan]+ viol=[0-9-]+ \([0-9.]+s\)' "$LOCAL"/remote_logs/*.log 2>/dev/null \
  | sed -E 's/seed ([0-9]+) ([a-z_]+) EPI=([-0-9.eEnan]+) viol=([0-9-]+) \(([0-9.]+)s\)/\2,\1,\3,\4,\5/' \
  | sort -t, -k1,1 -k2,2n -u >> "$SALV"

echo "################ SALVAGED (method,seed,epi,viol,secs) ################"
column -s, -t "$SALV" 2>/dev/null || cat "$SALV"
n_salv=$(($(wc -l < "$SALV") - 1))
n_part=$(ls "$LOCAL"/tables/e3_seeded_*.csv 2>/dev/null | wc -l)
echo "################ DONE ################"
echo "  saved to: $LOCAL"
echo "  completed (controller,seed) combos in logs: $n_salv"
echo "  full e3_seeded_*.csv partials pulled: $n_part  (need 18 = 10 cheap + 8 long for full merge)"
echo "  when 18 partials are present, run:  <venv-python> own-article/merge_e3.py"
