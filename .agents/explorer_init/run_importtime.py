import subprocess
import sys
import re

def run_and_parse():
    # Run the importtime check
    cmd = [sys.executable, "-X", "importtime", "-c", "import ace.cli"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    
    # importtime output goes to stderr
    output = res.stderr
    
    lines = output.splitlines()
    parsed_lines = []
    
    # Example line:
    # import time: self [us] | cumulative [us] | imported_name
    # import time:       253 |        253 |   _frozen_importlib_external
    pattern = re.compile(r"import time:\s+(\d+)\s+\|\s+(\d+)\s+\|\s+(.+)")
    
    for line in lines:
        match = pattern.match(line)
        if match:
            self_time = int(match.group(1)) / 1000.0  # ms
            cum_time = int(match.group(2)) / 1000.0   # ms
            name = match.group(3)
            parsed_lines.append((self_time, cum_time, name))
            
    # Sort by self time
    sorted_by_self = sorted(parsed_lines, key=lambda x: x[0], reverse=True)
    print("Top 20 slowest imports by self time (ms):")
    for self_time, cum_time, name in sorted_by_self[:20]:
        print(f"  {name:<40} : self={self_time:7.2f} ms, cumulative={cum_time:7.2f} ms")
        
    print("\nTop 20 slowest imports by cumulative time (ms):")
    sorted_by_cum = sorted(parsed_lines, key=lambda x: x[1], reverse=True)
    for self_time, cum_time, name in sorted_by_cum[:20]:
        print(f"  {name:<40} : self={self_time:7.2f} ms, cumulative={cum_time:7.2f} ms")

if __name__ == "__main__":
    run_and_parse()
