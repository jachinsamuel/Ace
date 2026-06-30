import time
t0 = time.perf_counter()
import ace.cli
t1 = time.perf_counter()
print(f"Total time to import ace.cli: {(t1 - t0)*1000:.2f} ms")
