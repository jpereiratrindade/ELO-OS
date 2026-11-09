#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Host test double for the supervisor protocol. This is not a Qt GUI."""
import argparse
import os
from pathlib import Path
import time

parser = argparse.ArgumentParser()
parser.add_argument('--health-file', type=Path, required=True)
parser.add_argument('--health-token', required=True)
args = parser.parse_args()
root = args.health_file.parent
starts = root / 'starts'
starts.write_text(str(int(starts.read_text()) + 1 if starts.exists() else 1))
mode = os.environ.get('ELO_FAKE_MODE', 'normal')
if mode == 'exit':
    raise SystemExit(17)
sequence = 0
while True:
    if not (root / 'freeze-counter').exists():
        sequence += 1
    stamp = int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)
    token = 'wrong-generation' if mode == 'wrong-token' else args.health_token
    state = 'ERROR_RECOVERABLE' if mode == 'diagnostic' else 'READY_LOCAL'
    record = f'ELO_HEALTH_V1 {token} {os.getpid()} {stamp} {sequence} {state} 1 {"a" * 64}\n'
    temporary = root / 'health.tmp'
    temporary.write_text(record)
    temporary.replace(args.health_file)
    time.sleep(0.02)
