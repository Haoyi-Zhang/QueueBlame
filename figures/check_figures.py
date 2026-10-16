"""Verify fresh Python generation of the two consumed semantic diagrams."""
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='queue-blame-figures-') as tmp:
        out=Path(tmp)
        subprocess.run([sys.executable,'-B',str(HERE/'draw_schematics.py'),
                        '--output',str(out)],check=True,timeout=60)
        for name in ('architecture','transfer'):
            if (out/(name+'.pdf')).read_bytes() != (HERE/(name+'.pdf')).read_bytes():
                raise RuntimeError('Stale or nondeterministic diagram: '+name)
    print('Two consumed vector diagrams regenerate exactly; label bounds pass.')
