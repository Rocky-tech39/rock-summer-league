# Rock Clan - 숲 VOD 자동 동기화 (Summer League + K.E.D. League)
# geicom 방송국 VOD 목록에서 리그 경기를 찾아 사이트 다시보기 링크를 자동 등록
import json, re, urllib.request, functools

DB='https://rock-summer-league-default-rtdb.asia-southeast1.firebasedatabase.app'
API='https://chapi.sooplive.co.kr/api/geicom/vods/all?page={}&per_page=60&orderby=reg_date'
PAIRS=[(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
QFDEF=[('A',1,'B',2),('C',1,'D',2),('B',1,'A',2),('D',1,'C',2)]

LEAGUES=[
 {'node':'league','name':'Summer','keywords':['써머리그','썸머리그','summer'],
  'groups':{'A':['팡','승구','인','카스'],'B':['머머리','호랑이','스트','에이쥬르'],
            'C':['순대','달선','로키','조이'],'D':['비니','루빡','아따','원']},
  'alias':{'팡':['팡','pang'],'승구':['승구'],'인':['인'],'카스':['카스'],
   '머머리':['머머리'],'호랑이':['호랑이'],'스트':['스트'],
   '에이쥬르':['에이쥬르','아주르','에이주르','아쥬르','azure'],
   '순대':['순대'],'달선':['달선'],'로키':['로키'],'조이':['조이'],
   '비니':['비니'],'루빡':['루빡'],'아따':['아따','아따보이'],'원':['원']},
  'exact':{'인','원'}},
 {'node':'ked_league','name':'KED','keywords':['k.e.d','ked','금은동','케드'],
  'groups':{'A':['베이직','스끼다시','하나','낭만'],'B':['SU인직','프렌드','로키','오마킹'],
            'C':['비니','아주르','미스트','머머리'],'D':['꼬마진','글로리','MGZG','야호']},
  'alias':{'베이직':['베이직','basic'],'스끼다시':['스끼다시','스키다시'],'하나':['하나'],'낭만':['낭만'],
   'SU인직':['su인직','인직'],'프렌드':['프렌드','friend'],'로키':['로키'],'오마킹':['오마킹'],
   '비니':['비니'],'아주르':['아주르','에이쥬르','아쥬르'],'미스트':['미스트','mist'],'머머리':['머머리'],
   '꼬마진':['꼬x마진','꼬마진'],'글로리':['글로리','glory'],'MGZG':['mgzg'],'야호':['야호']},
  'exact':set()},
]

def http(url,data=None,method='GET'):
    req=urllib.request.Request(url,data=data,method=method,
        headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/json'})
    return urllib.request.urlopen(req,timeout=30).read().decode()

def canon(token,alias,exact):
    t=re.sub(r'[^\w가-힣.]','',token).lower()
    if not t: return None
    for name,al in alias.items():
        for a in al:
            if name in exact:
                if t==a: return name
            elif t==a or (len(a)>=2 and a in t): return name
    return None

def parse_title(title,alias,exact):
    m=re.split(r'[vV][sS]',title)
    if len(m)!=2: return None
    left=m[0].strip().split(); right=m[1].strip().split()
    if not left or not right: return None
    p1=canon(left[-1],alias,exact); p2=canon(right[0],alias,exact)
    if p1 and p2 and p1!=p2: return (p1,p2)
    return None

def match_score(games):
    return sum(1 for w in games if w==0), sum(1 for w in games if w==1)
def complete(games): return all(w is not None for w in games)

def standings(groups,state,g):
    ps=[{'i':i,'name':n,'mw':0,'ml':0,'gw':0,'gl':0} for i,n in enumerate(groups[g])]
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

def ko_matches(groups,state):
    ko=state.get('KO') or {}
    def qual(g,rank):
        if not all(complete(m) for m in state[g]): return None
        return standings(groups,state,g)[rank-1]['name']
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

def sync(lg,vods):
    groups=lg['groups']
    hits=[]
    for v in vods:
        t=v['title_name']; tl=t.lower()
        if not any(k in tl for k in lg['keywords']): continue
        pr=parse_title(t,lg['alias'],lg['exact'])
        if pr: hits.append((pr,v['title_no'],t))
    if not hits:
        print(f"[{lg['name']}] 새 VOD 없음"); return
    raw=http(DB+'/'+lg['node']+'.json')
    if raw=='null':
        print(f"[{lg['name']}] 리그 데이터 없음, 건너뜀"); return
    state=json.loads(json.loads(raw))
    vod=state.get('VOD') or {}
    komap=ko_matches(groups,state)
    added=[]
    for (p1,p2),no,title in hits:
        key=None
        for g,names in groups.items():
            if p1 in names and p2 in names:
                i,j=names.index(p1),names.index(p2)
                key='%s-%d'%(g,PAIRS.index((min(i,j),max(i,j))))
                break
        if not key:
            for k2,pair in komap.items():
                if pair==frozenset((p1,p2)): key=k2; break
        if key and key not in vod:
            vod[key]='https://vod.sooplive.com/player/%d'%no
            added.append((key,p1,p2,title))
    if added:
        state['VOD']=vod
        http(DB+'/'+lg['node']+'.json',data=json.dumps(json.dumps(state,ensure_ascii=False)).encode(),method='PUT')
    print(f"[{lg['name']}] 신규 등록 {len(added)}건")
    for key,p1,p2,title in added: print(f'  {key}: {p1} vs {p2}  <- {title}')

def main():
    vods=[]
    for page in (1,2):
        d=json.loads(http(API.format(page)))
        rows=d.get('data') or []
        if not rows: break
        vods+=rows
    for lg in LEAGUES: sync(lg,vods)

if __name__=='__main__':
    main()
