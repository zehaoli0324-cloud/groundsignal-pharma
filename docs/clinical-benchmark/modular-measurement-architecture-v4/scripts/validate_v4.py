#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SVG_DIR=ROOT/'svg'; PNG_DIR=ROOT/'output'/'png'; PNG_DIR.mkdir(parents=True,exist_ok=True)
issues=[]; records=[]; files=sorted(SVG_DIR.glob('*.svg'))
if len(files)!=6: issues.append({'rule':'SVG_COUNT','expected':6,'actual':len(files)})
for p in files:
    try: root=ET.parse(p).getroot()
    except Exception as e:
        issues.append({'file':p.name,'rule':'XML_PARSE','error':str(e)}); continue
    vb=[float(x) for x in root.attrib['viewBox'].split()]; w,h=vb[2],vb[3]
    ids=[]; min_font=999.0
    for e in root.iter():
        if 'id' in e.attrib: ids.append(e.attrib['id'])
        if e.tag.endswith('text'):
            fs=float(e.attrib.get('font-size',0)); min_font=min(min_font,fs)
            x=float(e.attrib.get('x',0)); y=float(e.attrib.get('y',0))
            if not(0<=x<=w and 0<=y<=h): issues.append({'file':p.name,'rule':'TEXT_OOB','xy':[x,y]})
        if e.tag.endswith('rect'):
            x=float(e.attrib.get('x',0)); y=float(e.attrib.get('y',0)); rw=float(e.attrib.get('width',0)); rh=float(e.attrib.get('height',0))
            if x<0 or y<0 or x+rw>w or y+rh>h: issues.append({'file':p.name,'rule':'RECT_OOB','rect':[x,y,rw,rh]})
    dup=sorted(k for k,v in Counter(ids).items() if v>1)
    if dup: issues.append({'file':p.name,'rule':'DUPLICATE_IDS','ids':dup})
    if min_font<15: issues.append({'file':p.name,'rule':'FONT_TOO_SMALL','min_font':min_font})
    png=PNG_DIR/(p.stem+'.png'); cairosvg.svg2png(url=str(p),write_to=str(png),output_width=1800)
    with Image.open(png) as im:
        if im.getbbox() is None: issues.append({'file':p.name,'rule':'BLANK_RENDER'})
        size=im.size
    records.append({'file':p.name,'min_font':min_font,'png_size':size})
result={'status':'PASS' if not issues else 'FAIL','svg_count':len(files),'issues':issues,'records':records}
print(json.dumps(result,ensure_ascii=False,indent=2)); raise SystemExit(0 if not issues else 1)
