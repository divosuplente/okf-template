#!/usr/bin/env bash
# Check upstream OKF spec repo for recent changes to the okf/ directory.
# Usage: bash tools/check-okf-upstream.sh
set -euo pipefail

curl -sL "https://api.github.com/repos/GoogleCloudPlatform/knowledge-catalog/commits?path=okf&per_page=5" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, dict) and 'message' in data:
    print(data.get('message', 'Unknown') + ' (rate limited or requires auth)')
    sys.exit(1)
for c in data:
    date = c['commit']['author']['date'][:10]
    msg = c['commit']['message'].split('\n')[0]
    sha = c['sha'][:7]
    print(f'{date} {sha} {msg}')
"
