#!/usr/bin/env python3
import os, subprocess
result = subprocess.run(["ls", "-la", "specs/sample_spec/"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
