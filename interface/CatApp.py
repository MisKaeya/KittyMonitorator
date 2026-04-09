#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║  🐾  Cat Monitorator v3.0  ✿  nyaa~         ║
║  Sistema Distribuído de Monitoramento Felino ║
╚══════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math, os, random, threading, shutil
import socket, json, time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 2005
CATS_FILE   = os.path.join(os.path.dirname(__file__), "cats.json")
PHOTOS_DIR  = os.path.join(os.path.dirname(__file__), "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

def load_cats():
    if not os.path.exists(CATS_FILE):
        return {}
    try:
        with open(CATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cats(data):
    try:
        with open(CATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar cats.json: {e}")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ═══════════════════════════════════════════════
#  PALETA
# ═══════════════════════════════════════════════
BG        = "#FFF0F5"
PINK      = "#FFB7C5"
MINT      = "#B5EAD7"
PEACH     = "#FFDAC1"
LAVENDER  = "#C7CEEA"
YELLOW    = "#FFFACD"
CREAM     = "#FFF9F0"
TEXT      = "#5C4A6E"
DPINK     = "#FF8FAB"
DMINT     = "#6DC49A"
BORDER    = "#DDA0DD"
GOLD      = "#FFD700"
WHITE     = "#FFFFFF"
DGRAY     = "#909090"
LGRAY     = "#D0D0D0"
MGRAY     = "#B0B0B0"
SOFT_BLUE = "#AED6F1"
RED_BLOCK = "#FF6B6B"
RED_DARK  = "#CC3333"

FT = ("Courier", 22, "bold")
FM = ("Courier", 13, "bold")
FB = ("Courier", 11)
FS = ("Courier", 9)

cat_data: dict = {}

# ═══════════════════════════════════════════════
#  PELAGENS
# ═══════════════════════════════════════════════
FUR = {
    "cinza":    ("#BDBDBD", "#888888", "#E0E0E0"),
    "laranja":  ("#FFAA55", "#CC7722", "#FFCC88"),
    "preto":    ("#333333", "#111111", "#555555"),
    "branco":   ("#F0F0F0", "#CACACA", "#FFFFFF"),
    "creme":    ("#FFE4B5", "#D4A96A", "#FFF3D0"),
    "rajado":   ("#474645", "#A8A6A4", "#655F59"),
    "siamês":   ("#F5DEB3", "#8B5E3C", "#FAF0E0"),
    "mesclado": ("#AABBCC", "#7788AA", "#CDDAEC"),
}
FUR_OPTIONS = list(FUR.keys())

def get_fur(pelagem):
    p = pelagem.lower().strip()
    for k in FUR:
        if k in p:
            return FUR[k]
    return list(FUR.values())[abs(hash(pelagem)) % len(FUR)]

# ═══════════════════════════════════════════════
#  SPRITES PIXEL ART
# ═══════════════════════════════════════════════
SPR_SENTADO = [
    "    DD  DD    ",
    "   DPPDPPD    ",
    "  DBBBBBBBD   ",
    "  DBBBBBBBD   ",
    "  DBW GG WBD  ",
    "  DBW KK WBD  ",
    "  DBB PP BBD  ",
    "  DBBBBBBBD   ",
    " DBBLLLLBBD   ",
    " DBBBBBBBBD   ",
    "  DBBB BBBD   ",
    "  DBD   DBD   ",
    "   B     B    ",
]
SPR_DORMINDO = [
    "              ",
    "  DD          ",
    " DPPD         ",
    "DBBBBD        ",
    "DB--BBD       ",
    "DBBBBBD       ",
    "DBBLLBD       ",
    "DBBBBBBBBD    ",
    "DBBBBBBBBD    ",
    " DBBBBBBD     ",
    "  DBBBD       ",
    "   DBD        ",
    "    B         ",
]

def _render_sprite(c, sx, sy, sprite, fur_key, px=5, tag="spr"):
    fur  = FUR.get(fur_key, FUR["cinza"])
    body, dark, light = fur
    cmap = {
        'B': body, 'D': dark, 'L': light,
        'P': "#FF9EB5", 'W': WHITE,
        'G': "#44BB88", 'K': "#1A1A1A",
        'T': "#FF4477", '-': dark, '~': dark,
    }
    for r, row in enumerate(sprite):
        for col, ch in enumerate(row):
            if ch == ' ':
                continue
            x1, y1 = sx + col * px, sy + r * px
            c.create_rectangle(x1, y1, x1+px, y1+px,
                                fill=cmap.get(ch, "#FF00FF"), outline='', tags=tag)

# ═══════════════════════════════════════════════
#  MASCOTE
# ═══════════════════════════════════════════════
class MascotCat:
    SIZE = 110
    def __init__(self, root, host):
        self.root   = root
        self.frame_n = 0
        self.idle   = 0
        self.mode   = "follow"
        self.mx = 400
        self.my = 300
        self.fur    = "cinza"
        self._job   = None
        self.cv = tk.Canvas(host, width=self.SIZE, height=self.SIZE,
                            bg=BG, highlightthickness=0, cursor="none")
        self.cv.place(relx=1.0, rely=1.0, anchor="se", x=-12, y=-12)
        host.bind("<Motion>", self._motion, add="+")
        self._tick()

    def _motion(self, e):
        self.mx = e.x_root; self.my = e.y_root
        self.idle = 0
        if self.mode != "follow":
            self.mode = "follow"

    def _tick(self):
        self.frame_n += 1; self.idle += 1
        if self.idle > 220:
            self.mode = random.choice(["lick","sleep"])
            self.idle = 0
        self._draw()
        try:
            self._job = self.root.after(50, self._tick)
        except Exception:
            pass

    def _draw(self):
        c = self.cv; c.delete("all")
        c.create_rectangle(0,0,self.SIZE,self.SIZE,fill=BG,outline='')
        {"sleep": self._sleep, "lick": self._lick, "follow": self._follow}[self.mode]()

    def _sleep(self):
        c, f = self.cv, self.frame_n
        fur = FUR.get(self.fur, FUR["cinza"]); body, dark, light = fur
        c.create_oval(8,50,72,90,fill=body,outline=dark,width=2)
        c.create_oval(30,30,78,68,fill=body,outline=dark,width=2)
        c.create_polygon(32,35,24,18,42,32,fill=body,outline=dark)
        c.create_polygon(60,35,70,18,55,32,fill=body,outline=dark)
        c.create_polygon(33,34,27,21,40,31,fill="#FF9EB5",outline='')
        c.create_polygon(59,34,67,21,54,31,fill="#FF9EB5",outline='')
        c.create_line(40,47,50,44,fill=dark,width=2)
        c.create_line(56,44,66,47,fill=dark,width=2)
        c.create_oval(51,50,57,55,fill="#FF9EB5",outline='')
        rx = int(math.sin(f*0.06)*6)
        c.create_arc(2,55,28,95,start=160+rx,extent=160,style="arc",outline=dark,width=3)
        for i, z in enumerate("zZz"):
            yo = (f*2+i*14)%40
            c.create_text(80,30-yo,text=z,font=("Courier",7+i*2,"bold"),fill=LAVENDER)

    def _lick(self):
        c, f = self.cv, self.frame_n
        fur = FUR.get(self.fur, FUR["cinza"]); body, dark, light = fur
        paw_y = int(72+math.sin(f*0.25)*8)
        c.create_oval(18,40,85,96,fill=body,outline=dark,width=2)
        c.create_oval(22,40,80,80,fill=light,outline='')
        c.create_oval(20,8,82,58,fill=body,outline=dark,width=2)
        c.create_polygon(24,14,16,0,37,12,fill=body,outline=dark)
        c.create_polygon(68,14,78,0,57,12,fill=body,outline=dark)
        c.create_polygon(25,13,19,3,35,11,fill="#FF9EB5",outline='')
        c.create_polygon(67,13,75,3,56,11,fill="#FF9EB5",outline='')
        c.create_arc(30,26,46,40,start=0,extent=180,style='chord',fill=dark,outline='')
        c.create_arc(54,26,70,40,start=0,extent=180,style='chord',fill=dark,outline='')
        c.create_oval(47,44,54,50,fill="#FF9EB5",outline='')
        c.create_oval(14,paw_y-12,36,paw_y+8,fill=body,outline=dark,width=2)
        if f%14<7:
            c.create_oval(18,paw_y-18,32,paw_y-6,fill="#FF4477",outline='')

    def _follow(self):
        c, f = self.cv, self.frame_n
        fur = FUR.get(self.fur, FUR["cinza"]); body, dark, light = fur
        try:
            cx = c.winfo_rootx()+self.SIZE//2; cy = c.winfo_rooty()+self.SIZE//2
            a = math.atan2(self.my-cy, self.mx-cx)
            ex = int(math.cos(a)*3); ey = int(math.sin(a)*3)
        except: ex=ey=0
        bob = int(math.sin(f*0.12)*2)
        c.create_oval(16,46+bob,90,100+bob,fill=body,outline=dark,width=2)
        c.create_oval(28,52+bob,78,90+bob,fill=light,outline='')
        c.create_oval(18,6+bob,88,56+bob,fill=body,outline=dark,width=2)
        c.create_polygon(22,14+bob,12,0+bob,38,12+bob,fill=body,outline=dark)
        c.create_polygon(82,14+bob,94,0+bob,68,12+bob,fill=body,outline=dark)
        c.create_polygon(23,13+bob,16,3+bob,36,11+bob,fill="#FF9EB5",outline='')
        c.create_polygon(81,13+bob,90,3+bob,67,11+bob,fill="#FF9EB5",outline='')
        for bx in (36,70):
            c.create_oval(bx-9,22+bob,bx+9,38+bob,fill=WHITE,outline=dark,width=1)
            c.create_oval(bx+ex-5,27+bob+ey,bx+ex+5,37+bob+ey,fill="#44BB88",outline='')
            c.create_oval(bx+ex-2,29+bob+ey,bx+ex+2,35+bob+ey,fill=dark,outline='')
        c.create_oval(49,41+bob,57,47+bob,fill="#FF9EB5",outline='')
        for x1,y1,x2,y2 in [(16,35+bob,34,33+bob),(16,39+bob,34,39+bob),
                              (72,33+bob,90,35+bob),(72,39+bob,90,39+bob)]:
            c.create_line(x1,y1,x2,y2,fill=dark,width=1)
        tw = int(math.sin(f*0.18)*10)
        c.create_arc(0,62,32,100,start=170+tw,extent=180,style="arc",outline=dark,width=4)

# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════
def px_btn(parent, text, cmd, bg=PINK, fg=TEXT, w=26, pady=10):
    outer = tk.Frame(parent, bg=TEXT, padx=2, pady=2)
    tk.Button(outer, text=text, command=cmd, bg=bg, fg=fg, font=FM,
              relief="flat", bd=0, width=w, padx=12, pady=pady, cursor="hand2",
              activebackground=TEXT, activeforeground=WHITE).pack()
    return outer

def px_entry(parent, var, w=20):
    return tk.Entry(parent, textvariable=var, font=FB, bg=WHITE, fg=TEXT,
                    relief="flat", width=w, highlightthickness=2,
                    highlightbackground=BORDER, highlightcolor=DPINK)

def section_header(parent, title, sub="", bg=PINK):
    f = tk.Frame(parent, bg=bg)
    f.pack(fill="x")
    tk.Label(f, text=title, font=FT, bg=bg, fg=TEXT).pack(pady=(14,3))
    if sub:
        tk.Label(f, text=sub, font=FB, bg=bg, fg=TEXT).pack(pady=(0,10))
    tk.Frame(parent, bg=DPINK, height=3).pack(fill="x")
    return f

# ═══════════════════════════════════════════════
#  FOTO
# ═══════════════════════════════════════════════
_photo_cache: dict = {}

def load_photo(path, size=(100,100)):
    key = (path, size)
    if key in _photo_cache:
        return _photo_cache[key]
    if not PIL_AVAILABLE or not path or not os.path.exists(path):
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
        bg_img = Image.new("RGBA", size, (255,255,255,255))
        ox = (size[0]-img.width)//2; oy = (size[1]-img.height)//2
        bg_img.paste(img, (ox,oy), img)
        tk_img = ImageTk.PhotoImage(bg_img)
        _photo_cache[key] = tk_img
        return tk_img
    except Exception as e:
        print(f"Erro ao carregar foto {path}: {e}")
        return None

def copy_photo_to_app(src_path):
    """Copia a foto para a pasta da app e retorna o novo caminho."""
    if not src_path or not os.path.exists(src_path):
        return src_path
    ext  = os.path.splitext(src_path)[1].lower()
    name = f"cat_{int(time.time())}{ext}"
    dst  = os.path.join(PHOTOS_DIR, name)
    try:
        shutil.copy2(src_path, dst)
        return dst
    except Exception:
        return src_path

# ═══════════════════════════════════════════════
#  ANIMAÇÕES DO PAINEL
# ═══════════════════════════════════════════════
def _fur_or(pelagem):
    return get_fur(pelagem) if pelagem else FUR["cinza"]

def draw_cat_dormindo(c, cx, cy, f, pelagem="cinza"):
    body, dark, light = _fur_or(pelagem); c.delete("cat")
    c.create_oval(cx-65,cy+55,cx+65,cy+75,fill="#E8D8E8",outline='',tags="cat")
    c.create_oval(cx-65,cy-20,cx+65,cy+60,fill=body,outline=dark,width=2,tags="cat")
    c.create_oval(cx-50,cy-15,cx+50,cy+45,fill=light,outline='',tags="cat")
    c.create_oval(cx+10,cy-70,cx+90,cy+10,fill=body,outline=dark,width=2,tags="cat")
    c.create_polygon(cx+15,cy-65,cx+8,cy-90,cx+30,cy-62,fill=body,outline=dark,tags="cat")
    c.create_polygon(cx+72,cy-65,cx+82,cy-90,cx+60,cy-62,fill=body,outline=dark,tags="cat")
    c.create_polygon(cx+17,cy-64,cx+12,cy-84,cx+29,cy-61,fill="#FF9EB5",outline='',tags="cat")
    c.create_polygon(cx+71,cy-64,cx+78,cy-84,cx+61,cy-61,fill="#FF9EB5",outline='',tags="cat")
    c.create_line(cx+28,cy-35,cx+42,cy-38,fill=dark,width=3,tags="cat")
    c.create_line(cx+52,cy-38,cx+66,cy-35,fill=dark,width=3,tags="cat")
    c.create_oval(cx+46,cy-22,cx+54,cy-16,fill="#FF9EB5",outline='',tags="cat")
    rx = int(math.sin(f*0.06)*10)
    c.create_arc(cx-100,cy+10,cx-20,cy+80,start=130+rx,extent=140,
                 style="arc",outline=dark,width=5,tags="cat")
    for i, z in enumerate("zZZ"):
        yo = (f*2+i*20)%70
        c.create_text(cx+105,cy-50-yo,text=z,font=("Courier",9+i*3,"bold"),fill=LAVENDER,tags="cat")

def draw_cat_comendo(c, cx, cy, f, pelagem="cinza"):
    body, dark, light = _fur_or(pelagem); c.delete("cat")
    c.create_oval(cx-55,cy+65,cx+55,cy+80,fill="#E8D8E8",outline='',tags="cat")
    c.create_arc(cx-40,cy+40,cx+40,cy+80,start=180,extent=180,
                 fill=PEACH,outline=BORDER,width=2,style='chord',tags="cat")
    c.create_oval(cx-42,cy+40,cx+42,cy+55,fill=BORDER,outline='',tags="cat")
    for i in range(5):
        bx = cx-20+i*10
        c.create_oval(bx-4,cy+44,bx+4,cy+52,fill=DPINK,outline='',tags="cat")
    c.create_oval(cx-45,cy-25,cx+45,cy+65,fill=body,outline=dark,width=2,tags="cat")
    c.create_oval(cx-35,cy-20,cx+35,cy+50,fill=light,outline='',tags="cat")
    c.create_oval(cx-35,cy-95,cx+35,cy-25,fill=body,outline=dark,width=2,tags="cat")
    c.create_polygon(cx-30,cy-90,cx-42,cy-112,cx-14,cy-88,fill=body,outline=dark,tags="cat")
    c.create_polygon(cx+30,cy-90,cx+42,cy-112,cx+14,cy-88,fill=body,outline=dark,tags="cat")
    c.create_polygon(cx-29,cy-89,cx-39,cy-108,cx-15,cy-87,fill="#FF9EB5",outline='',tags="cat")
    c.create_polygon(cx+29,cy-89,cx+39,cy-108,cx+15,cy-87,fill="#FF9EB5",outline='',tags="cat")
    for ox in (-12,12):
        c.create_oval(cx+ox-8,cy-72,cx+ox+8,cy-56,fill=WHITE,outline=dark,width=1,tags="cat")
        c.create_oval(cx+ox-4,cy-68,cx+ox+4,cy-60,fill="#44BB88",outline='',tags="cat")
        c.create_oval(cx+ox-2,cy-67,cx+ox+2,cy-61,fill=dark,outline='',tags="cat")
    t = f%20; ty = cy-40+(4 if t<10 else 0)
    c.create_oval(cx-8,ty,cx+8,ty+14,fill="#FF4477",outline='',tags="cat")
    for i in range(2):
        hx = cx+50+i*20; hy = cy-70-(f*2+i*25)%50
        c.create_text(hx,hy,text="♥",font=("Courier",12,"bold"),fill=DPINK,tags="cat")

def draw_cat_gordo(c, cx, cy, f, pelagem="cinza"):
    body, dark, light = _fur_or(pelagem); c.delete("cat")
    c.create_oval(cx-75,cy+55,cx+75,cy+80,fill="#E8D8E8",outline='',tags="cat")
    c.create_oval(cx-75,cy-50,cx+75,cy+70,fill=body,outline=dark,width=3,tags="cat")
    c.create_oval(cx-60,cy-40,cx+60,cy+55,fill=light,outline='',tags="cat")
    c.create_oval(cx-45,cy-115,cx+45,cy-30,fill=body,outline=dark,width=2,tags="cat")
    c.create_oval(cx-50,cy-80,cx-20,cy-55,fill="#FFD0D8",outline='',tags="cat")
    c.create_oval(cx+20,cy-80,cx+50,cy-55,fill="#FFD0D8",outline='',tags="cat")
    c.create_polygon(cx-40,cy-110,cx-55,cy-132,cx-20,cy-108,fill=body,outline=dark,tags="cat")
    c.create_polygon(cx+40,cy-110,cx+55,cy-132,cx+20,cy-108,fill=body,outline=dark,tags="cat")
    c.create_polygon(cx-39,cy-109,cx-51,cy-128,cx-21,cy-107,fill="#FF9EB5",outline='',tags="cat")
    c.create_polygon(cx+39,cy-109,cx+51,cy-128,cx+21,cy-107,fill="#FF9EB5",outline='',tags="cat")
    for ox in (-15,15):
        c.create_oval(cx+ox-9,cy-90,cx+ox+9,cy-74,fill=WHITE,outline=dark,width=1,tags="cat")
        c.create_arc(cx+ox-9,cy-90,cx+ox+9,cy-74,start=0,extent=180,
                     style='chord',fill=dark,outline='',tags="cat")
    c.create_oval(cx-6,cy-68,cx+6,cy-62,fill="#FF9EB5",outline='',tags="cat")
    for pox in (-55,45):
        c.create_oval(cx+pox,cy+20,cx+pox+25,cy+45,fill=body,outline=dark,width=2,tags="cat")
    for i in range(4):
        a = math.radians(f*4+i*90)
        sx = cx+int(math.cos(a)*90); sy = cy+int(math.sin(a)*40)-20
        pts = []
        for j in range(5):
            ra = math.radians(-90+j*72*2+f*4); rb = math.radians(-90+(j*2+1)*36+f*4)
            pts += [sx+int(math.cos(ra)*9), sy+int(math.sin(ra)*9)]
            pts += [sx+int(math.cos(rb)*4), sy+int(math.sin(rb)*4)]
        c.create_polygon(pts,fill=GOLD,outline='',tags="cat")

def draw_cat_aventureiro(c, cx, cy, f, pelagem="cinza"):
    body, dark, light = _fur_or(pelagem); c.delete("cat")
    c.create_oval(cx-50,cy+65,cx+50,cy+78,fill="#E8D8E8",outline='',tags="cat")
    bob = int(math.sin(f*0.22)*5)
    tw  = int(math.sin(f*0.15)*12)
    c.create_arc(cx+30,cy-30+bob,cx+90,cy+50+bob,start=60+tw,extent=200,
                 style="arc",outline=dark,width=5,tags="cat")
    c.create_oval(cx-42,cy-10+bob,cx+42,cy+70+bob,fill=body,outline=dark,width=2,tags="cat")
    c.create_oval(cx-32,cy-5+bob,cx+32,cy+60+bob,fill=light,outline='',tags="cat")
    c.create_rectangle(cx-42,cy+8+bob,cx+42,cy+22+bob,fill="#FF4444",outline="#CC2222",width=1,tags="cat")
    c.create_polygon(cx+42,cy+8+bob,cx+42,cy+22+bob,cx+58,cy+15+bob,fill="#FF4444",outline='',tags="cat")
    c.create_oval(cx-35,cy-90+bob,cx+35,cy-20+bob,fill=body,outline=dark,width=2,tags="cat")
    c.create_polygon(cx-30,cy-85+bob,cx-44,cy-108+bob,cx-12,cy-83+bob,fill=body,outline=dark,tags="cat")
    c.create_polygon(cx+30,cy-85+bob,cx+44,cy-108+bob,cx+12,cy-83+bob,fill=body,outline=dark,tags="cat")
    c.create_polygon(cx-29,cy-84+bob,cx-40,cy-104+bob,cx-13,cy-82+bob,fill="#FF9EB5",outline='',tags="cat")
    c.create_polygon(cx+29,cy-84+bob,cx+40,cy-104+bob,cx+13,cy-82+bob,fill="#FF9EB5",outline='',tags="cat")
    for ox in (-12,12):
        c.create_oval(cx+ox-9,cy-68+bob,cx+ox+9,cy-50+bob,fill=WHITE,outline=dark,width=1,tags="cat")
        c.create_oval(cx+ox-5,cy-65+bob,cx+ox+5,cy-55+bob,fill="#44BB88",outline='',tags="cat")
        c.create_oval(cx+ox-2,cy-63+bob,cx+ox+2,cy-57+bob,fill=dark,outline='',tags="cat")
    c.create_oval(cx-5,cy-44+bob,cx+5,cy-38+bob,fill="#FF9EB5",outline='',tags="cat")
    for i, (ox, phase) in enumerate([(-22,0),(-8,math.pi),(8,math.pi),(22,0)]):
        leg_y = int(math.sin(f*0.3+phase)*12)
        c.create_oval(cx+ox-8,cy+50+bob+leg_y,cx+ox+8,cy+72+bob+leg_y,
                      fill=body,outline=dark,width=1,tags="cat")
    for i in range(3):
        px = cx-80-i*28; py = cy+75+(i%2)*12
        col = [LGRAY,MGRAY,DGRAY][i]
        c.create_oval(px-8,py-8,px+8,py+8,fill=col,outline='',tags="cat")
        for j in range(3):
            ta = math.radians(j*120-60)
            c.create_oval(px+int(math.cos(ta)*9)-4,py+int(math.sin(ta)*9)-4,
                          px+int(math.cos(ta)*9)+4,py+int(math.sin(ta)*9)+4,
                          fill=col,outline='',tags="cat")


# ═══════════════════════════════════════════════
#  SISTEMA DE TOAST (substitui messagebox)
# ═══════════════════════════════════════════════
class ToastManager:
    """
    Gerencia notificações flutuantes no canto superior esquerdo.
    Cada toast aparece, empilha e some automaticamente após alguns segundos.
    Toasts críticos (needs_owner=True) ficam até o usuário dispensar.
    """
    TOAST_W   = 340
    TOAST_H   = 80
    MARGIN    = 8
    AUTO_HIDE = 5000   # ms para toasts sutis
    X_OFFSET  = 8
    Y_OFFSET  = 8

    def __init__(self, root, content_frame):
        self.root    = root
        self.content = content_frame
        self._toasts = []   # list of tk.Frame

    def show(self, msg: str, kind: str = "info", on_ok=None):
        """
        kind: "info" (azul sutil), "warn" (laranja), "critical" (vermelho, fica até ok)
        on_ok: callback chamado quando o usuário pressiona OK (toasts críticos)
        """
        colors = {
            "info":     (LAVENDER, TEXT,    "ℹ",  False),
            "warn":     (PEACH,    TEXT,    "⚠",  False),
            "critical": (DPINK,    WHITE,   "🚨", True),
        }
        bg, fg, icon, sticky = colors.get(kind, colors["info"])

        # Frame do toast
        frame = tk.Frame(self.content, bg=bg,
                         highlightthickness=2, highlightbackground=BORDER,
                         relief="flat")

        # Ícone + texto
        top = tk.Frame(frame, bg=bg)
        top.pack(fill="x", padx=10, pady=(8,4))
        tk.Label(top, text=icon, font=("Courier",14,"bold"),
                 bg=bg, fg=fg).pack(side="left", padx=(0,6))
        tk.Label(top, text=msg, font=FS, bg=bg, fg=fg,
                 wraplength=self.TOAST_W-70, justify="left",
                 anchor="w").pack(side="left", fill="x", expand=True)

        # Botão fechar / OK
        def _dismiss():
            self._remove(frame)
            if on_ok:
                on_ok()

        btn_text = "OK" if sticky else "✕"
        btn_bg   = RED_BLOCK if sticky else DGRAY
        tk.Button(frame, text=btn_text, command=_dismiss,
                  bg=btn_bg, fg=WHITE, font=FS, relief="flat",
                  cursor="hand2", padx=8, pady=2).pack(side="right", padx=8, pady=8)

        self._toasts.append(frame)
        self._restack()

        # Auto-hide para toasts não-críticos
        if not sticky:
            self.root.after(self.AUTO_HIDE, lambda: self._remove(frame))

    def _remove(self, frame):
        if frame in self._toasts:
            self._toasts.remove(frame)
            try:
                frame.place_forget()
                frame.destroy()
            except Exception:
                pass
        self._restack()

    def _restack(self):
        """
        Reposiciona todos os toasts no canto superior DIREITO.
        Calcula x a partir da largura real do content frame, o que funciona
        em qualquer tamanho, inclusive fullscreen.
        relx=1.0/anchor="ne" falha quando o widget ainda nao foi renderizado;
        o calculo explicito de x e mais robusto.
        """
        self.root.update_idletasks()
        content_w = self.content.winfo_width()
        if content_w <= 1:
            self.root.after(80, self._restack)
            return
        x = content_w - self.TOAST_W - self.X_OFFSET
        y = self.Y_OFFSET
        for f in self._toasts:
            try:
                f.place(in_=self.content, x=x, y=y, width=self.TOAST_W)
                f.lift()
                self.root.update_idletasks()
                h = f.winfo_reqheight()
                y += h + self.MARGIN
            except Exception:
                pass


# ═══════════════════════════════════════════════
#  APLICATIVO PRINCIPAL
# ═══════════════════════════════════════════════
class CatApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🐾 Cat Monitorator")
        self.root.configure(bg=BG)
        self.root.geometry("1024x768")
        self._fullscreen = False
        self._stack: list = []

        # Navbar
        self._topbar = tk.Frame(self.root, bg=BORDER, height=3)
        self._topbar.pack(fill="x", side="top")
        self._navbar = tk.Frame(self.root, bg=LAVENDER, pady=6)
        self._navbar.pack(fill="x", side="top")
        self._back_btn = tk.Button(
            self._navbar, text="◀  voltar", font=FB,
            bg=LAVENDER, fg=TEXT, relief="flat", bd=0,
            cursor="hand2", command=self._pop, activebackground=PINK)
        self._back_btn.pack(side="left", padx=14)
        self._crumb_lbl = tk.Label(self._navbar, text="", font=FB, bg=LAVENDER, fg=TEXT)
        self._crumb_lbl.pack(side="left", padx=4)
        tk.Button(self._navbar, text="⛶  tela cheia", font=FS,
                  bg=LAVENDER, fg=TEXT, relief="flat", bd=0,
                  cursor="hand2", command=self._toggle_fs,
                  activebackground=PINK).pack(side="right", padx=14)

        # Conteúdo
        self._content = tk.Frame(self.root, bg=BG)
        self._content.pack(fill="both", expand=True)

        # Toast manager (global para toda a app)
        self.toast = ToastManager(self.root, self._content)

        # Callback chamado quando _handle_alert atualiza o estado de um gato.
        # A _page_sensor o registra para atualizar estado_lbl em tempo real.
        # Outras páginas deixam None.
        self._sensor_refresh_cb = None
        self._sensor_event_hook  = None

        # Mascote
        self.mascot = MascotCat(self.root, self._content)

        # Dados
        global cat_data
        cat_data = load_cats()

        # TCP servidor
        self.server_conn = None
        self._srv_buf    = ""
        self._connect_to_server()

        self.root.bind("<F11>", lambda e: self._toggle_fs())
        self.root.bind("<Escape>", lambda e: self._exit_fs())

        self._push("🏠  início", self._page_main)

    # ── TCP ──────────────────────────────────────
    def _connect_to_server(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0); s.connect((SERVER_HOST, SERVER_PORT))
            s.settimeout(None); self.server_conn = s
            threading.Thread(target=self._listen_server, daemon=True).start()
            print(f"[UI] Conectado ao servidor {SERVER_HOST}:{SERVER_PORT}")
        except Exception as e:
            self.server_conn = None
            print(f"[UI] Servidor não disponível: {e}")

    def _send_command(self, cmd):
        if self.server_conn:
            try:
                self.server_conn.sendall((json.dumps(cmd)+"\n").encode())
            except Exception as e:
                print(f"[UI] Erro ao enviar: {e}")

    def _listen_server(self):
        buf = b""
        try:
            while True:
                chunk = self.server_conn.recv(1024)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        alert = json.loads(line.decode("utf-8", errors="ignore"))
                        self.root.after(0, lambda a=alert: self._handle_alert(a))
                    except Exception:
                        pass
        except Exception as e:
            print(f"[UI] Conexão encerrada: {e}")

    def _handle_alert(self, alert):
        """
        Processa mensagens do servidor. Dois tipos chegam:

        1. Alertas normais (com "message"): viram toasts e opcionalmente
           atualizam o estado do gato se o alert incluir o campo "estado".

        2. state_update (sem "message"): só atualizam o estado do gato.
           Enviados pelo server quando o gato chega/sai da cama ou quando
           outros sensores disparam, sem necessidade de notificar o dono.

        O campo "estado" no alert é definido pelo SERVER, não inferido aqui.
        Isso evita falsos positivos (ex: "tentou sair" atualizar estado para
        "aventureiro" mesmo com a porta bloqueada).
        """
        msg         = alert.get("message")
        sensor      = alert.get("sensor", "")
        cat         = alert.get("cat_name", "")
        action      = alert.get("action")
        subtle      = alert.get("subtle", False)
        needs_owner = alert.get("needs_owner", False)
        novo_estado = alert.get("estado")   # lido diretamente do server

        # ── Atualiza estado do gato ────────────────────────────────
        if cat and cat in cat_data and novo_estado:
            # "acordado" não tem animação própria: volta para "dormindo"
            # (próximo evento real — comer, sair — vai substituir)
            estado_mapeado = "dormindo" if novo_estado == "acordado" else novo_estado
            if cat_data[cat].get("estado") != estado_mapeado:
                cat_data[cat]["estado"] = estado_mapeado
                save_cats(cat_data)
                if self._sensor_refresh_cb:
                    self._sensor_refresh_cb(cat)

        # ── state_update puro: sem toast ──────────────────────────
        if alert.get("type") == "state_update":
            return

        # ── Exibe toast ────────────────────────────────────────────
        if not msg:
            return
        if isinstance(msg, list):
            msg = " | ".join(msg)

        def _on_ok():
            if sensor == "bed":
                self._send_command({"command": "ok_bed", "cat": cat})
            elif sensor == "sandbox":
                self._send_command({"command": "ok_sandbox", "cat": cat})

        # Despacha evento para o feed do painel de sensores
        if self._sensor_event_hook and sensor:
            self._sensor_event_hook(alert)

        if needs_owner:
            self.toast.show(msg, kind="critical", on_ok=_on_ok)
        elif action:
            self.toast.show(msg, kind="warn")
        else:
            self.toast.show(msg, kind="info")

    # ── Navegação ─────────────────────────────────
    def _push(self, title, builder, *args):
        self._stack.append((title, builder, args)); self._render()

    def _pop(self):
        if len(self._stack) > 1:
            self._stack.pop()
            self._sensor_refresh_cb = None
            self._sensor_event_hook  = None   # limpa hooks ao sair da página de sensores
            self._render()

    def _render(self):
        for w in self._content.winfo_children():
            if w is not self.mascot.cv:
                w.destroy()
        # Recria o toast manager apontando para o novo content
        self.toast = ToastManager(self.root, self._content)

        title, builder, args = self._stack[-1]
        crumb = " › ".join(t for t,_,_ in self._stack)
        self._crumb_lbl.config(text=crumb)
        (self._back_btn.pack if len(self._stack)>1 else self._back_btn.pack_forget)(
            side="left", padx=14) if len(self._stack)>1 else self._back_btn.pack_forget()
        builder(*args)
        try:
            self.mascot.cv.tkraise()
        except Exception:
            pass
        self.mascot.cv.place(in_=self._content, relx=1.0, rely=1.0, anchor="se", x=-12, y=-12)

    def _toggle_fs(self):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    def _exit_fs(self):
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes("-fullscreen", False)

    # ══════════════════════════════════════════════
    #  PÁGINAS
    # ══════════════════════════════════════════════

    # ── Principal ─────────────────────────────────
    def _page_main(self):
        cf = self._content
        bg_cv = tk.Canvas(cf, bg=BG, highlightthickness=0)
        bg_cv.pack(fill="both", expand=True)

        center = tk.Frame(bg_cv, bg=BG)
        win_id = bg_cv.create_window(0, 0, window=center, anchor="center")

        def _resize(e):
            # FIX 1: centraliza corretamente em qualquer tamanho, inclusive fullscreen
            bg_cv.coords(win_id, e.width//2, e.height//2)
            bg_cv.delete("decor")
            random.seed(7)
            for _ in range(18):
                px = random.randint(20, e.width-20)
                py = random.randint(20, e.height-20)
                bg_cv.create_oval(px-10,py-10,px+10,py+10,fill=LGRAY,outline='',tags="decor")
            for sx, sy, spr in [(20,80,SPR_SENTADO),(0,150,SPR_DORMINDO)]:
                _render_sprite(bg_cv,sx,sy,spr,"cinza",px=3,tag="decor")

        bg_cv.bind("<Configure>", _resize)

        tk.Label(center, text="🐾  Cat Monitorator",
                 font=("Courier",28,"bold"), bg=BG, fg=TEXT).pack(pady=(0,4))
        tk.Label(center, text="sistema distribuído de monitoramento felino",
                 font=FB, bg=BG, fg=DGRAY).pack()
        tk.Frame(center, bg=DPINK, height=3, width=400).pack(pady=12)

        grid = tk.Frame(center, bg=BG)
        grid.pack(pady=8)
        btns = [
            ("🐱  cadastrar gatinho",  PINK,     self._goto_register),
            ("📋  ver gatinhos",        MINT,     self._goto_view),
            ("✏️   editar gatinho",     PEACH,    self._goto_edit),
            ("🗑️   excluir gatinho",    LAVENDER, self._goto_delete),
            ("📡  painel de sensores", YELLOW,   self._goto_sensor),
        ]
        for i, (lbl, bg_c, cmd) in enumerate(btns):
            r, col = divmod(i, 2)
            px_btn(grid, lbl, cmd, bg=bg_c, w=22, pady=12).grid(row=r, column=col, padx=10, pady=8)

        tk.Label(center,
                 text="⚠  este sistema não substitui a atenção presencial ao seu gatinho!",
                 font=FS, bg=BG, fg=DGRAY, wraplength=480).pack(pady=16)

    def _goto_register(self): self._push("🐱  cadastrar", self._page_register)
    def _goto_view(self):     self._push("📋  ver gatinhos", self._page_view)
    def _goto_edit(self):     self._push("✏️  editar", self._page_edit)
    def _goto_delete(self):   self._push("🗑️  excluir", self._page_delete)
    def _goto_sensor(self):   self._push("📡  sensores", self._page_sensor)

    # ── Cadastrar ─────────────────────────────────
    def _page_register(self):
        cf = self._content
        section_header(cf, "🐱  cadastrar gatinho",
                       "preencha os dados do seu novo amiguinho ♡", PINK)
        body = tk.Frame(cf, bg=BG)
        body.pack(fill="both", expand=True, padx=40, pady=20)
        left  = tk.Frame(body, bg=BG); left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(body, bg=BG, width=220); right.pack(side="right", fill="y", padx=(20,0))
        right.pack_propagate(False)

        v = {k: tk.StringVar() for k in ["nome","raça","peso","idade"]}
        pelagem_var = tk.StringVar(value=FUR_OPTIONS[0])
        filhote_var = tk.BooleanVar(); castrado_var = tk.BooleanVar()
        photo_path  = tk.StringVar()

        def field(parent, label, var, hint=""):
            row = tk.Frame(parent, bg=BG); row.pack(fill="x", pady=5)
            tk.Label(row, text=label, font=FB, bg=BG, fg=TEXT,
                     width=16, anchor="w").pack(side="left")
            px_entry(row, var, w=22).pack(side="left")
            if hint:
                tk.Label(row, text=hint, font=FS, bg=BG, fg=DGRAY).pack(side="left", padx=6)

        field(left,"nome:",v["nome"]); field(left,"raça:",v["raça"])
        field(left,"peso (kg):",v["peso"],"ex: 4.2"); field(left,"idade:",v["idade"],"anos ou meses")

        prow = tk.Frame(left, bg=BG); prow.pack(fill="x", pady=5)
        tk.Label(prow, text="pelagem:", font=FB, bg=BG, fg=TEXT,
                 width=16, anchor="w").pack(side="left")
        combo = ttk.Combobox(prow, textvariable=pelagem_var, values=FUR_OPTIONS,
                             state="readonly", font=FB, width=18)
        combo.pack(side="left")
        spr_cv = tk.Canvas(prow, width=80, height=70, bg=BG, highlightthickness=0)
        spr_cv.pack(side="left", padx=10)
        def update_preview(*_):
            spr_cv.delete("all")
            _render_sprite(spr_cv,0,0,SPR_SENTADO,pelagem_var.get(),px=5,tag="all")
        combo.bind("<<ComboboxSelected>>", update_preview); update_preview()

        ck_row = tk.Frame(left, bg=BG); ck_row.pack(fill="x", pady=8)
        tk.Checkbutton(ck_row, text="é filhote?", variable=filhote_var,
                       font=FB, bg=BG, fg=TEXT, activebackground=BG,
                       selectcolor=PINK).pack(side="left", padx=10)
        tk.Checkbutton(ck_row, text="é castrado?", variable=castrado_var,
                       font=FB, bg=BG, fg=TEXT, activebackground=BG,
                       selectcolor=MINT).pack(side="left", padx=10)

        # Foto
        tk.Label(right, text="📷  foto do gatinho", font=FM, bg=BG, fg=TEXT).pack(pady=(10,6))
        if not PIL_AVAILABLE:
            tk.Label(right, text="⚠ instale Pillow\npara usar fotos:\npip install Pillow",
                     font=FS, bg=PEACH, fg=TEXT, justify="center",
                     relief="flat", padx=8, pady=6).pack(pady=8)
        tk.Label(right, text="(opcional)", font=FS, bg=BG, fg=DGRAY).pack()
        photo_cv = tk.Canvas(right, width=160, height=160, bg=LGRAY,
                             highlightthickness=2, highlightbackground=BORDER)
        photo_cv.pack(pady=8)
        photo_cv.create_text(80,80, text="nenhuma foto\nselecionada",
                             font=FS, fill=DGRAY, justify="center")
        _photo_ref = [None]

        def _open_gallery():
            if not PIL_AVAILABLE:
                self.toast.show("Instale Pillow para usar fotos:\npip install Pillow", kind="warn")
                return
            path = filedialog.askopenfilename(
                title="Selecionar foto",
                filetypes=[("Imagens","*.jpg *.jpeg *.png *.gif *.bmp *.webp"),("Todos","*.*")])
            if not path: return
            img = load_photo(path, (156,156))
            if img:
                _photo_ref[0] = img
                photo_path.set(path)
                photo_cv.delete("all")
                photo_cv.create_image(2,2, image=img, anchor="nw")
            else:
                photo_cv.delete("all")
                photo_cv.create_text(80,80, text="erro ao\ncarregar",
                                     font=FS, fill="#CC4444", justify="center")

        def _clear_photo():
            photo_path.set(""); _photo_ref[0] = None
            photo_cv.delete("all")
            photo_cv.create_text(80,80, text="nenhuma foto\nselecionada",
                                 font=FS, fill=DGRAY, justify="center")

        px_btn(right,"🖼  da galeria",_open_gallery,bg=PEACH,w=16,pady=6).pack(pady=4)
        px_btn(right,"✕  remover",_clear_photo,bg=LGRAY,fg=DGRAY,w=16,pady=4).pack(pady=2)

        def _save():
            nome = v["nome"].get().strip().lower()
            if not nome:
                self.toast.show("O gatinho precisa de um nome ♡", kind="warn"); return
            if nome in cat_data:
                if not messagebox.askyesno("já existe", f"'{nome}' já existe. sobrescrever?"): return
            try: peso = float(v["peso"].get())
            except ValueError:
                self.toast.show("Peso deve ser número. ex: 4.2", kind="warn"); return
            try: idade = int(v["idade"].get())
            except ValueError:
                self.toast.show("Idade deve ser número inteiro", kind="warn"); return

            foto_final = copy_photo_to_app(photo_path.get()) if photo_path.get() else ""
            cat_data[nome] = {
                "raça": v["raça"].get().strip(), "pelagem": pelagem_var.get(),
                "peso": peso, "idade": idade, "filhote": filhote_var.get(),
                "castrado": castrado_var.get(), "estado": "dormindo", "foto": foto_final,
            }
            save_cats(cat_data)
            self.toast.show(f"Gatinho '{nome}' cadastrado! 🐾", kind="info")
            self.root.after(1200, self._pop)

        px_btn(cf,"💾  salvar gatinho",_save,bg=MINT,w=28,pady=12).pack(pady=12)

    # ── Ver ────────────────────────────────────────
    def _page_view(self):
        cf = self._content
        section_header(cf,"📋  gatinhos cadastrados",
                       f"{len(cat_data)} gatinho(s) no sistema ♡", MINT)
        outer = tk.Frame(cf, bg=BG); outer.pack(fill="both", expand=True, padx=20, pady=10)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0,0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120),"units"))

        if not cat_data:
            tk.Label(inner, text="nenhum gatinho cadastrado ainda...\n(｡•́︿•̀｡)",
                     font=FM, bg=BG, fg=DGRAY).pack(pady=60); return

        colors = [PINK, MINT, PEACH, LAVENDER, YELLOW]
        for i, (nome, info) in enumerate(cat_data.items()):
            bg_c = colors[i%len(colors)]
            card = tk.Frame(inner, bg=bg_c, relief="flat",
                            highlightthickness=2, highlightbackground=BORDER)
            card.pack(fill="x", padx=12, pady=6)
            spr_cv = tk.Canvas(card, width=72, height=68, bg=bg_c, highlightthickness=0)
            spr_cv.pack(side="left", padx=10, pady=8)
            _render_sprite(spr_cv,1,1,SPR_SENTADO,info.get("pelagem","cinza"),px=5,tag="s")
            nf = tk.Frame(card, bg=bg_c); nf.pack(side="left", fill="both", expand=True, pady=8)
            tk.Label(nf, text=nome.title(), font=FM, bg=bg_c, fg=TEXT).pack(anchor="w")
            tk.Label(nf,
                     text=f"raça: {info.get('raça','-')}  •  peso: {info.get('peso','-')} kg  •  estado: {info.get('estado','dormindo')}",
                     font=FS, bg=bg_c, fg=TEXT).pack(anchor="w")
            if info.get("foto"):
                img = load_photo(info["foto"], (60,60))
                if img:
                    lbl = tk.Label(card, image=img, bg=bg_c)
                    lbl.image = img; lbl.pack(side="right", padx=10, pady=8)

    # ── Editar ─────────────────────────────────────
    def _page_edit(self):
        cf = self._content
        section_header(cf,"✏️  editar gatinho","selecione e atualize os dados ♡", PEACH)
        body = tk.Frame(cf, bg=BG); body.pack(fill="both", expand=True, padx=50, pady=20)
        selected = tk.StringVar(); names = list(cat_data.keys())
        if not names:
            tk.Label(body, text="nenhum gatinho cadastrado.", font=FM, bg=BG, fg=DGRAY).pack(pady=40); return

        sel_row = tk.Frame(body, bg=BG); sel_row.pack(fill="x", pady=8)
        tk.Label(sel_row, text="gatinho:", font=FB, bg=BG, fg=TEXT, width=14, anchor="w").pack(side="left")
        combo = ttk.Combobox(sel_row, textvariable=selected, values=names,
                             state="readonly", font=FM, width=20); combo.pack(side="left")
        spr_cv = tk.Canvas(sel_row, width=72, height=68, bg=BG, highlightthickness=0)
        spr_cv.pack(side="left", padx=14)

        fields = {}; pelagem_var = tk.StringVar()
        filhote_var = tk.BooleanVar(); castrado_var = tk.BooleanVar()
        photo_path = tk.StringVar(); _photo_ref = [None]
        form = tk.Frame(body, bg=BG); form.pack(fill="x", pady=8)

        for lbl, key in [("raça:","raça"),("peso (kg):","peso"),("idade:","idade")]:
            row = tk.Frame(form, bg=BG); row.pack(fill="x", pady=4)
            tk.Label(row, text=lbl, font=FB, bg=BG, fg=TEXT, width=16, anchor="w").pack(side="left")
            var = tk.StringVar(); fields[key] = var
            px_entry(row, var).pack(side="left")

        p_row = tk.Frame(form, bg=BG); p_row.pack(fill="x", pady=4)
        tk.Label(p_row, text="pelagem:", font=FB, bg=BG, fg=TEXT, width=16, anchor="w").pack(side="left")
        pel_combo = ttk.Combobox(p_row, textvariable=pelagem_var, values=FUR_OPTIONS,
                                 state="readonly", font=FB, width=18); pel_combo.pack(side="left")

        ck_row = tk.Frame(form, bg=BG); ck_row.pack(fill="x", pady=6)
        tk.Checkbutton(ck_row, text="filhote", variable=filhote_var, font=FB, bg=BG,
                       activebackground=BG, selectcolor=PINK).pack(side="left", padx=10)
        tk.Checkbutton(ck_row, text="castrado", variable=castrado_var, font=FB, bg=BG,
                       activebackground=BG, selectcolor=MINT).pack(side="left", padx=10)

        photo_cv = tk.Canvas(form, width=100, height=100, bg=LGRAY,
                             highlightthickness=1, highlightbackground=BORDER)
        photo_cv.pack(pady=6)

        def _choose_photo():
            if not PIL_AVAILABLE:
                self.toast.show("Instale Pillow: pip install Pillow", kind="warn"); return
            path = filedialog.askopenfilename(
                filetypes=[("Imagens","*.jpg *.jpeg *.png *.bmp *.webp")])
            if not path: return
            img = load_photo(path, (96,96))
            if img:
                _photo_ref[0] = img; photo_path.set(path)
                photo_cv.delete("all"); photo_cv.create_image(2,2,image=img,anchor="nw")

        px_btn(form,"🖼  trocar foto",_choose_photo,bg=PEACH,w=18,pady=6).pack(pady=4)

        def _load_fields(*_):
            nome = selected.get()
            if nome not in cat_data: return
            info = cat_data[nome]
            fields["raça"].set(info.get("raça","")); fields["peso"].set(info.get("peso",""))
            fields["idade"].set(info.get("idade","")); pelagem_var.set(info.get("pelagem",FUR_OPTIONS[0]))
            filhote_var.set(info.get("filhote",False)); castrado_var.set(info.get("castrado",False))
            photo_path.set(info.get("foto",""))
            spr_cv.delete("all"); _render_sprite(spr_cv,1,1,SPR_SENTADO,info.get("pelagem","cinza"),px=5,tag="s")
            photo_cv.delete("all")
            if info.get("foto"):
                img = load_photo(info["foto"],(96,96))
                if img:
                    _photo_ref[0] = img; photo_cv.create_image(2,2,image=img,anchor="nw"); return
            photo_cv.create_text(50,50,text="sem foto",font=FS,fill=DGRAY,justify="center")

        combo.bind("<<ComboboxSelected>>", _load_fields)

        def _save():
            nome = selected.get()
            if nome not in cat_data:
                self.toast.show("Selecione um gatinho!", kind="warn"); return
            try: peso = float(fields["peso"].get())
            except ValueError:
                self.toast.show("Peso deve ser número", kind="warn"); return
            try: idade = int(fields["idade"].get())
            except ValueError:
                self.toast.show("Idade deve ser inteiro", kind="warn"); return
            foto_final = copy_photo_to_app(photo_path.get()) if photo_path.get() else cat_data[nome].get("foto","")
            cat_data[nome].update({
                "raça": fields["raça"].get(), "pelagem": pelagem_var.get(),
                "peso": peso, "idade": idade, "filhote": filhote_var.get(),
                "castrado": castrado_var.get(), "foto": foto_final,
            })
            save_cats(cat_data)
            self.toast.show(f"Gatinho '{nome}' atualizado! ♡", kind="info")
            self.root.after(1200, self._pop)

        px_btn(body,"💾  salvar alterações",_save,bg=MINT,w=28,pady=12).pack(pady=10)

    # ── Excluir ────────────────────────────────────
    def _page_delete(self):
        cf = self._content
        section_header(cf,"🗑️  excluir gatinho","cuidado: ação irreversível", LAVENDER)
        body = tk.Frame(cf, bg=BG); body.pack(fill="both", expand=True, padx=60, pady=30)
        names = list(cat_data.keys())
        if not names:
            tk.Label(body, text="nenhum gatinho cadastrado.", font=FM, bg=BG, fg=DGRAY).pack(pady=40); return

        selected = tk.StringVar()
        spr_cv = tk.Canvas(body, width=80, height=74, bg=BG, highlightthickness=0)
        spr_cv.pack(pady=8)
        sel_row = tk.Frame(body, bg=BG); sel_row.pack(pady=10)
        tk.Label(sel_row, text="gatinho:", font=FB, bg=BG, fg=TEXT).pack(side="left")
        combo = ttk.Combobox(sel_row, textvariable=selected, values=names,
                             state="readonly", font=FM, width=20)
        combo.pack(side="left", padx=10)

        def _on_sel(*_):
            nome = selected.get()
            if nome in cat_data:
                spr_cv.delete("all")
                _render_sprite(spr_cv,2,2,SPR_SENTADO,cat_data[nome].get("pelagem","cinza"),px=5,tag="s")
        combo.bind("<<ComboboxSelected>>", _on_sel)

        def _delete():
            nome = selected.get()
            if nome not in cat_data:
                self.toast.show("Selecione um gatinho!", kind="warn"); return
            if messagebox.askyesno("confirmar", f"excluir '{nome}'?\n(｡•́︿•̀｡)"):
                del cat_data[nome]; save_cats(cat_data)
                _photo_cache.clear()
                self.toast.show(f"'{nome}' removido.", kind="info")
                self.root.after(1200, self._pop)

        px_btn(body,"🗑️  excluir gatinho",_delete,bg=DPINK,w=26,pady=12).pack(pady=16)

    # ── Sensores ───────────────────────────────────
    def _page_sensor(self):
        cf = self._content
        section_header(cf,"📡  painel de sensores","monitoramento em tempo real ♡", YELLOW)

        if not cat_data:
            tk.Label(cf, text="cadastre um gatinho primeiro! (｡•́︿•̀｡)",
                     font=FM, bg=BG, fg=DGRAY).pack(pady=60); return

        main = tk.Frame(cf, bg=BG); main.pack(fill="both", expand=True)

        # ══════════════════════════════════════════
        # PAINEL ESQUERDO — gatinho + controles
        # ══════════════════════════════════════════
        left = tk.Frame(main, bg=LAVENDER, width=230)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="gatinho:", font=FB, bg=LAVENDER, fg=TEXT).pack(pady=(14,3))
        selected = tk.StringVar(value=list(cat_data.keys())[0])
        cat_combo = ttk.Combobox(left, textvariable=selected,
                                 values=list(cat_data.keys()),
                                 state="readonly", font=FM, width=14)
        cat_combo.pack(padx=10)

        tk.Label(left, text="estado:", font=FB, bg=LAVENDER, fg=TEXT).pack(pady=(10,2))
        estado_lbl = tk.Label(left, text="💤 dormindo", font=FM, bg=LAVENDER, fg=TEXT)
        estado_lbl.pack()

        info_lbl = tk.Label(left, text="", font=FS, bg=LAVENDER, fg=TEXT,
                            wraplength=210, justify="left")
        info_lbl.pack(pady=6, padx=8)

        spr_left = tk.Canvas(left, width=74, height=68, bg=LAVENDER, highlightthickness=0)
        spr_left.pack()

        tk.Frame(left, bg=BORDER, height=2).pack(fill="x", pady=6, padx=8)
        tk.Label(left, text="controle do dono:", font=FB, bg=LAVENDER, fg=TEXT).pack(pady=(2,4))

        def ctrl_btn(txt, bg_c, cmd):
            tk.Button(left, text=txt, command=cmd, bg=bg_c, fg=TEXT,
                      font=FS, relief="flat", cursor="hand2",
                      activebackground=TEXT, activeforeground=WHITE,
                      padx=4, pady=3).pack(fill="x", padx=10, pady=1)

        tk.Label(left, text="🍽 dispenser:", font=FS, bg=LAVENDER, fg=TEXT).pack(anchor="w", padx=10, pady=(4,0))
        ctrl_btn("🔓 desbloquear", MINT,
                 lambda: (self._send_command({"command":"unblock_food","cat":selected.get()}),
                          self.toast.show(f"Dispenser desbloqueado para {selected.get()}", kind="info")))
        ctrl_btn("🔒 bloquear", RED_BLOCK,
                 lambda: (self._send_command({"command":"block_food","cat":selected.get()}),
                          self.toast.show(f"Dispenser bloqueado para {selected.get()}", kind="warn")))

        tk.Label(left, text="🚪 porta:", font=FS, bg=LAVENDER, fg=TEXT).pack(anchor="w", padx=10, pady=(4,0))
        ctrl_btn("🔓 abrir", MINT,
                 lambda: (self._send_command({"command":"open_door","cat":selected.get()}),
                          self.toast.show(f"Porta aberta para {selected.get()}", kind="info")))
        ctrl_btn("🔒 fechar", RED_BLOCK,
                 lambda: (self._send_command({"command":"close_door","cat":selected.get()}),
                          self.toast.show(f"Porta fechada para {selected.get()}", kind="warn")))

        tk.Label(left, text="🪟 janela:", font=FS, bg=LAVENDER, fg=TEXT).pack(anchor="w", padx=10, pady=(4,0))
        ctrl_btn("🔓 abrir", MINT,
                 lambda: (self._send_command({"command":"open_window","cat":selected.get()}),
                          self.toast.show(f"Janela aberta para {selected.get()}", kind="info")))
        ctrl_btn("🔒 fechar", RED_BLOCK,
                 lambda: (self._send_command({"command":"close_window","cat":selected.get()}),
                          self.toast.show(f"Janela fechada para {selected.get()}", kind="warn")))

        # ══════════════════════════════════════════
        # PAINEL DIREITO — monitor de sensores
        # ══════════════════════════════════════════
        right = tk.Frame(main, bg=BG)
        right.pack(side="right", fill="both", expand=True)

        # ── Configuração dos sensores ──────────────
        SENSORS = [
            ("door",    "🚪", "Porta",    PINK),
            ("window",  "🪟", "Janela",   MINT),
            ("food",    "🍽", "Comida",   PEACH),
            ("bed",     "🛏", "Cama",     LAVENDER),
            ("sandbox", "🏖", "Caixinha", YELLOW),
        ]
        # sensor_key → lista de eventos (max 50): {"ts", "cat", "msg", "action"}
        sensor_events: dict[str, list] = {s[0]: [] for s in SENSORS}

        active_sensor = tk.StringVar(value="door")

        # ── Tabs de seleção de sensor ──────────────
        tab_bar = tk.Frame(right, bg=BG)
        tab_bar.pack(fill="x", padx=10, pady=(8,0))

        _tab_btns = {}

        def _select_sensor(key):
            active_sensor.set(key)
            for k, btn in _tab_btns.items():
                cfg = next(s for s in SENSORS if s[0]==k)
                btn.config(
                    bg=cfg[3] if k==key else LGRAY,
                    fg=TEXT   if k==key else DGRAY,
                    relief="flat"
                )
            _refresh_feed()

        for s_key, s_icon, s_name, s_col in SENSORS:
            btn = tk.Button(
                tab_bar, text=f"{s_icon}  {s_name}",
                font=FB, relief="flat", cursor="hand2",
                bg=LGRAY, fg=DGRAY, padx=10, pady=6,
                command=lambda k=s_key: _select_sensor(k),
                activebackground=TEXT, activeforeground=WHITE
            )
            btn.pack(side="left", padx=3)
            _tab_btns[s_key] = btn

        # Seleciona a primeira tab visualmente
        _tab_btns["door"].config(bg=PINK, fg=TEXT)

        # ── Indicador de atividade (canvas) ───────
        indicator_frame = tk.Frame(right, bg=WHITE,
                                   highlightthickness=2, highlightbackground=BORDER)
        indicator_frame.pack(fill="x", padx=10, pady=6)

        ind_cv = tk.Canvas(indicator_frame, bg=WHITE, height=110, highlightthickness=0)
        ind_cv.pack(fill="x")

        # Estado do indicador
        _ind = {
            "active": False,   # True quando acabou de receber evento
            "pulse":  0,       # contador de frames do pulso
            "last_cat": "",    # último gato que ativou
            "last_msg": "",    # última mensagem
            "job": None,
        }

        def _draw_indicator():
            """
            Desenha o indicador de atividade do sensor selecionado.
            Quando ativo: círculo pulsante colorido + sprite do gato + nome.
            Quando inativo: círculo cinza "aguardando...".
            """
            ind_cv.delete("all")
            w = ind_cv.winfo_width() or 700
            sensor_key = active_sensor.get()
            sensor_cfg  = next(s for s in SENSORS if s[0]==sensor_key)
            s_icon, s_name, s_col = sensor_cfg[1], sensor_cfg[2], sensor_cfg[3]

            cx = w // 2

            if _ind["active"]:
                # Pulso expansivo
                p = _ind["pulse"]
                radius = 28 + int(math.sin(p * 0.25) * 10)
                alpha_r = 28 + int(math.sin(p * 0.25 + 1) * 18)

                # Anel externo (eco do pulso)
                ind_cv.create_oval(cx-alpha_r, 55-alpha_r, cx+alpha_r, 55+alpha_r,
                                   outline=s_col, width=3)
                # Círculo principal
                ind_cv.create_oval(cx-radius, 55-radius, cx+radius, 55+radius,
                                   fill=s_col, outline=BORDER, width=2)
                # Ícone do sensor no círculo
                ind_cv.create_text(cx, 55, text=s_icon,
                                   font=("Courier", 20, "bold"), fill=TEXT)

                # Sprite do gato que ativou (à esquerda)
                cat = _ind["last_cat"]
                if cat and cat in cat_data:
                    pelagem = cat_data[cat].get("pelagem", "cinza")
                    sprite_x = max(10, cx - 160)
                    _render_sprite(ind_cv, sprite_x, 20, SPR_SENTADO, pelagem, px=4, tag="ind")
                    ind_cv.create_text(sprite_x + 28, 80, text=cat.title(),
                                       font=FS, fill=TEXT, tags="ind")

                # Nome do sensor e mensagem curta (à direita)
                ind_cv.create_text(cx + 80, 42, text=f"{s_name} ativada!",
                                   font=FM, fill=TEXT, anchor="w")
                msg_short = _ind["last_msg"][:60] + ("…" if len(_ind["last_msg"]) > 60 else "")
                ind_cv.create_text(cx + 80, 62, text=msg_short,
                                   font=FS, fill=DGRAY, anchor="w", width=w - cx - 90)

                _ind["pulse"] += 1
                # Desativa o pulso após ~3 segundos (60 frames a 50ms)
                if _ind["pulse"] > 60:
                    _ind["active"] = False
                    _ind["pulse"]  = 0
            else:
                # Estado ocioso
                ind_cv.create_oval(cx-22, 33, cx+22, 77,
                                   fill=LGRAY, outline=MGRAY, width=2)
                ind_cv.create_text(cx, 55, text=s_icon,
                                   font=("Courier", 18), fill=MGRAY)
                ind_cv.create_text(cx + 34, 55, text=f"aguardando {s_name.lower()}…",
                                   font=FS, fill=DGRAY, anchor="w")

            _ind["job"] = ind_cv.after(50, _draw_indicator)

        # ── Feed de eventos (lista scrollável) ────
        feed_outer = tk.Frame(right, bg=BG)
        feed_outer.pack(fill="both", expand=True, padx=10, pady=(0,8))

        feed_header = tk.Frame(feed_outer, bg=LGRAY)
        feed_header.pack(fill="x")
        tk.Label(feed_header, text="histórico de atividade",
                 font=FB, bg=LGRAY, fg=TEXT).pack(side="left", padx=10, pady=4)
        tk.Button(feed_header, text="🗑 limpar", font=FS, bg=LGRAY, fg=DGRAY,
                  relief="flat", cursor="hand2",
                  command=lambda: (sensor_events[active_sensor.get()].clear(),
                                   _refresh_feed())
                  ).pack(side="right", padx=8)

        feed_canvas = tk.Canvas(feed_outer, bg=WHITE, highlightthickness=0)
        feed_scroll = tk.Scrollbar(feed_outer, orient="vertical",
                                   command=feed_canvas.yview)
        feed_canvas.configure(yscrollcommand=feed_scroll.set)
        feed_scroll.pack(side="right", fill="y")
        feed_canvas.pack(side="left", fill="both", expand=True)

        feed_inner = tk.Frame(feed_canvas, bg=WHITE)
        feed_win   = feed_canvas.create_window((0,0), window=feed_inner, anchor="nw")
        feed_canvas.bind("<Configure>",
                         lambda e: feed_canvas.itemconfig(feed_win, width=e.width))
        feed_inner.bind("<Configure>",
                        lambda e: feed_canvas.configure(
                            scrollregion=feed_canvas.bbox("all")))
        feed_canvas.bind_all("<MouseWheel>",
                             lambda e: feed_canvas.yview_scroll(
                                 -1*(e.delta//120), "units"))

        # Mapa de ícones por ação
        ACTION_ICON = {
            "block_door":    ("🔒", RED_BLOCK),
            "block_window":  ("🔒", RED_BLOCK),
            "block_dispenser":("🔒", RED_BLOCK),
            "reset_sandbox": ("🏥", PEACH),
            "cat_mood_check":("😿", LAVENDER),
            None:            ("●",  MINT),
        }

        def _refresh_feed():
            """Reconstrói a lista de eventos do sensor selecionado."""
            for w in feed_inner.winfo_children():
                w.destroy()

            events = sensor_events[active_sensor.get()]
            if not events:
                tk.Label(feed_inner, text="nenhum evento registrado ainda…",
                         font=FS, bg=WHITE, fg=DGRAY).pack(pady=20)
                return

            # Mais recente primeiro
            for ev in reversed(events):
                row_bg = ev.get("row_bg", WHITE)
                row = tk.Frame(feed_inner, bg=row_bg,
                               highlightthickness=1,
                               highlightbackground=LGRAY)
                row.pack(fill="x", padx=4, pady=2)

                # Ícone de ação
                icon_txt, icon_col = ACTION_ICON.get(ev.get("action"), ACTION_ICON[None])
                tk.Label(row, text=icon_txt, font=("Courier",13,"bold"),
                         bg=row_bg, fg=icon_col, width=2).pack(side="left", padx=6, pady=4)

                # Sprite do gato (mini, 3px)
                cat = ev.get("cat","")
                if cat and cat in cat_data:
                    pelagem = cat_data[cat].get("pelagem","cinza")
                    spr = tk.Canvas(row, width=45, height=42,
                                    bg=row_bg, highlightthickness=0)
                    spr.pack(side="left", padx=2)
                    _render_sprite(spr, 0, 0, SPR_SENTADO, pelagem, px=3)

                # Textos
                txt_frame = tk.Frame(row, bg=row_bg)
                txt_frame.pack(side="left", fill="x", expand=True, padx=4)

                header_txt = f"{cat.title()}" if cat else "desconhecido"
                if ev.get("action"):
                    header_txt += f"  [{ev['action']}]"
                tk.Label(txt_frame, text=header_txt,
                         font=FB, bg=row_bg, fg=TEXT,
                         anchor="w").pack(fill="x")

                msg = ev.get("msg","")
                if isinstance(msg, list): msg = " | ".join(msg)
                if msg:
                    tk.Label(txt_frame, text=msg, font=FS, bg=row_bg,
                             fg=DGRAY, anchor="w", wraplength=380,
                             justify="left").pack(fill="x")

                # Timestamp (direita)
                tk.Label(row, text=ev.get("ts",""), font=FS,
                         bg=row_bg, fg=MGRAY).pack(side="right", padx=8)

        _refresh_feed()   # inicia vazio

        # ── Hook: recebe eventos do servidor ──────
        def _on_sensor_alert(alert):
            """
            Chamado pelo _handle_alert quando chega alerta do servidor.
            Registra o evento no sensor correspondente e atualiza a UI.
            """
            sensor_key  = alert.get("sensor", "")
            if sensor_key not in sensor_events:
                return

            cat    = alert.get("cat_name", "")
            msg    = alert.get("message", "")
            action = alert.get("action")
            ts     = alert.get("timestamp","")
            if ts:
                try:
                    ts = ts[11:19]   # extrai HH:MM:SS do ISO timestamp
                except Exception:
                    pass

            # Cor de fundo da linha conforme gravidade
            if action in ("block_door","block_window","block_dispenser"):
                row_bg = "#FFE0E0"   # vermelho claro
            elif action in ("reset_sandbox","cat_mood_check"):
                row_bg = "#FFF0D0"   # laranja claro
            else:
                row_bg = WHITE

            sensor_events[sensor_key].append({
                "ts": ts, "cat": cat, "msg": msg,
                "action": action, "row_bg": row_bg,
            })
            # Mantém no máximo 50 eventos por sensor
            if len(sensor_events[sensor_key]) > 50:
                sensor_events[sensor_key].pop(0)

            # Atualiza indicador se este sensor estiver selecionado
            if sensor_key == active_sensor.get():
                _ind["active"]   = True
                _ind["pulse"]    = 0
                _ind["last_cat"] = cat
                _ind["last_msg"] = msg if isinstance(msg, str) else " | ".join(msg)
                _refresh_feed()

        # ── Atualiza info do gato selecionado ─────
        ESTADOS_ICON = {
            "dormindo":    "💤 dormindo",
            "comendo":     "🍽 comendo",
            "gordo":       "😺 ficou gordo",
            "aventureiro": "🗺 aventureiro",
        }

        def _on_cat_change(*_):
            nome = selected.get()
            info = cat_data.get(nome, {})
            estado_lbl.config(text=ESTADOS_ICON.get(info.get("estado","dormindo"),
                                                     info.get("estado","dormindo")))
            spr_left.delete("all")
            _render_sprite(spr_left, 2, 2, SPR_SENTADO, info.get("pelagem","cinza"), px=5)
            unit = "meses" if info.get("filhote") else "anos"
            extras = [x for x in ["filhote" if info.get("filhote") else "",
                                   "castrado" if info.get("castrado") else ""] if x]
            info_lbl.config(
                text=f"{nome.title()}\nraça: {info.get('raça','-')}\n"
                     f"peso: {info.get('peso','-')} kg\n"
                     f"idade: {info.get('idade','-')} {unit}"
                     + (f"\n{'  •  '.join(extras)}" if extras else ""))
            self.mascot.fur = info.get("pelagem","cinza")

        cat_combo.bind("<<ComboboxSelected>>", _on_cat_change)
        _on_cat_change()

        # Registra callbacks globais
        def _refresh_from_alert(cat_name):
            if cat_name == selected.get():
                _on_cat_change()
        self._sensor_refresh_cb  = _refresh_from_alert
        self._sensor_event_hook  = _on_sensor_alert   # novo hook de eventos

        # Inicia o indicador
        cf.after(120, _draw_indicator)
        ind_cv.bind("<Destroy>", lambda e: (
            ind_cv.after_cancel(_ind["job"]) if _ind.get("job") else None))

    def run(self):
        self.root.mainloop()

# ═══════════════════════════════════════════════
if __name__ == "__main__":
    app = CatApp(); app.run()