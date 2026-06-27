#!/usr/bin/env python3
import os, time
paths = [
    'trackit_dev.db',
    os.path.join('app','trackit_dev.db'),
]
for p in paths:
    ap = os.path.abspath(p)
    if os.path.exists(ap):
        print(p, '->', ap, 'mtime:', time.ctime(os.path.getmtime(ap)))
    else:
        print(p, '->', ap, 'MISSING')
