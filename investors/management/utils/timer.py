import contextlib
import time


@contextlib.contextmanager
def timer(label: str = "Block"):
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        elapsed = end - start
        print(f"{label} took {elapsed:.2f} seconds")
