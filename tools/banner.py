"""Kanal banner seçenekleri (2560x1440, telefonda görünen alan ortadaki 1546x423). Seçilen: A → assets/kanal/banner.png"""
import random, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
R="/home/claude/youtube-bot/assets/"
W,H=2560,1440; PAPER=(236,226,206); RED=(183,31,46); DARK=(32,28,26); CREAM=(248,243,232)
F=lambda s: ImageFont.truetype(R+"fonts/ArchivoBlack-Regular.ttf", s)
def paper(seed=1):
    random.seed(seed)
    b=Image.new("RGB",(W,H),PAPER)
    n=Image.effect_noise((W//2,H//2),28).resize((W,H)).convert("RGB")
    b=Image.blend(b,ImageChops.multiply(b,n.point(lambda p:180+p//4)),0.6)
    f=Image.effect_noise((W//6,H//6),60).resize((W,H),Image.BICUBIC).filter(ImageFilter.GaussianBlur(2)).convert("RGB")
    return Image.blend(b,ImageChops.multiply(b,f.point(lambda p:200+p//5)),0.5)
def torn(w,h,seed,amp=10,step=14):
    r=random.Random(seed)
    pts=[(x,r.uniform(0,amp)) for x in range(0,w+1,step)]+[(w-r.uniform(0,amp),y) for y in range(0,h+1,step)]
    pts+=[(x,h-r.uniform(0,amp)) for x in range(w,-1,-step)]+[(r.uniform(0,amp),y) for y in range(h,-1,-step)]
    m=Image.new("L",(w,h),0); ImageDraw.Draw(m).polygon(pts,fill=255); return m
def stick(bg,card,x,y,seed,ang):
    m=torn(*card.size,seed,amp=9)
    card=card.rotate(ang,expand=True,resample=Image.BICUBIC); m=m.rotate(ang,expand=True,resample=Image.BICUBIC)
    sh=Image.new("L",bg.size,0); sh.paste(m,(x+10,y+14)); sh=sh.filter(ImageFilter.GaussianBlur(14)).point(lambda p:int(p*.5))
    bg.paste(Image.composite(Image.new("RGB",bg.size,(90,70,55)),bg,sh)); bg.paste(card,(x,y),m); return card.size
def tape(bg,x,y,ang,seed,w=200,h=52):
    t=Image.new("RGBA",(w,h),RED+(215,)); t.putalpha(ImageChops.multiply(t.split()[3],torn(w,h,seed,6,10)))
    t=t.rotate(ang,expand=True,resample=Image.BICUBIC); bg.paste(t,(x,y),t)
def label(text,size,fg,bgc,padx=34,pady=18):
    f=F(size); b=f.getbbox(text); w,h=b[2]-b[0]+2*padx,b[3]-b[1]+2*pady
    c=Image.new("RGB",(w,h),bgc); ImageDraw.Draw(c).text((padx-b[0],pady-b[1]),text,font=f,fill=fg); return c
def logo(s): return Image.open(R+"filigran.png").convert("RGBA").resize((s,s),Image.LANCZOS)
SERI=["VURGUN DOSYALARI","ÇÖZÜLEMEYEN GİZEMLER","İNSAN VÜCUDU VE BEYİN"]

SX,SY,SW,SH=(W-1546)//2,(H-423)//2,1546,423
def v_A():
    bg=paper(1)
    lg=logo(210); bg.paste(lg,(SX+40,SY+40),lg)
    title=label("KIRMIZI KRAVAT",104,CREAM,RED,40,22)
    tx=SX+290; stick(bg,title,tx,SY+38,7,-1.2)
    tape(bg,tx+title.width-120,SY+5,-30,3,170,46)
    sub=label("Tarihin, bilimin ve insanın bilinmeyen dosyaları",38,DARK,CREAM,26,12)
    stick(bg,sub,tx+20,SY+205,11,0.8)
    d=ImageDraw.Draw(bg); f=F(23); txt="   •   ".join(SERI)+"   •   HER GÜN 19:00"
    tw=d.textlength(txt,font=f); d.text((SX+(SW-tw)/2,SY+335),txt,font=f,fill=RED)
    return bg
def v_B():
    bg=paper(2); y0=SY+55
    lg=logo(190); bg.paste(lg,(SX+40,y0+40),lg)
    t1=label("KIRMIZI",100,DARK,CREAM,28,12); t2=label("KRAVAT",100,CREAM,RED,28,12)
    stick(bg,t1,SX+260,y0,21,-2); stick(bg,t2,SX+280,y0+125,22,1.5)
    tape(bg,SX+260+t1.width-30,y0-40,-35,5,150,42)
    for i,s in enumerate(SERI):
        c=label(s,32,CREAM if i==0 else DARK,RED if i==0 else CREAM,24,12)
        stick(bg,c,SX+900+(i%2)*30,y0+5+i*80,30+i,[-2,1.5,-1][i])
    d=ImageDraw.Draw(bg); d.text((SX+910,y0+255),"HER GÜN 19:00'DA YENİ DOSYA",font=F(28),fill=RED)
    return bg
def v_C():
    bg=Image.new("RGB",(W,H),(28,24,22)); n=Image.effect_noise((W//2,H//2),20).resize((W,H)).convert("RGB")
    bg=Image.blend(bg,ImageChops.multiply(bg,n.point(lambda p:200+p//5)),0.5)
    sw=1480; strip=paper(3).crop((0,0,sw,320)); x=(W-sw)//2; y=SY+50
    stick(bg,strip,x,y,40,-1)
    lg=logo(210); bg.paste(lg,(x+70,y+50),lg)
    d=ImageDraw.Draw(bg); d.text((x+320,y+70),"KIRMIZI KRAVAT",font=F(112),fill=RED)
    d.text((x+330,y+215),"Bilinmeyen hikâyelerin dosyası  •  Her gün 19:00",font=F(36),fill=DARK)
    tape(bg,x-70,y-30,-35,8); tape(bg,x+sw-150,y+250,-35,9)
    return bg
def guide(im):
    g=im.copy(); d=ImageDraw.Draw(g)
    d.rectangle(((W-1546)//2,(H-423)//2,(W+1546)//2,(H+423)//2),outline=(0,160,255),width=6)
    d.rectangle(((W-2560)//2,(H-423)//2,(W+2560)//2,(H+423)//2),outline=(0,200,90),width=4)
    return g
for n,fn in [("A",v_A),("B",v_B),("C",v_C)]:
    im=fn(); im.save(f"banner_{n}.png",optimize=True)
    guide(im).resize((1280,720)).save(f"onizleme_{n}.jpg",quality=88)
    # telefonda görünen alan
    im.crop(((W-1546)//2,(H-423)//2,(W+1546)//2,(H+423)//2)).save(f"telefon_{n}.jpg",quality=88)
