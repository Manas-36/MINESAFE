import sys, time, pods
def vol(a,b):
    try: return a.intersect(b).val().Volume()
    except Exception: return 0.0
for n in (sys.argv[1:] or pods.POD_FUNCS):
    t=time.time(); P,C=pods.POD_FUNCS[n]()
    bad=[]
    for cn,c in C.items():
        for pn,p in P.items():
            v=vol(c,p)
            if v>0.5: bad.append(f"{cn} x {pn}: {v:.1f}")
    keys=list(C)
    for i,a in enumerate(keys):
        for b in keys[i+1:]:
            if a.split('_')[0]==b.split('_')[0] and ('pcb' in a+b or 'parts' in a+b or 'modules' in a+b or 'xiao' in a+b): continue
            v=vol(C[a],C[b])
            if v>0.5: bad.append(f"{a} x {b}: {v:.1f}")
    bb=P[list(P)[0]].union(P[list(P)[1]]).val().BoundingBox()
    print(n, f"{bb.xlen:.0f}x{bb.ylen:.0f}x{bb.zlen:.0f}", "OK" if not bad else bad, f"{time.time()-t:.0f}s")
