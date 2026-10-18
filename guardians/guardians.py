#!/usr/bin/env python3
"""Offline Guardians renderer. Python 3.10+ and Pillow; no browser required."""
import argparse, gzip, json, math, re, urllib.request
from pathlib import Path
from functools import lru_cache
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parent
RENDERER='e85cd6e7941e201a4397d3a48bc2ad17eb6d1080b9005008ed3b39b6e80358b9i0'
def read(name):
 p=ROOT/name
 return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_text())
@lru_cache(maxsize=1)
def selection_data():return read('data/selection.json.gz')

def select(code,padding):
 if not re.fullmatch(r'[A-H][A-F][A-H][A-G]',code) or code[0]!=code[2]:raise ValueError('Invalid collection trait code')
 if not 0<=padding<=2100000000000000:raise ValueError('Padding outside Bitcoin output-value range')
 data=selection_data();amount=float(padding);refs=[]
 for layer,c in enumerate(code):
  g=data[layer][ord(c)-65];n=float(len(g) if isinstance(g,list) else g['length']);r=math.fmod(amount,n)
  refs.append(g[int(r)] if isinstance(g,list) else {float(k):v for k,v in g.items() if k!='length'}[r])
  amount=float(math.floor(amount/n))
 return refs
NS='{http://www.w3.org/2000/svg}'
RECT=re.compile(r'M(\d+) (\d+)h(\d+)v(\d+)h-(\d+)z')
def body(path,fragment):
 root=ET.fromstring(gzip.decompress(path.read_bytes()));nodes={n.get('id'):n for n in root.iter() if n.get('id')}
 css=root.find(NS+'style').text;palettes={k:dict(re.findall(r'(--c\d+):(#[0-9a-fA-F]{6});',v)) for k,v in re.findall(r'\.(e\d+)\{([^}]+)\}',css)}
 out=Image.new('RGBA',(54,54));draw=ImageDraw.Draw(out)
 def paint(node,colors):
  if node.tag==NS+'use':paint(nodes[node.get('href')[1:]],palettes.get(node.get('class'),colors))
  elif node.tag==NS+'path':
   fill=node.get('fill');fill=colors[fill[4:-1]] if fill.startswith('var(') else fill
   d=node.get('d');matches=list(RECT.finditer(d))
   if ''.join(m.group() for m in matches)!=d:raise ValueError('Unsupported SVG geometry')
   for m in matches:
    x,y,w,h,back=map(int,m.groups());assert w==back;draw.rectangle((x,y,x+w-1,y+h-1),fill=fill)
  else:
   for child in node:paint(child,colors)
 paint(nodes[fragment],{});return out

def render(refs,transparent=False):
 assets=read('data/assets.json');out=Image.new('RGBA',(54,54))
 for index,ref in enumerate(refs):
  if index==0 and transparent:continue
  iid,_,fragment=ref.partition('#');path=ROOT/assets[iid]
  im=body(path,fragment) if fragment else Image.open(path).convert('RGBA')
  if im.size!=(54,54):im=im.resize((54,54),Image.Resampling.NEAREST)
  out.alpha_composite(im)
 return out

def resolve(iid,fetch=False):
 if not re.fullmatch(r'[0-9a-f]{64}i\d+',iid):raise ValueError('Invalid inscription ID')
 collection=read('data/collection.json')
 if iid in collection:return collection[iid]['code']
 if not fetch:raise ValueError('ID not in local collection manifest. Import the collection list, or use --fetch-code once (requires internet).')
 from html.parser import HTMLParser
 class Parser(HTMLParser):
  code=None
  def handle_starttag(self,tag,attrs):
   if tag=='script' and dict(attrs).get('src')=='/content/'+RENDERER:
    self.code=next((k.upper() for k,v in attrs if v in (None,'')),None)
 req=urllib.request.Request('https://ordinals.com/content/'+iid,headers={'Accept-Encoding':'identity'})
 with urllib.request.urlopen(req,timeout=30) as response:content=response.read().decode()
 p=Parser();p.feed(content)
 if not p.code:raise ValueError('Inscription does not reference the collection renderer')
 select(p.code,0);collection[iid]={'code':p.code};(ROOT/'data/collection.json').write_text(json.dumps(collection,indent=2)+'\n');return p.code

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 for cmd in ['render','inspect']:
  a=sub.add_parser(cmd);g=a.add_mutually_exclusive_group(required=True);g.add_argument('--id');g.add_argument('--code');a.add_argument('--padding',type=int,required=True);a.add_argument('--fetch-code',action='store_true')
  if cmd=='render':
   a.add_argument('--scale',type=int,default=1);a.add_argument('--size',type=int,choices=[24,54],default=54);a.add_argument('--transparent',action='store_true');a.add_argument('--output',type=Path,required=True)
 a=sub.add_parser('import-ids');a.add_argument('file',type=Path)
 args=p.parse_args()
 if args.command=='import-ids':
  # JSON array of IDs, array of {id,code}, or object mapping ID to code/record.
  x=json.loads(args.file.read_text());rows=([{'id':k,'code':v if isinstance(v,str) else v['code']} for k,v in x.items()] if isinstance(x,dict) else x)
  for row in rows:
   if isinstance(row,str):resolve(row,True)
   else:
    iid=row['id'];code=row['code'].upper();select(code,0)
    if not re.fullmatch(r'[0-9a-f]{64}i\d+',iid):raise ValueError('Invalid inscription ID')
    c=read('data/collection.json');c[iid]={'code':code};(ROOT/'data/collection.json').write_text(json.dumps(c,indent=2)+'\n')
  print('Imported',len(rows),'IDs');return
 code=args.code.upper() if args.code else resolve(args.id,args.fetch_code);refs=select(code,args.padding)
 assets=read('data/assets.json');traits=read('data/body-traits.json.gz')
 info={'id':args.id,'code':code,'padding':args.padding,'layers':[{'layer':name,'inscription_reference':ref,'file':assets[ref.split('#')[0]]} for name,ref in zip(['background','orb','body','eyes'],refs)],'body':traits[refs[2]]}
 if args.command=='render':
  if args.scale<1:raise ValueError('Scale must be a positive integer')
  im=render(refs,args.transparent)
  if args.size!=54:im=im.resize((args.size,args.size),Image.Resampling.NEAREST)
  im=im.resize((args.size*args.scale,)*2,Image.Resampling.NEAREST);args.output.parent.mkdir(parents=True,exist_ok=True);im.save(args.output);info['output']=str(args.output)
 print(json.dumps(info,indent=2))
if __name__=='__main__':
 try:main()
 except (ValueError,KeyError) as e:raise SystemExit(str(e))
