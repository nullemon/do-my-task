import re,sys
def sec(t): h,mi,s=t.split(":"); return int(h)*3600+int(mi)*60+float(s)
def words(path):
    out=[]; cur=None
    for line in open(path,encoding="utf-8"):
        m=re.match(r"(\d\d:\d\d:\d\d\.\d+) -->",line)
        if m: cur=sec(m.group(1)); continue
        if "<c>" in line and cur is not None:
            parts=re.split(r"<(\d\d:\d\d:\d\d\.\d+)>",line.strip())
            out.append((cur,re.sub(r"<[^>]+>","",parts[0]).strip()))
            for i in range(1,len(parts),2): out.append((sec(parts[i]),re.sub(r"<[^>]+>","",parts[i+1]).strip()))
    return out
if __name__=="__main__":
    w=words(sys.argv[1]); a,b=float(sys.argv[2]),float(sys.argv[3])
    print(" ".join(f"{x}@{t:.2f}" for t,x in w if a<=t<=b and x))
