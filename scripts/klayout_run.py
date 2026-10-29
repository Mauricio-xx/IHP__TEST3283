"""Run a KLayout batch script and fail loudly: -zz swallows exceptions and exits 0."""
import traceback, sys
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
try:
    exec(compile(open(script).read(), script, "exec"), globals())
except BaseException:
    traceback.print_exc(); sys.stdout.flush(); sys.exit(1)
