#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║  🐾  Cat Monitorator v2.0  ✿  nyaa~         ║
║  Sistema Distribuído de Monitoramento Felino ║
╚══════════════════════════════════════════════╝
Página única · Tela cheia · Pixel Art · Fotos
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math, os, random
import socket
import json

HOST = "127.0.0.1"
PORT_INTERFACE = 1005
interface_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def initialize_app():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT_INTERFACE))
    server_socket.listen()
    
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ═══════════════════════════════════════════════════════
#  🎨  PALETE PASTEL
# ═══════════════════════════════════════════════════════
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

FT = ("Courier", 22, "bold")
FM = ("Courier", 13, "bold")
FB = ("Courier", 11)
FS = ("Courier", 9)

# ═══════════════════════════════════════════════════════
#  📦  DADOS GLOBAIS
# ═══════════════════════════════════════════════════════
cat_data: dict = {}

# ═══════════════════════════════════════════════════════
#  🐱  PELAGENS — mapa de cores (corpo, sombra, claro)
# ═══════════════════════════════════════════════════════
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

def get_fur(pelagem: str):
    """Retorna (corpo, sombra, claro) para uma pelagem."""
    p = pelagem.lower().strip()
    for k in FUR:
        if k in p:
            return FUR[k]
    return list(FUR.values())[abs(hash(pelagem)) % len(FUR)]


# ═══════════════════════════════════════════════════════
#  🖼️  PIXEL ART — desenho de gatos no canvas
#     Sprites: 14 colunas x 13 linhas, pixels de 5px
#     B=corpo  D=sombra  L=claro  P=rosa(orelha/nariz)
#     W=branco G=iris  K=preto  T=língua  -=olho fechado
# ═══════════════════════════════════════════════════════

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

SPR_LAMBENDO = [
    "    DD  DD    ",
    "   DPPDPPD    ",
    "  DBBBBBBBD   ",
    "  DB~~BB~~D   ",
    "  DBB PP BBD  ",
    "  DBBBBBBBD   ",
    " DBBBBBBBBBD  ",
    " DBBLLLLBBD   ",
    " DBBBBBBBD    ",
    "  DBD DBBD    ",
    "   B  TTTBD   ",
    "      TTTBD   ",
    "       BD     ",
]

SPR_ANDANDO = [
    "  DD  DD      ",
    " DPPDPPD      ",
    "DBBBBBBD      ",
    "DB~~BB~~D     ",
    "DBB PP BBD    ",
    "DBBBBBBBD     ",
    "DBBBBBBBBD    ",
    "DBBLLLLBD     ",
    "DBBBBBBBD     ",
    " DBBBBBD      ",
    " DBD  DBBD    ",
    "  B    BBD    ",
    "        BD    ",
]

def _render_sprite(c, sx, sy, sprite, fur_key, px=5, tag="spr"):
    fur = FUR.get(fur_key, FUR["cinza"])
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
            fill = cmap.get(ch, "#FF00FF")
            x1, y1 = sx + col * px, sy + r * px
            c.create_rectangle(x1, y1, x1+px, y1+px,
                                fill=fill, outline='', tags=tag)


# ═══════════════════════════════════════════════════════
#  🐾  MASCOTE GATINHO — acompanha cursor ou faz pose
# ═══════════════════════════════════════════════════════
class MascotCat:
    SIZE = 110

    def __init__(self, root, host):
        self.root = root
        self.frame_n = 0
        self.idle = 0
        self.mode = "follow"   # follow | lick | sleep
        self.mx = 400
        self.my = 300
        self.fur = "cinza"
        self._job = None

        self.cv = tk.Canvas(host, width=self.SIZE, height=self.SIZE,
                            bg=BG, highlightthickness=0, cursor="none")
        self.cv.place(relx=1.0, rely=1.0, anchor="se", x=-12, y=-12)

        host.bind("<Motion>", self._motion, add="+")
        self._tick()

    def reattach(self, host):
        """Move mascot to a new host widget."""
        try:
            self.cv.place_forget()
            self.cv.place(in_=host, relx=1.0, rely=1.0, anchor="se", x=-12, y=-12)
        except Exception:
            pass
        host.bind("<Motion>", self._motion, add="+")

    def _motion(self, e):
        self.mx = e.x_root
        self.my = e.y_root
        self.idle = 0
        if self.mode != "follow":
            self.mode = "follow"

    def _tick(self):
        self.frame_n += 1
        self.idle += 1
        if self.idle > 220:
            self.mode = random.choice(["lick", "sleep"])
            self.idle = 0
        self._draw()
        try:
            self._job = self.root.after(50, self._tick)
        except Exception:
            pass

    def _draw(self):
        c = self.cv
        c.delete("all")
        c.create_rectangle(0, 0, self.SIZE, self.SIZE, fill=BG, outline='')
        {
            "sleep": self._draw_sleep,
            "lick":  self._draw_lick,
            "follow": self._draw_follow,
        }[self.mode]()

    # ── poses do mascote ─────────────────────────────
    def _draw_sleep(self):
        c, f = self.cv, self.frame_n
        fur = FUR.get(self.fur, FUR["cinza"])
        body, dark, light = fur

        # corpo enrolado
        c.create_oval(8, 50, 72, 90, fill=body, outline=dark, width=2)
        c.create_oval(30, 30, 78, 68, fill=body, outline=dark, width=2)
        # orelhas
        c.create_polygon(32,35, 24,18, 42,32, fill=body, outline=dark)
        c.create_polygon(60,35, 70,18, 55,32, fill=body, outline=dark)
        c.create_polygon(33,34, 27,21, 40,31, fill="#FF9EB5", outline='')
        c.create_polygon(59,34, 67,21, 54,31, fill="#FF9EB5", outline='')
        # olhos fechados
        c.create_line(40, 47, 50, 44, fill=dark, width=2)
        c.create_line(56, 44, 66, 47, fill=dark, width=2)
        # nariz
        c.create_oval(51, 50, 57, 55, fill="#FF9EB5", outline='')
        # rabo
        rx = int(math.sin(f * 0.06) * 6)
        c.create_arc(2, 55, 28, 95, start=160+rx, extent=160,
                     style="arc", outline=dark, width=3)
        # ZZZs
        for i, z in enumerate("zZz"):
            yo = (f * 2 + i * 14) % 40
            c.create_text(80, 30 - yo, text=z,
                          font=("Courier", 7+i*2, "bold"),
                          fill=LAVENDER)

    def _draw_lick(self):
        c, f = self.cv, self.frame_n
        fur = FUR.get(self.fur, FUR["cinza"])
        body, dark, light = fur

        paw_y = int(72 + math.sin(f * 0.25) * 8)
        # corpo
        c.create_oval(18, 40, 85, 96, fill=body, outline=dark, width=2)
        c.create_oval(22, 40, 80, 80, fill=light, outline='')
        # cabeça
        c.create_oval(20, 8, 82, 58, fill=body, outline=dark, width=2)
        # orelhas
        c.create_polygon(24,14, 16,0, 37,12, fill=body, outline=dark)
        c.create_polygon(68,14, 78,0, 57,12, fill=body, outline=dark)
        c.create_polygon(25,13, 19,3, 35,11, fill="#FF9EB5", outline='')
        c.create_polygon(67,13, 75,3, 56,11, fill="#FF9EB5", outline='')
        # olhos semicerrados
        c.create_arc(30, 26, 46, 40, start=0, extent=180,
                     style='chord', fill=dark, outline='')
        c.create_arc(54, 26, 70, 40, start=0, extent=180,
                     style='chord', fill=dark, outline='')
        # nariz
        c.create_oval(47, 44, 54, 50, fill="#FF9EB5", outline='')
        # patinha levantada
        c.create_oval(14, paw_y-12, 36, paw_y+8, fill=body, outline=dark, width=2)
        # língua lambendo
        if f % 14 < 7:
            c.create_oval(18, paw_y-18, 32, paw_y-6,
                          fill="#FF4477", outline='')

    def _draw_follow(self):
        c, f = self.cv, self.frame_n
        fur = FUR.get(self.fur, FUR["cinza"])
        body, dark, light = fur

        # direção do olhar
        try:
            cx = c.winfo_rootx() + self.SIZE // 2
            cy = c.winfo_rooty() + self.SIZE // 2
            a = math.atan2(self.my - cy, self.mx - cx)
            ex = int(math.cos(a) * 3)
            ey = int(math.sin(a) * 3)
        except Exception:
            ex, ey = 0, 0

        bob = int(math.sin(f * 0.12) * 2)

        # corpo
        c.create_oval(16, 46+bob, 90, 100+bob, fill=body, outline=dark, width=2)
        c.create_oval(28, 52+bob, 78, 90+bob, fill=light, outline='')
        # cabeça
        c.create_oval(18, 6+bob, 88, 56+bob, fill=body, outline=dark, width=2)
        # orelhas
        c.create_polygon(22,14+bob, 12,0+bob, 38,12+bob, fill=body, outline=dark)
        c.create_polygon(82,14+bob, 94,0+bob, 68,12+bob, fill=body, outline=dark)
        c.create_polygon(23,13+bob, 16,3+bob, 36,11+bob, fill="#FF9EB5", outline='')
        c.create_polygon(81,13+bob, 90,3+bob, 67,11+bob, fill="#FF9EB5", outline='')
        # olhos rastreando cursor
        for bx in (36, 70):
            c.create_oval(bx-9, 22+bob, bx+9, 38+bob,
                          fill=WHITE, outline=dark, width=1)
            c.create_oval(bx+ex-5, 27+bob+ey, bx+ex+5, 37+bob+ey,
                          fill="#44BB88", outline='')
            c.create_oval(bx+ex-2, 29+bob+ey, bx+ex+2, 35+bob+ey,
                          fill=dark, outline='')
        # nariz
        c.create_oval(49, 41+bob, 57, 47+bob, fill="#FF9EB5", outline='')
        # bigodes
        for x1,y1,x2,y2 in [(16,35+bob,34,33+bob),(16,39+bob,34,39+bob),
                              (72,33+bob,90,35+bob),(72,39+bob,90,39+bob)]:
            c.create_line(x1,y1,x2,y2, fill=dark, width=1)
        # rabo
        tw = int(math.sin(f * 0.18) * 10)
        c.create_arc(0, 62, 32, 100, start=170+tw, extent=180,
                     style="arc", outline=dark, width=4)


# ═══════════════════════════════════════════════════════
#  🖱️  HELPERS DE WIDGET
# ═══════════════════════════════════════════════════════
def px_btn(parent, text, cmd, bg=PINK, fg=TEXT, w=26, pady=10):
    outer = tk.Frame(parent, bg=TEXT, padx=2, pady=2)
    tk.Button(
        outer, text=text, command=cmd,
        bg=bg, fg=fg, font=FM, relief="flat", bd=0,
        width=w, padx=12, pady=pady, cursor="hand2",
        activebackground=TEXT, activeforeground=WHITE
    ).pack()
    return outer

def px_entry(parent, var, w=20):
    return tk.Entry(
        parent, textvariable=var, font=FB,
        bg=WHITE, fg=TEXT, relief="flat", width=w,
        highlightthickness=2,
        highlightbackground=BORDER,
        highlightcolor=DPINK
    )

def section_header(parent, title, sub="", bg=PINK):
    f = tk.Frame(parent, bg=bg)
    f.pack(fill="x")
    tk.Label(f, text=title, font=FT, bg=bg, fg=TEXT).pack(pady=(14,3))
    if sub:
        tk.Label(f, text=sub, font=FB, bg=bg, fg=TEXT).pack(pady=(0,10))
    tk.Frame(parent, bg=DPINK, height=3).pack(fill="x")
    return f


# ═══════════════════════════════════════════════════════
#  📷  FOTO — resize e cache PIL
# ═══════════════════════════════════════════════════════
_photo_cache: dict = {}   # path -> ImageTk.PhotoImage

def load_photo(path, size=(100, 100)):
    """Carrega e redimensiona uma foto usando PIL."""
    key = (path, size)
    if key in _photo_cache:
        return _photo_cache[key]
    if not PIL_AVAILABLE or not path or not os.path.exists(path):
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
        # centraliza em fundo branco
        canvas_img = Image.new("RGBA", size, (255, 255, 255, 255))
        ox = (size[0] - img.width) // 2
        oy = (size[1] - img.height) // 2
        canvas_img.paste(img, (ox, oy), img)
        tk_img = ImageTk.PhotoImage(canvas_img)
        _photo_cache[key] = tk_img
        return tk_img
    except Exception:
        return None


# ═══════════════════════════════════════════════════════
#  🎮  ANIMAÇÕES DO PAINEL DE SENSORES
#     (gatos grandes animados baseados no estado)
# ═══════════════════════════════════════════════════════
def _fur_or(pelagem):
    return get_fur(pelagem) if pelagem else FUR["cinza"]

def draw_cat_dormindo(c, cx, cy, f, pelagem="cinza"):
    body, dark, light = _fur_or(pelagem)
    c.delete("cat")
    # sombra
    c.create_oval(cx-65, cy+55, cx+65, cy+75, fill="#E8D8E8", outline='', tags="cat")
    # corpo enrolado
    c.create_oval(cx-65, cy-20, cx+65, cy+60, fill=body, outline=dark, width=2, tags="cat")
    c.create_oval(cx-50, cy-15, cx+50, cy+45, fill=light, outline='', tags="cat")
    # cabeça
    c.create_oval(cx+10, cy-70, cx+90, cy+10, fill=body, outline=dark, width=2, tags="cat")
    # orelhas
    c.create_polygon(cx+15,cy-65, cx+8,cy-90, cx+30,cy-62, fill=body, outline=dark, tags="cat")
    c.create_polygon(cx+72,cy-65, cx+82,cy-90, cx+60,cy-62, fill=body, outline=dark, tags="cat")
    c.create_polygon(cx+17,cy-64, cx+12,cy-84, cx+29,cy-61, fill="#FF9EB5", outline='', tags="cat")
    c.create_polygon(cx+71,cy-64, cx+78,cy-84, cx+61,cy-61, fill="#FF9EB5", outline='', tags="cat")
    # olhos fechados
    c.create_line(cx+28,cy-35, cx+42,cy-38, fill=dark, width=3, tags="cat")
    c.create_line(cx+52,cy-38, cx+66,cy-35, fill=dark, width=3, tags="cat")
    # nariz
    c.create_oval(cx+46,cy-22, cx+54,cy-16, fill="#FF9EB5", outline='', tags="cat")
    # rabo
    rx = int(math.sin(f * 0.06) * 10)
    c.create_arc(cx-100, cy+10, cx-20, cy+80,
                 start=130+rx, extent=140, style="arc",
                 outline=dark, width=5, tags="cat")
    # ZZZ flutuantes
    for i, z in enumerate("zZZ"):
        yo = (f * 2 + i * 20) % 70
        sz = 9 + i * 3
        c.create_text(cx+105, cy-50-yo, text=z,
                      font=("Courier", sz, "bold"), fill=LAVENDER, tags="cat")

def draw_cat_comendo(c, cx, cy, f, pelagem="cinza"):
    body, dark, light = _fur_or(pelagem)
    c.delete("cat")
    # sombra
    c.create_oval(cx-55, cy+65, cx+55, cy+80, fill="#E8D8E8", outline='', tags="cat")
    # tigela
    c.create_arc(cx-40, cy+40, cx+40, cy+80, start=180, extent=180,
                 fill=PEACH, outline=BORDER, width=2, style='chord', tags="cat")
    c.create_oval(cx-42, cy+40, cx+42, cy+55, fill=BORDER, outline='', tags="cat")
    # comida na tigela
    for i in range(5):
        bx = cx - 20 + i * 10
        c.create_oval(bx-4, cy+44, bx+4, cy+52, fill=DPINK, outline='', tags="cat")
    # corpo
    c.create_oval(cx-45, cy-25, cx+45, cy+65, fill=body, outline=dark, width=2, tags="cat")
    c.create_oval(cx-35, cy-20, cx+35, cy+50, fill=light, outline='', tags="cat")
    # cabeça inclinada
    c.create_oval(cx-35, cy-95, cx+35, cy-25, fill=body, outline=dark, width=2, tags="cat")
    # orelhas
    c.create_polygon(cx-30,cy-90, cx-42,cy-112, cx-14,cy-88, fill=body, outline=dark, tags="cat")
    c.create_polygon(cx+30,cy-90, cx+42,cy-112, cx+14,cy-88, fill=body, outline=dark, tags="cat")
    c.create_polygon(cx-29,cy-89, cx-39,cy-108, cx-15,cy-87, fill="#FF9EB5", outline='', tags="cat")
    c.create_polygon(cx+29,cy-89, cx+39,cy-108, cx+15,cy-87, fill="#FF9EB5", outline='', tags="cat")
    # olhos
    for ox in (-12, 12):
        c.create_oval(cx+ox-8, cy-72, cx+ox+8, cy-56,
                      fill=WHITE, outline=dark, width=1, tags="cat")
        c.create_oval(cx+ox-4, cy-68, cx+ox+4, cy-60,
                      fill="#44BB88", outline='', tags="cat")
        c.create_oval(cx+ox-2, cy-67, cx+ox+2, cy-61,
                      fill=dark, outline='', tags="cat")
    # língua animada
    t = f % 20
    ty = cy - 40 + (4 if t < 10 else 0)
    c.create_oval(cx-8, ty, cx+8, ty+14, fill="#FF4477", outline='', tags="cat")
    # partículas de comida
    for i in range(4):
        px = cx + random.randint(-30, 30)
        py = cy + 30 - (f * 3 + i * 15) % 50
        c.create_oval(px-3, py-3, px+3, py+3, fill=GOLD, outline='', tags="cat")
    # coraçõezinhos
    for i in range(2):
        hx = cx + 50 + i * 20
        hy = cy - 70 - (f * 2 + i * 25) % 50
        c.create_text(hx, hy, text="♥", font=("Courier",12,"bold"),
                      fill=DPINK, tags="cat")

def draw_cat_gordo(c, cx, cy, f, pelagem="cinza"):
    body, dark, light = _fur_or(pelagem)
    c.delete("cat")
    # sombra grande
    c.create_oval(cx-75, cy+55, cx+75, cy+80, fill="#E8D8E8", outline='', tags="cat")
    # corpo bem redondo
    c.create_oval(cx-75, cy-50, cx+75, cy+70, fill=body, outline=dark, width=3, tags="cat")
    c.create_oval(cx-60, cy-40, cx+60, cy+55, fill=light, outline='', tags="cat")
    # cabeça grande
    c.create_oval(cx-45, cy-115, cx+45, cy-30, fill=body, outline=dark, width=2, tags="cat")
    # bochechas
    c.create_oval(cx-50, cy-80, cx-20, cy-55, fill="#FFD0D8", outline='', tags="cat")
    c.create_oval(cx+20, cy-80, cx+50, cy-55, fill="#FFD0D8", outline='', tags="cat")
    # orelhas
    c.create_polygon(cx-40,cy-110, cx-55,cy-132, cx-20,cy-108, fill=body, outline=dark, tags="cat")
    c.create_polygon(cx+40,cy-110, cx+55,cy-132, cx+20,cy-108, fill=body, outline=dark, tags="cat")
    c.create_polygon(cx-39,cy-109, cx-51,cy-128, cx-21,cy-107, fill="#FF9EB5", outline='', tags="cat")
    c.create_polygon(cx+39,cy-109, cx+51,cy-128, cx+21,cy-107, fill="#FF9EB5", outline='', tags="cat")
    # olhos semiadormecidos
    for ox in (-15, 15):
        c.create_oval(cx+ox-9, cy-90, cx+ox+9, cy-74,
                      fill=WHITE, outline=dark, width=1, tags="cat")
        c.create_arc(cx+ox-9, cy-90, cx+ox+9, cy-74,
                     start=0, extent=180, style='chord',
                     fill=dark, outline='', tags="cat")
    # nariz
    c.create_oval(cx-6, cy-68, cx+6, cy-62, fill="#FF9EB5", outline='', tags="cat")
    # patinhas pequenas
    for pox in (-55, 45):
        c.create_oval(cx+pox, cy+20, cx+pox+25, cy+45,
                      fill=body, outline=dark, width=2, tags="cat")
    # estrelinhas orbitando
    for i in range(4):
        a = math.radians(f * 4 + i * 90)
        sx = cx + int(math.cos(a) * 90)
        sy = cy + int(math.sin(a) * 40) - 20
        pts = []
        for j in range(5):
            ra = math.radians(-90 + j * 72 * 2 + f * 4)
            rb = math.radians(-90 + (j * 2 + 1) * 36 + f * 4)
            pts += [sx + int(math.cos(ra)*9), sy + int(math.sin(ra)*9)]
            pts += [sx + int(math.cos(rb)*4), sy + int(math.sin(rb)*4)]
        c.create_polygon(pts, fill=GOLD, outline='', tags="cat")
    # migalhas no chão
    for i in range(6):
        gx = cx - 60 + i * 22
        c.create_oval(gx, cy+68, gx+5, cy+74, fill=PEACH, outline='', tags="cat")

def draw_cat_aventureiro(c, cx, cy, f, pelagem="cinza"):
    body, dark, light = _fur_or(pelagem)
    c.delete("cat")
    # sombra
    c.create_oval(cx-50, cy+65, cx+50, cy+78, fill="#E8D8E8", outline='', tags="cat")
    # bobbing vertical
    bob = int(math.sin(f * 0.22) * 5)
    # rabo em arco para cima
    tw = int(math.sin(f * 0.15) * 12)
    c.create_arc(cx+30, cy-30+bob, cx+90, cy+50+bob,
                 start=60+tw, extent=200, style="arc",
                 outline=dark, width=5, tags="cat")
    # corpo
    c.create_oval(cx-42, cy-10+bob, cx+42, cy+70+bob, fill=body, outline=dark, width=2, tags="cat")
    c.create_oval(cx-32, cy-5+bob, cx+32, cy+60+bob, fill=light, outline='', tags="cat")
    # bandana vermelha
    c.create_rectangle(cx-42, cy+8+bob, cx+42, cy+22+bob,
                       fill="#FF4444", outline="#CC2222", width=1, tags="cat")
    c.create_polygon(cx+42, cy+8+bob, cx+42, cy+22+bob, cx+58, cy+15+bob,
                     fill="#FF4444", outline='', tags="cat")
    # cabeça
    c.create_oval(cx-35, cy-90+bob, cx+35, cy-20+bob, fill=body, outline=dark, width=2, tags="cat")
    # orelhas
    c.create_polygon(cx-30,cy-85+bob, cx-44,cy-108+bob, cx-12,cy-83+bob,
                     fill=body, outline=dark, tags="cat")
    c.create_polygon(cx+30,cy-85+bob, cx+44,cy-108+bob, cx+12,cy-83+bob,
                     fill=body, outline=dark, tags="cat")
    c.create_polygon(cx-29,cy-84+bob, cx-40,cy-104+bob, cx-13,cy-82+bob,
                     fill="#FF9EB5", outline='', tags="cat")
    c.create_polygon(cx+29,cy-84+bob, cx+40,cy-104+bob, cx+13,cy-82+bob,
                     fill="#FF9EB5", outline='', tags="cat")
    # olhos atentos
    for ox in (-12, 12):
        c.create_oval(cx+ox-9, cy-68+bob, cx+ox+9, cy-50+bob,
                      fill=WHITE, outline=dark, width=1, tags="cat")
        c.create_oval(cx+ox-5, cy-65+bob, cx+ox+5, cy-55+bob,
                      fill="#44BB88", outline='', tags="cat")
        c.create_oval(cx+ox-2, cy-63+bob, cx+ox+2, cy-57+bob,
                      fill=dark, outline='', tags="cat")
    # nariz
    c.create_oval(cx-5, cy-44+bob, cx+5, cy-38+bob, fill="#FF9EB5", outline='', tags="cat")
    # pernas andando
    for i, (ox, phase) in enumerate([(-22, 0), (-8, math.pi), (8, math.pi), (22, 0)]):
        leg_y = int(math.sin(f * 0.3 + phase) * 12)
        c.create_oval(cx+ox-8, cy+50+bob+leg_y, cx+ox+8, cy+72+bob+leg_y,
                      fill=body, outline=dark, width=1, tags="cat")
    # rastros de patinha
    for i in range(3):
        px = cx - 80 - i * 28
        py = cy + 75 + (i % 2) * 12
        alpha_colors = [LGRAY, MGRAY, DGRAY]
        c.create_oval(px-8, py-8, px+8, py+8, fill=alpha_colors[i], outline='', tags="cat")
        for j in range(3):
            ta = math.radians(j * 120 - 60)
            c.create_oval(px+int(math.cos(ta)*9)-4, py+int(math.sin(ta)*9)-4,
                          px+int(math.cos(ta)*9)+4, py+int(math.sin(ta)*9)+4,
                          fill=alpha_colors[i], outline='', tags="cat")


# ═══════════════════════════════════════════════════════
#  🏠  APLICATIVO PRINCIPAL — single-page navigation
# ═══════════════════════════════════════════════════════
class CatApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🐾 Cat Monitorator")
        self.root.configure(bg=BG)
        self.root.geometry("1024x768")
        self._fullscreen = False

        # Stack de páginas: lista de (título, builder_fn, *args)
        self._stack: list = []

        # Barra superior fixa
        self._topbar = tk.Frame(self.root, bg=BORDER, height=3)
        self._topbar.pack(fill="x", side="top")

        self._navbar = tk.Frame(self.root, bg=LAVENDER, pady=6)
        self._navbar.pack(fill="x", side="top")
        self._back_btn = tk.Button(
            self._navbar, text="◀  voltar", font=FB,
            bg=LAVENDER, fg=TEXT, relief="flat", bd=0,
            cursor="hand2", command=self._pop,
            activebackground=PINK
        )
        self._back_btn.pack(side="left", padx=14)
        self._crumb_lbl = tk.Label(self._navbar, text="", font=FB,
                                   bg=LAVENDER, fg=TEXT)
        self._crumb_lbl.pack(side="left", padx=4)
        # botão fullscreen
        tk.Button(
            self._navbar, text="⛶  tela cheia", font=FS,
            bg=LAVENDER, fg=TEXT, relief="flat", bd=0,
            cursor="hand2", command=self._toggle_fs,
            activebackground=PINK
        ).pack(side="right", padx=14)

        # Área de conteúdo principal
        self._content = tk.Frame(self.root, bg=BG)
        self._content.pack(fill="both", expand=True)

        # Mascote — persistente em toda a sessão
        self.mascot = MascotCat(self.root, self._content)

        # Atalho teclado
        self.root.bind("<F11>", lambda e: self._toggle_fs())
        self.root.bind("<Escape>", lambda e: self._exit_fs())

        # Inicia na página principal
        self._push("🏠  início", self._page_main)

    # ── Navegação ─────────────────────────────────────
    def _push(self, title, builder, *args):
        self._stack.append((title, builder, args))
        self._render()

    def _pop(self):
        if len(self._stack) > 1:
            self._stack.pop()
            self._render()

    def _render(self):
        # Limpa conteúdo atual
        for w in self._content.winfo_children():
            if w is not self.mascot.cv:
                w.destroy()

        title, builder, args = self._stack[-1]

        # Atualiza breadcrumb
        crumb = " › ".join(t for t, _, _ in self._stack)
        self._crumb_lbl.config(text=crumb)

        # Exibe / oculta botão voltar
        if len(self._stack) > 1:
            self._back_btn.pack(side="left", padx=14)
        else:
            self._back_btn.pack_forget()

        # Constrói página
        builder(*args)

        # Reposiciona mascote sobre o novo conteúdo
        try:
            self.mascot.cv.tkraise()
        except Exception:
            pass
        self.mascot.cv.place(in_=self._content,
                             relx=1.0, rely=1.0, anchor="se", x=-12, y=-12)

    def _toggle_fs(self):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    def _exit_fs(self):
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes("-fullscreen", False)

    # ── Decorações de fundo ───────────────────────────
    def _bg_decor(self, canvas, w, h):
        """Desenha patadinhas e estrelinhas decorativas no fundo."""
        random.seed(42)
        for _ in range(14):
            px = random.randint(20, w-20)
            py = random.randint(20, h-20)
            a = random.uniform(0, 360)
            col = random.choice([PINK, MINT, PEACH, LAVENDER])
            # patinha
            canvas.create_oval(px-8, py-8, px+8, py+8,
                                fill=col, outline='', stipple='gray25')
            for j in range(3):
                ta = math.radians(a + j * 120)
                canvas.create_oval(
                    px+int(math.cos(ta)*11)-4, py+int(math.sin(ta)*11)-4,
                    px+int(math.cos(ta)*11)+4, py+int(math.sin(ta)*11)+4,
                    fill=col, outline='', stipple='gray25'
                )

    # ══════════════════════════════════════════════════
    #  📄  PÁGINAS
    # ══════════════════════════════════════════════════

    # ── Página Principal ─────────────────────────────
    def _page_main(self):
        cf = self._content

        # Canvas decorativo de fundo
        bg_cv = tk.Canvas(cf, bg=BG, highlightthickness=0)
        bg_cv.pack(fill="both", expand=True)

        def _resize(e):
            bg_cv.delete("decor")
            w, h = e.width, e.height
            # patadinhas decorativas
            random.seed(7)
            for _ in range(18):
                px = random.randint(20, w-20)
                py = random.randint(20, h-20)
                col = random.choice([PINK+"88", MINT+"88", PEACH+"88", LAVENDER+"88"])
                bg_cv.create_oval(px-10, py-10, px+10, py+10,
                                  fill=LGRAY, outline='', tags="decor")
            # sprites pequenos nos cantos
            for sx, sy, spr in [(20, 80, SPR_SENTADO), (0, 150, SPR_DORMINDO)]:
                _render_sprite(bg_cv, sx, sy, spr, "cinza", px=3, tag="decor")

        bg_cv.bind("<Configure>", _resize)

        # Frame central (sobre o canvas)
        center = tk.Frame(bg_cv, bg=BG)
        bg_cv.create_window(512, 384, window=center, anchor="center")

        # Título
        tk.Label(center, text="🐾  Cat Monitorator",
                 font=("Courier", 28, "bold"), bg=BG, fg=TEXT).pack(pady=(0, 4))
        tk.Label(center,
                 text="sistema distribuído de monitoramento felino",
                 font=FB, bg=BG, fg=DGRAY).pack()
        tk.Frame(center, bg=DPINK, height=3, width=400).pack(pady=12)

        # Grid de botões 2x3
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
            btn = px_btn(grid, lbl, cmd, bg=bg_c, w=22, pady=12)
            btn.grid(row=r, column=col, padx=10, pady=8)

        # aviso
        tk.Label(center,
                 text="⚠  este sistema não substitui a atenção presencial ao seu gatinho!",
                 font=FS, bg=BG, fg=DGRAY, wraplength=480).pack(pady=16)

    def _goto_register(self):
        self._push("🐱  cadastrar", self._page_register)

    def _goto_view(self):
        self._push("📋  ver gatinhos", self._page_view)

    def _goto_edit(self):
        self._push("✏️  editar", self._page_edit)

    def _goto_delete(self):
        self._push("🗑️  excluir", self._page_delete)

    def _goto_sensor(self):
        self._push("📡  sensores", self._page_sensor)

    # ── Cadastrar ────────────────────────────────────
    def _page_register(self):
        cf = self._content

        section_header(cf, "🐱  cadastrar gatinho",
                       "preencha os dados do seu novo amiguinho ♡", PINK)

        body = tk.Frame(cf, bg=BG)
        body.pack(fill="both", expand=True, padx=40, pady=20)

        # Formulário esquerda + foto direita
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(body, bg=BG, width=220)
        right.pack(side="right", fill="y", padx=(20, 0))
        right.pack_propagate(False)

        # variáveis do form
        v = {k: tk.StringVar() for k in
             ["nome", "raça", "peso", "idade"]}
        pelagem_var = tk.StringVar(value=FUR_OPTIONS[0])
        filhote_var = tk.BooleanVar()
        castrado_var = tk.BooleanVar()
        photo_path = tk.StringVar()

        def field(parent, label, var, hint=""):
            row = tk.Frame(parent, bg=BG)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=label, font=FB, bg=BG, fg=TEXT,
                     width=16, anchor="w").pack(side="left")
            e = px_entry(row, var, w=22)
            e.pack(side="left")
            if hint:
                tk.Label(row, text=hint, font=FS, bg=BG, fg=DGRAY).pack(side="left", padx=6)

        field(left, "nome:", v["nome"])
        field(left, "raça:", v["raça"])
        field(left, "peso (kg):", v["peso"], "ex: 4.2")
        field(left, "idade:", v["idade"], "anos ou meses")

        # pelagem (combobox)
        prow = tk.Frame(left, bg=BG)
        prow.pack(fill="x", pady=5)
        tk.Label(prow, text="pelagem:", font=FB, bg=BG, fg=TEXT,
                 width=16, anchor="w").pack(side="left")
        combo = ttk.Combobox(prow, textvariable=pelagem_var,
                             values=FUR_OPTIONS, state="readonly",
                             font=FB, width=18)
        combo.pack(side="left")

        # preview do sprite ao lado do combo
        spr_cv = tk.Canvas(prow, width=80, height=70, bg=BG, highlightthickness=0)
        spr_cv.pack(side="left", padx=10)

        def update_preview(*_):
            spr_cv.delete("all")
            _render_sprite(spr_cv, 0, 0, SPR_SENTADO, pelagem_var.get(), px=5, tag="all")

        combo.bind("<<ComboboxSelected>>", update_preview)
        update_preview()

        # checkboxes
        ck_row = tk.Frame(left, bg=BG)
        ck_row.pack(fill="x", pady=8)
        tk.Checkbutton(ck_row, text="é filhote?", variable=filhote_var,
                       font=FB, bg=BG, fg=TEXT,
                       activebackground=BG, selectcolor=PINK).pack(side="left", padx=10)
        tk.Checkbutton(ck_row, text="é castrado?", variable=castrado_var,
                       font=FB, bg=BG, fg=TEXT,
                       activebackground=BG, selectcolor=MINT).pack(side="left", padx=10)

        # ── Área de foto (direita) ─────────────────
        tk.Label(right, text="📷  foto do gatinho",
                 font=FM, bg=BG, fg=TEXT).pack(pady=(10, 6))
        tk.Label(right, text="(opcional)", font=FS, bg=BG, fg=DGRAY).pack()

        photo_cv = tk.Canvas(right, width=160, height=160, bg=LGRAY,
                             highlightthickness=2,
                             highlightbackground=BORDER)
        photo_cv.pack(pady=8)
        photo_cv.create_text(80, 72, text="nenhuma foto\nselecionada",
                             font=FS, fill=DGRAY, justify="center")

        _photo_ref = [None]  # manter referência PIL

        def _open_gallery():
            path = filedialog.askopenfilename(
                title="Selecionar foto",
                filetypes=[
                    ("Imagens", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
                    ("Todos", "*.*")
                ]
            )
            if path:
                photo_path.set(path)
                img = load_photo(path, (156, 156))
                if img:
                    _photo_ref[0] = img
                    photo_cv.delete("all")
                    photo_cv.create_image(2, 2, image=img, anchor="nw")
                else:
                    photo_cv.delete("all")
                    photo_cv.create_text(80, 72, text="erro ao\ncarregar",
                                         font=FS, fill="#CC4444", justify="center")

        def _clear_photo():
            photo_path.set("")
            _photo_ref[0] = None
            photo_cv.delete("all")
            photo_cv.create_text(80, 72, text="nenhuma foto\nselecionada",
                                 font=FS, fill=DGRAY, justify="center")

        px_btn(right, "🖼  da galeria", _open_gallery, bg=PEACH, w=16, pady=6).pack(pady=4)
        if not PIL_AVAILABLE:
            tk.Label(right, text="instale Pillow\npara fotos", font=FS,
                     bg=BG, fg=DGRAY).pack()
        px_btn(right, "✕  remover", _clear_photo, bg=LGRAY, fg=DGRAY, w=16, pady=4).pack(pady=2)

        # ── Botão salvar ─────────────────────────
        def _save():
            nome = v["nome"].get().strip().lower()
            if not nome:
                messagebox.showwarning("ops!", "o gatinho precisa de um nome ♡")
                return
            if nome in cat_data:
                if not messagebox.askyesno("já existe",
                                           f"'{nome}' já está cadastrado. deseja sobrescrever?"):
                    return
            try:
                peso = float(v["peso"].get())
            except ValueError:
                messagebox.showwarning("ops!", "peso deve ser um número. ex: 4.2")
                return
            try:
                idade = int(v["idade"].get())
            except ValueError:
                messagebox.showwarning("ops!", "idade deve ser um número inteiro")
                return

            cat_data[nome] = {
                "raça":     v["raça"].get().strip(),
                "pelagem":  pelagem_var.get(),
                "peso":     peso,
                "idade":    idade,
                "filhote":  filhote_var.get(),
                "castrado": castrado_var.get(),
                "estado":   "dormindo",
                "foto":     photo_path.get(),
            }
            messagebox.showinfo("nyaa~", f"gatinho '{nome}' cadastrado com sucesso! 🐾")
            self._pop()

        save_row = tk.Frame(cf, bg=BG)
        save_row.pack(pady=12)
        px_btn(save_row, "💾  salvar gatinho", _save, bg=MINT, w=28, pady=12).pack()

    # ── Ver Gatinhos ─────────────────────────────────
    def _page_view(self):
        cf = self._content
        section_header(cf, "📋  gatinhos cadastrados",
                       f"{len(cat_data)} gatinho(s) no sistema ♡", MINT)

        outer = tk.Frame(cf, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=10)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _on_resize)

        def _update_scroll(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _update_scroll)

        canvas.bind_all("<MouseWheel>", lambda e:
                        canvas.yview_scroll(-1*(e.delta//120), "units"))

        if not cat_data:
            tk.Label(inner, text="nenhum gatinho cadastrado ainda...\n(｡•́︿•̀｡)",
                     font=FM, bg=BG, fg=DGRAY).pack(pady=60)
            return

        colors = [PINK, MINT, PEACH, LAVENDER, YELLOW]
        estados_icon = {
            "dormindo":    "💤",
            "comendo":     "🍽",
            "gordo":       "🔴",
            "aventureiro": "🗺",
        }

        for i, (nome, info) in enumerate(cat_data.items()):
            bg_c = colors[i % len(colors)]
            card = tk.Frame(inner, bg=bg_c, relief="flat",
                            highlightthickness=2, highlightbackground=BORDER)
            card.pack(fill="x", padx=12, pady=6)

            # sprite pixel art do gato
            spr_cv = tk.Canvas(card, width=72, height=68,
                               bg=bg_c, highlightthickness=0)
            spr_cv.pack(side="left", padx=10, pady=8)
            _render_sprite(spr_cv, 1, 1, SPR_SENTADO, info.get("pelagem","cinza"),
                           px=5, tag="s")

            # info
            info_frame = tk.Frame(card, bg=bg_c)
            info_frame.pack(side="left", fill="both", expand=True, pady=8)

            tk.Label(info_frame,
                     text=f"{estados_icon.get(info.get('estado','dormindo'),'💤')}  {nome.title()}",
                     font=FM, bg=bg_c, fg=TEXT).pack(anchor="w")

            details = (
                f"raça: {info.get('raça','-')}  •  "
                f"pelagem: {info.get('pelagem','-')}  •  "
                f"peso: {info.get('peso','-')} kg"
            )
            tk.Label(info_frame, text=details,
                     font=FS, bg=bg_c, fg=TEXT).pack(anchor="w")

            extras = []
            if info.get("filhote"):  extras.append("filhote")
            if info.get("castrado"): extras.append("castrado")
            if extras:
                tk.Label(info_frame, text="  •  ".join(extras),
                         font=FS, bg=bg_c, fg=DGRAY).pack(anchor="w")

            # foto thumbnail se existir
            if info.get("foto"):
                img = load_photo(info["foto"], (60, 60))
                if img:
                    lbl = tk.Label(card, image=img, bg=bg_c)
                    lbl.image = img
                    lbl.pack(side="right", padx=10, pady=8)

    # ── Editar ────────────────────────────────────────
    def _page_edit(self):
        cf = self._content
        section_header(cf, "✏️  editar gatinho",
                       "selecione e atualize os dados ♡", PEACH)

        body = tk.Frame(cf, bg=BG)
        body.pack(fill="both", expand=True, padx=50, pady=20)

        selected = tk.StringVar()
        names = list(cat_data.keys())

        if not names:
            tk.Label(body, text="nenhum gatinho cadastrado.",
                     font=FM, bg=BG, fg=DGRAY).pack(pady=40)
            return

        # Seletor
        sel_row = tk.Frame(body, bg=BG)
        sel_row.pack(fill="x", pady=8)
        tk.Label(sel_row, text="gatinho:", font=FB, bg=BG, fg=TEXT,
                 width=14, anchor="w").pack(side="left")
        combo = ttk.Combobox(sel_row, textvariable=selected,
                             values=names, state="readonly",
                             font=FM, width=20)
        combo.pack(side="left")

        # Preview sprite
        spr_cv = tk.Canvas(sel_row, width=72, height=68,
                           bg=BG, highlightthickness=0)
        spr_cv.pack(side="left", padx=14)

        # Campos
        fields = {}
        pelagem_var = tk.StringVar()
        filhote_var = tk.BooleanVar()
        castrado_var = tk.BooleanVar()
        photo_path = tk.StringVar()
        _photo_ref = [None]

        form = tk.Frame(body, bg=BG)
        form.pack(fill="x", pady=8)

        for lbl, key in [("raça:", "raça"), ("peso (kg):", "peso"),
                          ("idade:", "idade")]:
            row = tk.Frame(form, bg=BG)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=lbl, font=FB, bg=BG, fg=TEXT,
                     width=16, anchor="w").pack(side="left")
            var = tk.StringVar()
            fields[key] = var
            px_entry(row, var).pack(side="left")

        p_row = tk.Frame(form, bg=BG)
        p_row.pack(fill="x", pady=4)
        tk.Label(p_row, text="pelagem:", font=FB, bg=BG, fg=TEXT,
                 width=16, anchor="w").pack(side="left")
        pel_combo = ttk.Combobox(p_row, textvariable=pelagem_var,
                                 values=FUR_OPTIONS, state="readonly",
                                 font=FB, width=18)
        pel_combo.pack(side="left")

        ck_row = tk.Frame(form, bg=BG)
        ck_row.pack(fill="x", pady=6)
        tk.Checkbutton(ck_row, text="filhote", variable=filhote_var,
                       font=FB, bg=BG, activebackground=BG,
                       selectcolor=PINK).pack(side="left", padx=10)
        tk.Checkbutton(ck_row, text="castrado", variable=castrado_var,
                       font=FB, bg=BG, activebackground=BG,
                       selectcolor=MINT).pack(side="left", padx=10)

        # Foto
        photo_cv = tk.Canvas(form, width=100, height=100, bg=LGRAY,
                             highlightthickness=1, highlightbackground=BORDER)
        photo_cv.pack(pady=6)

        def _choose_photo():
            path = filedialog.askopenfilename(
                filetypes=[("Imagens","*.jpg *.jpeg *.png *.bmp *.webp")])
            if path:
                photo_path.set(path)
                img = load_photo(path, (96, 96))
                if img:
                    _photo_ref[0] = img
                    photo_cv.delete("all")
                    photo_cv.create_image(2, 2, image=img, anchor="nw")

        px_btn(form, "🖼  trocar foto", _choose_photo, bg=PEACH, w=18, pady=6).pack(pady=4)

        def _load_fields(*_):
            nome = selected.get()
            if nome not in cat_data:
                return
            info = cat_data[nome]
            fields["raça"].set(info.get("raça",""))
            fields["peso"].set(info.get("peso",""))
            fields["idade"].set(info.get("idade",""))
            pelagem_var.set(info.get("pelagem", FUR_OPTIONS[0]))
            filhote_var.set(info.get("filhote", False))
            castrado_var.set(info.get("castrado", False))
            photo_path.set(info.get("foto", ""))
            # sprite preview
            spr_cv.delete("all")
            _render_sprite(spr_cv, 1, 1, SPR_SENTADO,
                           info.get("pelagem","cinza"), px=5, tag="s")
            # foto preview
            photo_cv.delete("all")
            if info.get("foto"):
                img = load_photo(info["foto"], (96,96))
                if img:
                    _photo_ref[0] = img
                    photo_cv.create_image(2, 2, image=img, anchor="nw")
                    return
            photo_cv.create_text(50, 50, text="sem foto",
                                  font=FS, fill=DGRAY, justify="center")

        combo.bind("<<ComboboxSelected>>", _load_fields)

        def _save():
            nome = selected.get()
            if nome not in cat_data:
                messagebox.showwarning("ops!", "selecione um gatinho!")
                return
            try:
                peso = float(fields["peso"].get())
            except ValueError:
                messagebox.showwarning("ops!", "peso deve ser número"); return
            try:
                idade = int(fields["idade"].get())
            except ValueError:
                messagebox.showwarning("ops!", "idade deve ser inteiro"); return
            cat_data[nome].update({
                "raça":     fields["raça"].get(),
                "pelagem":  pelagem_var.get(),
                "peso":     peso,
                "idade":    idade,
                "filhote":  filhote_var.get(),
                "castrado": castrado_var.get(),
                "foto":     photo_path.get(),
            })
            messagebox.showinfo("nyaa~", f"gatinho '{nome}' atualizado! ♡")
            self._pop()

        px_btn(body, "💾  salvar alterações", _save, bg=MINT, w=28, pady=12).pack(pady=10)

    # ── Excluir ────────────────────────────────────────
    def _page_delete(self):
        cf = self._content
        section_header(cf, "🗑️  excluir gatinho",
                       "cuidado: esta ação não pode ser desfeita", LAVENDER)

        body = tk.Frame(cf, bg=BG)
        body.pack(fill="both", expand=True, padx=60, pady=30)

        names = list(cat_data.keys())
        if not names:
            tk.Label(body, text="nenhum gatinho cadastrado.",
                     font=FM, bg=BG, fg=DGRAY).pack(pady=40)
            return

        selected = tk.StringVar()
        spr_cv = tk.Canvas(body, width=80, height=74, bg=BG, highlightthickness=0)
        spr_cv.pack(pady=8)

        sel_row = tk.Frame(body, bg=BG)
        sel_row.pack(pady=10)
        tk.Label(sel_row, text="gatinho:", font=FB, bg=BG, fg=TEXT).pack(side="left")
        combo = ttk.Combobox(sel_row, textvariable=selected,
                             values=names, state="readonly",
                             font=FM, width=20)
        combo.pack(side="left", padx=10)

        def _on_sel(*_):
            nome = selected.get()
            if nome in cat_data:
                spr_cv.delete("all")
                _render_sprite(spr_cv, 2, 2, SPR_SENTADO,
                               cat_data[nome].get("pelagem","cinza"),
                               px=5, tag="s")
        combo.bind("<<ComboboxSelected>>", _on_sel)

        info_lbl = tk.Label(body, text="", font=FB, bg=BG, fg=TEXT)
        info_lbl.pack(pady=6)

        def _delete():
            nome = selected.get()
            if nome not in cat_data:
                messagebox.showwarning("ops!", "selecione um gatinho!")
                return
            if messagebox.askyesno("confirmar",
                                   f"tem certeza que deseja excluir '{nome}'?\n(｡•́︿•̀｡)"):
                del cat_data[nome]
                _photo_cache.clear()
                messagebox.showinfo("feito", f"'{nome}' foi removido do sistema.")
                self._pop()

        px_btn(body, "🗑️  excluir gatinho", _delete, bg=DPINK, w=26, pady=12).pack(pady=16)

    # ── Sensores ──────────────────────────────────────
    def _page_sensor(self):
        cf = self._content
        section_header(cf, "📡  painel de sensores",
                       "monitoramento em tempo real ♡", YELLOW)

        if not cat_data:
            tk.Label(cf, text="cadastre um gatinho primeiro! (｡•́︿•̀｡)",
                     font=FM, bg=BG, fg=DGRAY).pack(pady=60)
            return

        main = tk.Frame(cf, bg=BG)
        main.pack(fill="both", expand=True)

        # ── Painel esquerdo (controles) ─────────────
        left = tk.Frame(main, bg=LAVENDER, width=240)
        left.pack(side="left", fill="y", padx=0)
        left.pack_propagate(False)

        tk.Label(left, text="gatinho:", font=FB, bg=LAVENDER, fg=TEXT).pack(pady=(18,4))

        selected = tk.StringVar(value=list(cat_data.keys())[0])
        cat_combo = ttk.Combobox(left, textvariable=selected,
                                 values=list(cat_data.keys()),
                                 state="readonly", font=FM, width=16)
        cat_combo.pack(padx=10)

        tk.Label(left, text="estado:", font=FB, bg=LAVENDER, fg=TEXT).pack(pady=(16,4))

        estado_var = tk.StringVar()
        estados = [
            ("💤  dormindo",    "dormindo"),
            ("🍽  comendo",     "comendo"),
            ("😺  ficou gordo", "gordo"),
            ("🗺  aventureiro", "aventureiro"),
        ]
        for lbl, val in estados:
            tk.Radiobutton(
                left, text=lbl, variable=estado_var, value=val,
                font=FB, bg=LAVENDER, fg=TEXT,
                activebackground=LAVENDER, selectcolor=PINK,
                command=lambda: _on_change()
            ).pack(anchor="w", padx=16, pady=3)

        info_lbl = tk.Label(left, text="", font=FS, bg=LAVENDER,
                            fg=TEXT, wraplength=200, justify="left")
        info_lbl.pack(pady=12, padx=10)

        # sprite preview no painel esquerdo
        spr_left = tk.Canvas(left, width=80, height=74, bg=LAVENDER, highlightthickness=0)
        spr_left.pack(pady=6)

        # ── Painel direito (animação + foto) ────────
        right = tk.Frame(main, bg=BG)
        right.pack(side="right", fill="both", expand=True)

        # Canvas principal de animação
        anim_cv = tk.Canvas(right, bg=CREAM, highlightthickness=3,
                            highlightbackground=GOLD)
        anim_cv.pack(fill="both", expand=True, padx=10, pady=10)

        # Grama e cenário de fundo
        def _draw_bg(w, h):
            anim_cv.delete("bg")
            # céu
            anim_cv.create_rectangle(0, 0, w, int(h*0.62),
                                     fill=SOFT_BLUE, outline='', tags="bg")
            # chão
            anim_cv.create_rectangle(0, int(h*0.62), w, h,
                                     fill=DMINT, outline='', tags="bg")
            # grama pontuda
            for gx in range(0, w, 14):
                gy = int(h * 0.62)
                anim_cv.create_polygon(
                    gx, gy, gx+5, gy-14, gx+10, gy,
                    fill=MINT, outline='', tags="bg"
                )
            # nuvens
            for nx, ny in [(80,30),(220,55),(380,20),(560,45),(420,60)]:
                for dx in [0, 22, -22]:
                    anim_cv.create_oval(nx+dx-24, ny-14, nx+dx+24, ny+14,
                                        fill=WHITE, outline='', tags="bg")

        anim_cv.bind("<Configure>", lambda e: _draw_bg(e.width, e.height))

        # Variáveis de animação
        _state = {"frame": 0, "job": None, "pelagem": "cinza", "photo_img": None}

        def _draw_polaroid(cv, px, py, img_tk, nome, tilt=8):
            """Desenha moldura polaroid criativa com foto."""
            # sombra
            cv.create_rectangle(px+8, py+8, px+138, py+188,
                                 fill="#DDCCDD", outline='', tags="cat")
            # fundo da polaroid (branco)
            cv.create_rectangle(px, py, px+130, py+185,
                                 fill=WHITE, outline=BORDER, width=3, tags="cat")
            # área da foto
            if img_tk:
                cv.create_image(px+5, py+5, image=img_tk, anchor="nw", tags="cat")
            else:
                cv.create_rectangle(px+5, py+5, px+125, py+130,
                                    fill=LGRAY, outline='', tags="cat")
                cv.create_text(px+65, py+70, text="📷\nsem foto",
                               font=FS, fill=DGRAY, justify="center", tags="cat")
            # legenda
            cv.create_rectangle(px, py+132, px+130, py+185,
                                 fill=WHITE, outline='', tags="cat")
            cv.create_text(px+65, py+150, text=nome.title(),
                           font=FM, fill=TEXT, tags="cat")
            # decorações (estrelinhas, coraçõezinhos)
            for dx, dy, sym, col in [(-14,-14,"★",GOLD),(138,-10,"♥",DPINK),
                                      (-10,185,"♡",PINK),(130,180,"✿",MINT)]:
                cv.create_text(px+dx, py+dy, text=sym,
                               font=("Courier",14,"bold"), fill=col, tags="cat")

        def _tick():
            _state["frame"] += 1
            f = _state["frame"]
            nome = selected.get()
            info = cat_data.get(nome, {})
            estado = info.get("estado", "dormindo")
            pelagem = info.get("pelagem", "cinza")

            w = anim_cv.winfo_width() or 600
            h = anim_cv.winfo_height() or 400
            cx = w // 2
            cy = int(h * 0.5)

            # Desenha animação do gato
            {
                "dormindo":    draw_cat_dormindo,
                "comendo":     draw_cat_comendo,
                "gordo":       draw_cat_gordo,
                "aventureiro": draw_cat_aventureiro,
            }.get(estado, draw_cat_dormindo)(anim_cv, cx, cy, f, pelagem)

            # Foto do gato em polaroid (se houver)
            foto_path = info.get("foto","")
            if foto_path and _state["photo_img"] is None:
                _state["photo_img"] = load_photo(foto_path, (120, 126))

            img = _state["photo_img"]
            # Polaroid posicionada na área direita superior
            pol_x = w - 170
            pol_y = 20
            if pol_x > cx + 80:
                _draw_polaroid(anim_cv, pol_x, pol_y, img, nome)
            elif foto_path:
                # janela pequena se não couber do lado
                _draw_polaroid(anim_cv, 15, 15, img, nome)

            _state["job"] = anim_cv.after(50, _tick)

        def _on_change(*_):
            nome = selected.get()
            info = cat_data.get(nome, {})
            est = estado_var.get() or info.get("estado","dormindo")
            if nome in cat_data:
                cat_data[nome]["estado"] = est
            _state["photo_img"] = None  # forçar reload de foto

            # Atualiza sprite esquerdo
            spr_left.delete("all")
            _render_sprite(spr_left, 2, 2, SPR_SENTADO,
                           info.get("pelagem","cinza"), px=5, tag="s")

            # Atualiza info
            unit = "meses" if info.get("filhote") else "anos"
            extras = []
            if info.get("filhote"):  extras.append("filhote")
            if info.get("castrado"): extras.append("castrado")
            tags = ("  •  ".join(extras) + "\n") if extras else ""
            info_lbl.config(
                text=f"{nome.title()}\n"
                     f"raça: {info.get('raça','-')}\n"
                     f"peso: {info.get('peso','-')} kg\n"
                     f"idade: {info.get('idade','-')} {unit}\n"
                     f"{tags}"
                     f"estado: {est}"
            )
            # mascote muda de pelagem
            self.mascot.fur = info.get("pelagem","cinza")

        cat_combo.bind("<<ComboboxSelected>>", _on_change)
        estado_var.set(cat_data[list(cat_data.keys())[0]].get("estado","dormindo"))
        _on_change()

        # Para job anterior se houver
        def _start():
            if _state["job"]:
                try:
                    anim_cv.after_cancel(_state["job"])
                except Exception:
                    pass
            _tick()

        # Inicia animação depois do layout
        cf.after(100, _start)

        # Para animação ao sair da página
        def _on_destroy(e):
            if _state["job"]:
                try:
                    anim_cv.after_cancel(_state["job"])
                except Exception:
                    pass
        anim_cv.bind("<Destroy>", _on_destroy)

    # ── Loop ──────────────────────────────────────────
    def run(self):
        self.root.mainloop()


# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    app = CatApp()
    app.run()