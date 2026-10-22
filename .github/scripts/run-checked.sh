#!/usr/bin/env bash
# Preserve a concise failure summary in check annotations as well as the log.
set -uo pipefail
log_file=$(mktemp)
bash --noprofile --norc -eo pipefail "$1" 2>&1 | tee "$log_file"
result=${PIPESTATUS[0]}
if (( result != 0 )); then
    /usr/bin/python3 - "$log_file" <<'PY'
import sys
from pathlib import Path
message = '\n'.join(Path(sys.argv[1]).read_text(errors='replace').splitlines()[-45:])
message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
print('::error::' + message)
PY
fi
exit "$result"
