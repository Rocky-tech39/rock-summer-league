# Rock Clan Summer League - 숲 VOD 자동 동기화
# geicom 방송국 VOD 목록에서 '써머리그' 경기를 찾아 사이트 다시보기 링크를 자동 등록
import json, re, urllib.request, functools

DB='https://rock-summer-league-default-rtdb.asia-southeast1.firebasedatabase.app'
API='https://chapi.sooplive.co.kr/api/geicom/vods/all?page={}&per_page=60&orderby=reg_date'

GROUPS={'A':['팡','승구','인','카스'],'B':['머머리','호랑이','스트','에이쥬르'],
        'C':['순대','달선','로키','조이'],'D':['비니','루빡','아따','원']}
PAIRS=[(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
QFDEF=[('A',1,'B',2),('C',1,'D',2),('B',1,'A',2),('D',1,'C',2)]
ALIAS={'팡':['팡','pang'],'승구':['승구'],'인':['인'],'카스':['카스'],
 '머머리':['머머리'],'호랑이':['호랑이'],'스트':['스트'],
 '에이쥬르':['에이쥬르','아주르','에이주르','아쥬르','azure'],
 '순대':['순대'],'달선':['달선'],'로키':['로키'],'조이':['조이'],
 '비니':['비니'],'루빡':['루빡'],'아따':['아따','아따보이'],'원':['원']}
EXACT_ONLY={'인','원'}  # 한 글자 이름은 정확히 일치할 때만

def http(url,data=None,method='GET'):
    req=urllib.request.Request(url,data=data,method=method,
        headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/json'})
    return urllib.request.urlopen(req,timeout=30).read().decode()

def canon(token):
    t=re.sub(r'[^\w가-힣]','',token).lower()
    if not t: return None
    for name,aliases in ALIAS.items():
        for a in aliases:
            if name in EXACT_ONLY:
                if t==a: return name
            elif t==a or (len(a)>=2 and a in t): return name
    return None

def parse_title(title):
    m=re.split(r'[vV][sS]',title)
    if len(m)!=2: return None
    left=m[0].strip().split(); right=m[1].strip().split()
    if not left or not right: return None
    p1=canon(left[-1]); p2=canon(right[0])
    if p1 and p2 and p1!=p2: return (p1,p2)
    return None

def match_score(games):
    a=sum(1 for w in games if w==0); b=sum(1 for w in games if w==1)
    return a,b
def complete(games): return all(w is not None for w in games)

def standings(state,g):
    ps=[{'i':i,'name':n,'mw':0,'ml':0,'gw':0,'gl':0} for i,n in enumerate(GROUPS[g])]
    for mi,games in enumerate(state[g]):
        i0,i1=PAIRS[mi]; a,b=match_score(games)
        ps[i0]['gw']+=a; ps[i0]['gl']+=b; ps[i1]['gw']+=b; ps[i1]['gl']+=a
        if complete(games):
            if a>b: ps[i0]['mw']+=1; ps[i1]['ml']+=1
            elif b>a: ps[i1]['mw']+=1; ps[i0]['ml']+=1
    for p in ps: p['diff']=p['gw']-p['gl']
    def h2h(x,y):
        for mi,(a0,a1) in enumerate(PAIRS):
            if {a0,a1}=={x['i'],y['i']}:
                games=state[g][mi]
                if not complete(games): return 0
                a,b=match_score(games)
                w=a0 if a>b else a1
                return -1 if w==x['i'] else 1
        return 0
    def cmp(x,y):
        if x['mw']!=y['mw']: return y['mw']-x['mw']
        if x['ml']!=y['ml']: return x['ml']-y['ml']
        if x['diff']!=y['diff']: return y['diff']-x['diff']
        return h2h(x,y)
    return sorted(ps,key=functools.cmp_to_key(cmp))

def ko_matches(state):
    ko=state.get('KO') or {}
    def qual(g,rank):
        if not all(complete(m) for m in state[g]): return None
        return standings(state,g)[rank-1]['name']
    def val(stored,pair):
        if not stored or not pair[0] or not pair[1]: return None
        return stored if stored in pair else None
    qfP=[(qual(a,b),qual(c,d)) for a,b,c,d in QFDEF]
    qfW=[val((ko.get('qf') or [None]*4)[i],qfP[i]) for i in range(4)]
    sfP=[(qfW[0],qfW[1]),(qfW[2],qfW[3])]
    sfW=[val((ko.get('sf') or [None,None])[i],sfP[i]) for i in range(2)]
    sfL=[(None if not sfW[i] or not sfP[i][0] or not sfP[i][1]
          else (sfP[i][1] if sfP[i][0]==sfW[i] else sfP[i][0])) for i in range(2)]
    out={}
    for i,p in enumerate(qfP):
        if p[0] and p[1]: out['ko-qf-%d'%i]=frozenset(p)
    for i,p in enumerate(sfP):
        if p[0] and p[1]: out['ko-sf-%d'%i]=frozenset(p)
    if sfW[0] and sfW[1]: out['ko-f-0']=frozenset((sfW[0],sfW[1]))
    if sfL[0] and sfL[1]: out['ko-third-0']=frozenset((sfL[0],sfL[1]))
    return out

def main():
    vods=[]
    for page in (1,2):
        d=json.loads(http(API.format(page)))
        rows=d.get('data') or []
        if not rows: break
        vods+=rows
    league_vods=[]
    for v in vods:
        t=v['title_name']
        if '써머리그' not in t and '썸머리그' not in t: continue
        pr=parse_title(t)
        if pr: league_vods.append((pr,v['title_no'],t))
    state=json.loads(json.loads(http(DB+'/league.json')))
    vod=state.get('VOD') or {}
    komap=ko_matches(state)
    added=[]
    for (p1,p2),no,title in league_vods:
        key=None
        for g,names in GROUPS.items():
            if p1 in names and p2 in names:
                i,j=names.index(p1),names.index(p2)
                key='%s-%d'%(g,PAIRS.index((min(i,j),max(i,j))))
                break
        if not key:
            for k,pair in komap.items():
                if pair==frozenset((p1,p2)): key=k; break
        if key and key not in vod:
            vod[key]='https://vod.sooplive.com/player/%d'%no
            added.append((key,p1,p2,title))
    if added:
        state['VOD']=vod
        http(DB+'/league.json',data=json.dumps(json.dumps(state,ensure_ascii=False)).encode(),method='PUT')
    print('신규 등록 %d건'%len(added))
    for key,p1,p2,title in added: print(f'  {key}: {p1} vs {p2}  ← {title}')
    if not added: print('추가할 새 VOD 없음')

if __name__=='__main__':
    main()
