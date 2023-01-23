import sys
from io import StringIO
import contextlib


@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


code = """
i = [0,1,2]
for j in i :
    print(j)
"""

with stdoutIO() as s:
    exec(code)
print(s.getvalue())
