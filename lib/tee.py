import sys
log=open(sys.argv[1],"a",encoding="utf-8")
for line in sys.stdin:
    sys.stdout.write(line); sys.stdout.flush(); log.write(line); log.flush()
