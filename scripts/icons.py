#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
src=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
items=[]
for idiom, scales, sizes in [('iphone',['2x','3x'],['20','29','40','60']),('ipad',['1x','2x'],['20','29','40','76']),('ipad',['2x'],['83.5']),('ios-marketing',['1x'],['1024'])]:
  for size in sizes:
    for scale in scales:
      px=round(float(size)*int(scale[0])); name=f'icon-{idiom}-{size}@{scale}.png'
      subprocess.run(['sips','-s','format','png','-z',str(px),str(px),str(src),'--out',str(out/name)],check=True,stdout=subprocess.DEVNULL)
      items.append({'idiom':idiom,'size':f'{size}x{size}','scale':scale,'filename':name})
(out/'Contents.json').write_text(json.dumps({'images':items,'info':{'author':'xcode','version':1}},indent=2))
