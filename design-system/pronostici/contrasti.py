def s(c):
    c = c/255
    return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
def lum(h):
    h=h.lstrip('#'); r,g,b=(int(h[i:i+2],16) for i in (0,2,4))
    return 0.2126*s(r)+0.7152*s(g)+0.0722*s(b)
def cr(a,b):
    la,lb=lum(a),lum(b); hi,lo=max(la,lb),min(la,lb)
    return round((hi+0.05)/(lo+0.05),2)
def L(h):
    y=lum(h)
    return round(116*(y**(1/3))-16 if y>0.008856 else 903.3*y,1)

DARK = {
 'ground':'#0F0E0C','surface':'#1B1917','surface-2':'#282420','surface-3':'#35302A',
 'edge':'#332F29','edge-strong':'#6F6759',
 'ink':'#F4F1EA','ink-2':'#C7C1B6','ink-3':'#A39C8F',
 'segnale':'#E8B027','segnale-ink':'#0F0E0C',
 'steel':'#93B8D6','yes':'#79C08F','no':'#E88C8C','warn':'#D9B45C','track':'#403A32',
}
LIGHT = {
 'ground':'#E6E1D6','surface':'#FCFBF8','surface-2':'#D9D2C3','surface-3':'#C9C1AE',
 'edge':'#CBC3B2','edge-strong':'#847C6B',
 'ink':'#16150F','ink-2':'#4A453C','ink-3':'#5C564B',
 'segnale':'#94620A','segnale-ink':'#FCFBF8',
 'steel':'#2A5370','yes':'#2A6140','no':'#8C2C2C','warn':'#6B4E00','track':'#C2B9A5',
}

def rep(n,P):
    print('='*66); print(n)
    print('piani L*: ground %s  surface %s  surface-2 %s  surface-3 %s' % (L(P['ground']),L(P['surface']),L(P['surface-2']),L(P['surface-3'])))
    for bg in ('ground','surface','surface-2','surface-3'):
        out=[]
        for fg in ('ink','ink-2','ink-3','steel','yes','no','warn'):
            out.append('%s %s'%(fg,cr(P[fg],P[bg])))
        print(' TESTO su %-10s %s'%(bg,'  '.join(out)))
    print(' segnale-ink su segnale ....... %s'%cr(P['segnale-ink'],P['segnale']))
    print(' segnale vs ground (barra 6px)  %s'%cr(P['segnale'],P['ground']))
    print(' segnale vs surface ........... %s'%cr(P['segnale'],P['surface']))
    print(' edge vs surface (divisorio) .. %s'%cr(P['edge'],P['surface']))
    print(' edge vs ground ............... %s'%cr(P['edge'],P['ground']))
    print(' edge-strong vs surface (ctrl)  %s'%cr(P['edge-strong'],P['surface']))
    print(' edge-strong vs ground ........ %s'%cr(P['edge-strong'],P['ground']))
    print(' ink su track (riempimento) ... %s'%cr(P['ink'],P['track']))
    print(' track vs surface ............. %s'%cr(P['track'],P['surface']))
    print(' steel vs surface (banda) ..... %s'%cr(P['steel'],P['surface']))
    print(' steel vs ground .............. %s'%cr(P['steel'],P['ground']))
    print(' ink vs surface-2 (hover riga)  %s'%cr(P['ink'],P['surface-2']))
rep('SCURO (default)',DARK); rep('CHIARO',LIGHT)
