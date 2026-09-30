import tkinter as tk
from tkinter import filedialog, messagebox
import shutil
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


# ============================================================
# ДИЗАЙН-СИСТЕМА (Fluent / Liquid Glass, dark)
# ============================================================

BG          = "#0B0F17"
SURFACE     = "#111827"
SURFACE_HI  = "#151C2B"
BORDER      = "#1f2735"          # ~rgba(255,255,255,0.08)
BORDER_HI   = "#2c3547"
TEXT        = "#F5F7FA"
SECONDARY   = "#8B95A7"
MUTED       = "#5b6472"
PRIMARY     = "#7C5CFF"
PRIMARY_HI  = "#8B70FF"
PRIMARY_LO  = "#6949e8"
SUCCESS     = "#4ADE80"
ERROR       = "#F87171"
WARN        = "#FACC15"

SETTINGS_FILE = "autosort_settings.json"
AUTO_INTERVAL_MS = 2000
APP_RUN_NAME = "Poryadok"

TEMP_EXTS = {".part", ".crdownload", ".tmp", ".download", ".partial"}

CATEGORIES = {
    "Картинки":  (".jpg", ".jpeg", ".png", ".gif", ".bmp",
                  ".svg", ".webp", ".heic", ".ico"),
    "Документы": (".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
                  ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".md"),
    "Видео":     (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"),
    "Музыка":    (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"),
    "Архивы":    (".zip", ".rar", ".7z", ".tar", ".gz", ".iso"),
    "Программы": (".exe", ".msi", ".apk", ".deb"),
    "Код":       (".py", ".js", ".ts", ".html", ".css", ".java",
                  ".cpp", ".cs", ".json", ".xml", ".sh", ".bat"),
}

CHIP_ICONS = {
    "Картинки": "🖼", "Документы": "📄", "Видео": "🎬", "Музыка": "🎵",
    "Архивы": "📦", "Программы": "⚙", "Код": "</>", "Другое": "•••",
}

FONT       = "Segoe UI"
F_TITLE    = (FONT, 26, "bold")
F_SUB      = (FONT, 11)
F_CAPS     = (FONT, 9, "bold")
F_BODY     = (FONT, 12)
F_BODY_B   = (FONT, 12, "bold")
F_SMALL    = (FONT, 10)
F_TINY     = (FONT, 9)
F_TIME     = ("Consolas", 9)


# ============================================================
# УТИЛИТЫ
# ============================================================

def hex_mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def rr_points(x1, y1, x2, y2, r):
    r = max(2, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1, x1 + r, y1, x1, y1, x1, y1 + r, x1, y1 + r,
        x1, y2 - r, x1, y2 - r, x1, y2, x1 + r, y2, x1 + r, y2,
        x2 - r, y2, x2 - r, y2, x2, y2, x2, y2 - r, x2, y2 - r,
        x2, y1 + r, x2, y1 + r, x2, y1, x2 - r, y1, x2 - r, y1,
        x1 + r, y1,
    ]


def is_file_locked(path: Path) -> bool:
    try:
        with open(path, "rb"):
            pass
        return False
    except (PermissionError, OSError):
        return True


class Anim:
    """Плавная величина 0..1 (или любая) с callback на каждый кадр."""

    def __init__(self, root, initial=0.0, speed=0.28):
        self.root = root
        self.v = initial
        self.target = initial
        self.speed = speed
        self.job = None
        self.cb = None

    def to(self, target, cb=None):
        self.target = target
        if cb:
            self.cb = cb
        if self.job is None and abs(self.target - self.v) > 0.001:
            self.job = self.root.after(16, self._step)

    def set(self, value):
        self.v = value
        self.target = value

    def _step(self):
        self.v += (self.target - self.v) * self.speed
        if abs(self.target - self.v) < 0.005:
            self.v = self.target
            self.job = None
            if self.cb:
                self.cb(self.v)
            return
        if self.cb:
            self.cb(self.v)
        self.job = self.root.after(16, self._step)


# ============================================================
# АВТОЗАПУСК С WINDOWS (без изменений логики)
# ============================================================

def autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    script = os.path.abspath(__file__)
    return f'"{exe}" "{script}"'


def get_autostart():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run"
        )
        try:
            winreg.QueryValueEx(key, APP_RUN_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_autostart(enabled):
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        try:
            if enabled:
                winreg.SetValueEx(
                    key, APP_RUN_NAME, 0, winreg.REG_SZ,
                    autostart_command()
                )
            else:
                try:
                    winreg.DeleteValue(key, APP_RUN_NAME)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ============================================================
# КНОПКА (Fluent: hover-glow, press-scale)
# ============================================================

class GlassButton:

    def __init__(self, canvas, root, x, y, w, h, text, command,
                 primary=False):
        self.c = canvas
        self.root = root
        self.x1, self.y1, self.x2, self.y2 = x, y, x + w, y + h
        self.command = command
        self.primary = primary
        self.radius = 12

        if primary:
            self.base, self.hover, self.press = PRIMARY, PRIMARY_HI, PRIMARY_LO
            self.edge, self.edge_hi = PRIMARY_LO, PRIMARY_HI
            self.fg = "#ffffff"
        else:
            self.base, self.hover, self.press = SURFACE_HI, "#1b2334", "#0e1420"
            self.edge, self.edge_hi = BORDER, BORDER_HI
            self.fg = TEXT

        self.font = (FONT, 11, "bold") if primary else (FONT, 11)

        self.hv = Anim(root, 0.0, 0.22)
        self.pr = Anim(root, 0.0, 0.35)
        self.hv.cb = lambda _v: self._redraw()
        self.pr.cb = lambda _v: self._redraw()

        self.shape = canvas.create_polygon(
            rr_points(x, y, x + w, y + h, self.radius),
            smooth=True, fill=self.base, outline=self.edge, width=1
        )
        self.gloss = canvas.create_line(
            x + self.radius, y + 1, x + w - self.radius, y + 1,
            fill=hex_mix(self.edge, "#ffffff", 0.10)
        )
        self.label = canvas.create_text(
            (x + x + w) / 2, (y + y + h) / 2,
            text=text, fill=self.fg, font=self.font
        )

        for item in (self.shape, self.label, self.gloss):
            canvas.tag_bind(item, "<Enter>", self._enter)
            canvas.tag_bind(item, "<Leave>", self._leave)
            canvas.tag_bind(item, "<ButtonPress-1>", self._down)
            canvas.tag_bind(item, "<ButtonRelease-1>", self._up)

    def _enter(self, e):
        self.c.configure(cursor="hand2")
        self.hv.to(1.0)

    def _leave(self, e):
        self.c.configure(cursor="")
        self.hv.to(0.0)
        self.pr.to(0.0)

    def _down(self, e):
        self.pr.to(1.0)

    def _up(self, e):
        self.pr.to(0.0)
        if self.x1 <= e.x <= self.x2 and self.y1 <= e.y <= self.y2:
            self.command()

    def _redraw(self):
        hv, pr = self.hv.v, self.pr.v
        fill = hex_mix(self.base, self.hover, hv)
        fill = hex_mix(fill, self.press, pr)
        edge = hex_mix(self.edge, self.edge_hi, hv)
        scale = 1.0 - 0.035 * pr

        cx = (self.x1 + self.x2) / 2
        cy = (self.y1 + self.y2) / 2
        x1 = cx + (self.x1 - cx) * scale
        x2 = cx + (self.x2 - cx) * scale
        y1 = cy + (self.y1 - cy) * scale
        y2 = cy + (self.y2 - cy) * scale

        self.c.coords(self.shape, *rr_points(x1, y1, x2, y2, self.radius))
        self.c.itemconfig(self.shape, fill=fill, outline=edge)
        self.c.coords(self.gloss, x1 + self.radius, y1 + 1,
                      x2 - self.radius, y1 + 1)
        self.c.itemconfig(
            self.gloss,
            fill=hex_mix(edge, "#ffffff", 0.10 + 0.10 * hv)
        )


# ============================================================
# ТОГГЛ В СТИЛЕ WINDOWS 11
# ============================================================

class WinToggle:

    def __init__(self, canvas, root, x, y, on_change):
        self.c = canvas
        self.root = root
        self.on_change = on_change
        self.value = False
        self.t = Anim(root, 0.0, 0.25)
        self.t.cb = lambda _v: self._redraw()

        self.x, self.y = x, y
        self.w, self.h = 46, 24

        self.track = canvas.create_polygon(
            rr_points(x, y, x + self.w, y + self.h, 12),
            smooth=True, fill="#2a3140", outline=BORDER_HI, width=1
        )
        self.knob = canvas.create_oval(
            x + 5, y + 5, x + 19, y + 19,
            fill=SECONDARY, outline=""
        )

        for item in (self.track, self.knob):
            canvas.tag_bind(item, "<ButtonPress-1>", self._click)
            canvas.tag_bind(item, "<Enter>", self._enter)
            canvas.tag_bind(item, "<Leave>", self._leave)

    def _enter(self, e):
        self.c.configure(cursor="hand2")

    def _leave(self, e):
        self.c.configure(cursor="")

    def _click(self, e):
        self.set_value(not self.value, fire=True)

    def set_value(self, value, fire=False):
        self.value = value
        self.t.to(1.0 if value else 0.0)
        if fire:
            self.on_change(value)

    def _redraw(self):
        t = ease(self.t.v)
        self.c.itemconfig(
            self.track,
            fill=hex_mix("#2a3140", PRIMARY, t),
            outline=hex_mix(BORDER_HI, PRIMARY_HI, t * 0.7)
        )
        kx = self.x + 5 + t * (self.w - 28)
        self.c.coords(self.knob, kx, self.y + 5, kx + 14, self.y + 19)
        self.c.itemconfig(
            self.knob,
            fill=hex_mix(SECONDARY, "#ffffff", t)
        )


# ============================================================
# ЖУРНАЛ: динамическая карточка + умный скролл
# ============================================================

ROW_H = 44
MAX_ROWS = 6
HEAD_H = 40
PAD_TOP = 8
PAD_BOT = 12

KIND_STYLE = {
    "success": (SUCCESS, "✓"),
    "info":    (SECONDARY, "●"),
    "process": (PRIMARY, "↻"),
    "warn":    (WARN, "\u26A0\uFE0E"),
    "error":   (ERROR, "✕"),
}


class Journal:

    def __init__(self, app, canvas, x1, x2, top):
        self.app = app
        self.c = canvas
        self.x1, self.x2, self.top = x1, x2, top

        self.entries = []
        self.pending = 0
        self.scroll = Anim(app.root, 0.0, 0.30)
        self.scroll.cb = lambda _v: self.draw()
        self.at_bottom = True
        self.drag = None
        self.sb_hover = False
        self.clear_hover = False
        self.pill_hover = False
        self._loop_job = None

        # Карточка
        self.card = canvas.create_polygon(
            rr_points(x1, top, x2, top + 10, 16),
            smooth=True, fill=SURFACE, outline=BORDER, width=1
        )
        self.gloss = canvas.create_line(
            x1 + 16, top + 1, x2 - 16, top + 1,
            fill=hex_mix(BORDER, "#ffffff", 0.10)
        )

        # Шапка
        self.h_title = canvas.create_text(
            x1 + 20, top + 21, text="ЖУРНАЛ", anchor="w",
            font=F_CAPS, fill=SECONDARY
        )
        self.counter = canvas.create_text(
            x2 - 20, top + 21, text="Разобрано: 0", anchor="e",
            font=F_SMALL, fill=SECONDARY
        )
        self.clear_btn = canvas.create_text(
            x2 - 130, top + 21, text="Очистить", anchor="e",
            font=F_TINY, fill=MUTED
        )
        canvas.tag_bind(self.clear_btn, "<Enter>", self._clear_in)
        canvas.tag_bind(self.clear_btn, "<Leave>", self._clear_out)
        canvas.tag_bind(self.clear_btn, "<ButtonPress-1>",
                        lambda e: self.clear())

        # Пустое состояние
        self.ph_icon = canvas.create_text(
            (x1 + x2) / 2, top + 52, text="✨",
            font=(FONT, 16), fill=MUTED
        )
        self.ph_1 = canvas.create_text(
            (x1 + x2) / 2, top + 78, text="Здесь пока ничего нет",
            font=F_SMALL, fill=SECONDARY
        )
        self.ph_2 = canvas.create_text(
            (x1 + x2) / 2, top + 96,
            text="Запустите сортировку — появится история действий",
            font=F_TINY, fill=MUTED
        )

        # Пул строк
        self.pool = []
        for _ in range(MAX_ROWS + 2):
            row = {
                "glyph": canvas.create_text(
                    -200, -200, text="", anchor="w",
                    font=(FONT, 10, "bold"), fill=MUTED
                ),
                "time": canvas.create_text(
                    -200, -200, text="", anchor="w",
                    font=F_TIME, fill=MUTED
                ),
                "title": canvas.create_text(
                    -200, -200, text="", anchor="w",
                    font=F_BODY_B, fill=TEXT
                ),
                "detail": canvas.create_text(
                    -200, -200, text="", anchor="w",
                    font=F_SMALL, fill=SECONDARY
                ),
            }
            self.pool.append(row)

        # Скроллбар
        self.sb_track = canvas.create_line(
            -200, -200, -200, -200, fill="#161d2b", width=4
        )
        self.sb_thumb = canvas.create_line(
            -200, -200, -200, -200, fill="#2a3140", width=5,
            capstyle="round"
        )
        canvas.tag_bind(self.sb_thumb, "<Enter>", self._sb_in)
        canvas.tag_bind(self.sb_thumb, "<Leave>", self._sb_out)
        canvas.tag_bind(self.sb_thumb, "<ButtonPress-1>", self._drag_start)
        canvas.tag_bind(self.sb_thumb, "<B1-Motion>", self._drag_move)
        canvas.tag_bind(self.sb_thumb, "<ButtonRelease-1>", self._drag_end)

        # Pill «Новые события»
        self.pill = canvas.create_polygon(
            rr_points(-200, -200, -100, -180, 12),
            smooth=True, fill=SURFACE_HI, outline=PRIMARY, width=1
        )
        self.pill_text = canvas.create_text(
            -150, -190, text="", font=F_TINY, fill=PRIMARY_HI
        )
        canvas.tag_bind(self.pill, "<ButtonPress-1>", self._pill_click)
        canvas.tag_bind(self.pill_text, "<ButtonPress-1>", self._pill_click)
        canvas.tag_bind(self.pill, "<Enter>", self._pill_in)
        canvas.tag_bind(self.pill_text, "<Enter>", self._pill_in)
        canvas.tag_bind(self.pill, "<Leave>", self._pill_out)
        canvas.tag_bind(self.pill_text, "<Leave>", self._pill_out)

        canvas.bind("<MouseWheel>", self._wheel)

    # --------------------------------------------------------
    # API
    # --------------------------------------------------------

    def add(self, kind, title, detail=None):
        self.entries.append({
            "kind": kind,
            "title": title,
            "detail": detail,
            "born": time.time(),
        })
        if len(self.entries) > 500:
            self.entries.pop(0)

        if not self.at_bottom:
            self.pending += 1
        self.app.on_journal_changed()
        self._kick()

    def set_counter(self, value):
        self.c.itemconfig(self.counter, text=f"Разобрано: {value}")

    def clear(self):
        self.entries = []
        self.pending = 0
        self.scroll.set(0.0)
        self.app.on_journal_changed()
        self.draw()

    def height_target(self):
        n = len(self.entries)
        if n == 0:
            return 118
        rows = min(n, MAX_ROWS)
        return HEAD_H + PAD_TOP + rows * ROW_H + PAD_BOT

    # --------------------------------------------------------
    # Скролл
    # --------------------------------------------------------

    def _view(self, h):
        view_top = self.top + HEAD_H + PAD_TOP - 4
        view_h = h - HEAD_H - PAD_TOP - PAD_BOT + 4
        return view_top, view_h

    def _scroll_max(self, h):
        _, view_h = self._view(h)
        return max(0.0, len(self.entries) * ROW_H - view_h)

    def _wheel(self, e):
        h = self.app.j_h
        view_top, view_h = self._view(h)
        if not (self.x1 <= e.x <= self.x2 and view_top - 10 <= e.y <= view_top + view_h + 10):
            return
        if len(self.entries) == 0:
            return
        delta = -1 if e.delta > 0 else 1
        target = self.scroll.target + delta * ROW_H * 2
        self.scroll.to(max(0.0, min(self._scroll_max(h), target)))
        self._sync_bottom_state()
        self._kick()

    def _drag_start(self, e):
        self.drag = (e.y, self.scroll.v)

    def _drag_move(self, e):
        if not self.drag:
            return
        h = self.app.j_h
        _, view_h = self._view(h)
        content_h = len(self.entries) * ROW_H
        if content_h <= 0:
            return
        ratio = content_h / max(1.0, view_h)
        dy = e.y - self.drag[0]
        self.scroll.set(max(0.0, min(self._scroll_max(h),
                                     self.drag[1] + dy * ratio)))
        self._sync_bottom_state()
        self.draw()

    def _drag_end(self, e):
        self.drag = None
        self._sync_bottom_state()

    def _sb_in(self, e):
        self.sb_hover = True
        self.draw()

    def _sb_out(self, e):
        self.sb_hover = False
        self.draw()

    def _sync_bottom_state(self):
        h = self.app.j_h
        bottom = self.scroll.target >= self._scroll_max(h) - 1.0
        if bottom and not self.at_bottom:
            self.pending = 0
        self.at_bottom = bottom

    def _pill_click(self, e):
        self.pending = 0
        self.scroll.to(self._scroll_max(self.app.j_h))
        self.at_bottom = True
        self._kick()

    def _pill_in(self, e):
        self.pill_hover = True
        self.c.configure(cursor="hand2")
        self.draw()

    def _pill_out(self, e):
        self.pill_hover = False
        self.c.configure(cursor="")
        self.draw()

    def _clear_in(self, e):
        self.clear_hover = True
        self.c.configure(cursor="hand2")
        self.c.itemconfig(self.clear_btn, fill=SECONDARY)

    def _clear_out(self, e):
        self.clear_hover = False
        self.c.configure(cursor="")
        self.c.itemconfig(self.clear_btn, fill=MUTED)

    # --------------------------------------------------------
    # Отрисовка
    # --------------------------------------------------------

    def layout(self, h):
        self.c.coords(self.card, *rr_points(self.x1, self.top,
                                            self.x2, self.top + h, 16))
        self.c.coords(self.gloss, self.x1 + 16, self.top + 1,
                      self.x2 - 16, self.top + 1)
        self.draw()

    def draw(self):
        c = self.c
        h = self.app.j_h
        view_top, view_h = self._view(h)
        n = len(self.entries)

        # Пустое состояние
        empty = (n == 0)
        state = "normal" if empty else "hidden"
        for item in (self.ph_icon, self.ph_1, self.ph_2):
            c.itemconfig(item, state=state)
        if empty:
            cy = self.top + HEAD_H + (h - HEAD_H) / 2
            c.coords(self.ph_icon, (self.x1 + self.x2) / 2, cy - 26)
            c.coords(self.ph_1, (self.x1 + self.x2) / 2, cy + 2)
            c.coords(self.ph_2, (self.x1 + self.x2) / 2, cy + 20)

        content_h = n * ROW_H
        scroll_max = self._scroll_max(h)
        scroll = max(0.0, min(scroll_max, self.scroll.v))
        self.at_bottom = scroll >= scroll_max - 1.0
        if self.at_bottom:
            self.pending = 0

        first = int(scroll // ROW_H)
        off = scroll % ROW_H
        now = time.time()
        animating = False

        for i, row in enumerate(self.pool):
            idx = first + i
            y = view_top + i * ROW_H - off

            if empty or idx >= n or y > view_top + view_h + 4:
                for it in row.values():
                    c.coords(it, -200, -200)
                continue

            e = self.entries[idx]
            age = (now - e["born"]) / 0.28
            if age < 1.0:
                animating = True
            f = ease(age)
            yoff = (1.0 - f) * 10
            color, glyph = KIND_STYLE[e["kind"]]
            faded = hex_mix("#39424f", color, f)

            c.itemconfig(row["glyph"], state="normal", text=glyph,
                         fill=faded)
            c.coords(row["glyph"], self.x1 + 20, y + 13 + yoff)

            c.itemconfig(row["time"], state="normal",
                         text=e["time"] if "time" in e else
                         datetime.fromtimestamp(e["born"]).strftime("%H:%M:%S"),
                         fill=hex_mix("#39424f", MUTED, f))
            c.coords(row["time"], self.x1 + 40, y + 14 + yoff)

            title = e["title"]
            if len(title) > 46:
                title = title[:43] + "..."
            c.itemconfig(row["title"], state="normal", text=title,
                         fill=hex_mix("#39424f", TEXT, f))
            c.coords(row["title"], self.x1 + 100, y + 13 + yoff)

            if e["detail"]:
                c.itemconfig(row["detail"], state="normal",
                             text=e["detail"],
                             fill=hex_mix("#39424f", SECONDARY, f))
                c.coords(row["detail"], self.x1 + 100, y + 29 + yoff)
            else:
                c.itemconfig(row["detail"], state="hidden")
                c.coords(row["detail"], -200, -200)

        # Скроллбар
        if content_h > view_h + 1:
            tx = self.x2 - 12
            c.coords(self.sb_track, tx, view_top + 2, tx, view_top + view_h - 2)
            thumb_len = max(24.0, view_h / content_h * view_h)
            pos = (scroll / content_h) * view_h
            c.coords(self.sb_thumb, tx, view_top + pos,
                     tx, view_top + pos + thumb_len)
            c.itemconfig(self.sb_thumb,
                         fill="#3b4356" if self.sb_hover else "#2a3140",
                         width=6 if self.sb_hover else 4,
                         state="normal")
            c.itemconfig(self.sb_track, state="normal")
        else:
            c.itemconfig(self.sb_thumb, state="hidden")
            c.itemconfig(self.sb_track, state="hidden")
            c.coords(self.sb_thumb, -200, -200, -200, -200)
            c.coords(self.sb_track, -200, -200, -200, -200)

        # Pill «Новые события»
        if self.pending > 0 and not self.at_bottom:
            text = f"↓  Новые события: {self.pending}"
            pw = 150
            px = (self.x1 + self.x2) / 2
            py = self.top + h - 24
            c.coords(self.pill, *rr_points(px - pw / 2, py - 12,
                                           px + pw / 2, py + 12, 12))
            c.itemconfig(self.pill, state="normal",
                         fill=SURFACE_HI if not self.pill_hover else "#1b2334",
                         outline=PRIMARY)
            c.coords(self.pill_text, px, py)
            c.itemconfig(self.pill_text, state="normal", text=text)
        else:
            c.itemconfig(self.pill, state="hidden")
            c.itemconfig(self.pill_text, state="hidden")
            c.coords(self.pill, -200, -200, -100, -180)
            c.coords(self.pill_text, -150, -190)

        if animating:
            self._kick()

    def _kick(self):
        if self._loop_job is None:
            self._loop_job = self.app.root.after(30, self._loop)

    def _loop(self):
        self._loop_job = None
        self.draw()
        recent = any(
            time.time() - e["born"] < 0.35 for e in self.entries[-3:]
        )
        if recent or self.scroll.job or self.drag:
            self._kick()


# ============================================================
# TOAST-УВЕДОМЛЕНИЯ
# ============================================================

class ToastManager:

    def __init__(self, root):
        self.root = root
        self.stack = []

    def show(self, title, message, kind="success"):
        top = tk.Toplevel(self.root)
        top.overriderredirect(True)
        top.attributes("-topmost", True)
        top.attributes("-transparentcolor", "#010203")
        top.attributes("-alpha", 0.0)

        w, h = 300, 64
        canvas = tk.Canvas(top, width=w, height=h,
                           bg="#010203", highlightthickness=0)
        canvas.pack()

        color = {"success": SUCCESS, "error": ERROR,
                 "info": PRIMARY}[kind]
        glyph = {"success": "✓", "error": "✕", "info": "●"}[kind]

        canvas.create_polygon(
            rr_points(1, 1, w - 1, h - 1, 14),
            smooth=True, fill=SURFACE_HI, outline=BORDER_HI, width=1
        )
        canvas.create_polygon(
            rr_points(10, 14, 14, h - 14, 2),
            smooth=True, fill=color, outline=""
        )
        canvas.create_text(30, 20, text=f"{glyph}  {title}", anchor="w",
                           font=(FONT, 11, "bold"), fill=TEXT)
        msg = message if len(message) < 40 else message[:37] + "..."
        canvas.create_text(30, 40, text=msg, anchor="w",
                           font=F_TINY, fill=SECONDARY)

        self.stack.append(top)
        self._place()
        self._fade(top, 0.0, True)

    def _place(self):
        x = self.root.winfo_rootx() + self.root.winfo_width() - 316
        y = self.root.winfo_rooty() + self.root.winfo_height() - 80
        for i, top in enumerate(reversed(self.stack)):
            top.geometry(f"+{x}+{y - i * 70}")

    def _fade(self, top, a, entering):
        if entering:
            a = min(1.0, a + 0.12)
            top.attributes("-alpha", a)
            if a < 1.0:
                self.root.after(16, lambda: self._fade(top, a, True))
            else:
                self.root.after(3200, lambda: self._fade(top, 1.0, False))
        else:
            a = max(0.0, a - 0.10)
            top.attributes("-alpha", a)
            if a > 0.0:
                self.root.after(16, lambda: self._fade(top, a, False))
            else:
                if top in self.stack:
                    self.stack.remove(top)
                top.destroy()
                self._place()


# ============================================================
# ПРИЛОЖЕНИЕ
# ============================================================

class App:

    W = 680

    def __init__(self, root):
        self.root = root
        self.root.title("Порядок")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.auto_on = False
        self.pending = {}
        self.undo_batches = []
        self.count = 0
        self.cat_counts = {c: 0 for c in list(CATEGORIES) + ["Другое"]}
        self.last_check = None
        self._status_job = None

        self.load_settings()

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._draw_header()
        self._build_folder_card()
        self._build_settings_card()
        self._build_actions()
        self._build_chips()

        # Журнал
        self.j_top = self.chips_bottom + 18
        self.journal = Journal(self, self.canvas, 28, self.W - 28, self.j_top)
        self.j_h = 118.0
        self.jh_anim = Anim(root, 118.0, 0.25)
        self.jh_anim.cb = self._apply_height

        # Строка состояния
        self.status_dot = self.canvas.create_oval(
            -200, -200, -200, -200, fill=MUTED, outline=""
        )
        self.status_text = self.canvas.create_text(
            -200, -200, text="", anchor="w", font=F_SMALL, fill=SECONDARY
        )
        self.status_check = self.canvas.create_text(
            -200, -200, text="", anchor="e", font=F_TINY, fill=MUTED
        )

        self.toasts = ToastManager(root)

        self._sync_layout()
        self.root.update_idletasks()
        self._enable_win11_look()
        self._fade(0.0)

        self.set_status_default()
        self.journal.draw()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --------------------------------------------------------
    # Шапка
    # --------------------------------------------------------

    def _draw_header(self):
        c = self.canvas

        c.create_polygon(
            rr_points(-160, -180, 320, 180, 160),
            smooth=True, fill="#0e1420", outline=""
        )
        c.create_polygon(
            rr_points(420, 560, 860, 940, 180),
            smooth=True, fill="#120f22", outline=""
        )

        # Логотип
        c.create_polygon(
            rr_points(28, 22, 68, 62, 12),
            smooth=True, fill=SURFACE_HI, outline=PRIMARY_LO, width=1
        )
        c.create_line(38, 36, 58, 36, fill=PRIMARY_HI, width=3)
        c.create_line(38, 43, 52, 43, fill=SECONDARY, width=3)
        c.create_line(38, 50, 55, 50, fill=SUCCESS, width=3)

        c.create_text(82, 34, text="Порядок", anchor="w",
                      font=F_TITLE, fill=TEXT)
        c.create_text(82, 58, text="Умная сортировка загрузок",
                      anchor="w", font=F_SUB, fill=SECONDARY)

    # --------------------------------------------------------
    # Карточка папки
    # --------------------------------------------------------

    def _build_folder_card(self):
        c = self.canvas
        y1, y2 = 84, 148

        self.folder_card = c.create_polygon(
            rr_points(28, y1, self.W - 28, y2, 14),
            smooth=True, fill=SURFACE, outline=BORDER, width=1
        )
        self.folder_gloss = c.create_line(
            44, y1 + 1, self.W - 44, y1 + 1,
            fill=hex_mix(BORDER, "#ffffff", 0.10)
        )
        self.folder_icon = c.create_text(
            52, (y1 + y2) / 2, text="📁", anchor="w", font=(FONT, 17)
        )
        c.create_text(84, y1 + 20, text="ПАПКА СОРТИРОВКИ", anchor="w",
                      font=F_CAPS, fill=SECONDARY)
        self.path_item = c.create_text(
            84, y1 + 42, text="", anchor="w", font=F_BODY, fill=TEXT
        )

        self.btn_browse = GlassButton(
            c, self.root, self.W - 128, y1 + 16, 84, 32,
            "Обзор", self.choose_folder
        )

        for item in (self.folder_card, self.folder_icon, self.path_item):
            c.tag_bind(item, "<Enter>", self._folder_in)
            c.tag_bind(item, "<Leave>", self._folder_out)
            c.tag_bind(item, "<ButtonPress-1>",
                       lambda e: self.choose_folder())

        self.refresh_path()

    def _folder_in(self, e):
        self.canvas.itemconfig(self.folder_card,
                               fill=SURFACE_HI, outline=BORDER_HI)
        self.canvas.configure(cursor="hand2")

    def _folder_out(self, e):
        self.canvas.itemconfig(self.folder_card,
                               fill=SURFACE, outline=BORDER)
        self.canvas.configure(cursor="")

    def refresh_path(self):
        text = str(self.folder)
        if len(text) > 52:
            text = "..." + text[-49:]
        self.canvas.itemconfig(self.path_item, text=text)

    # --------------------------------------------------------
    # Карточка настроек
    # --------------------------------------------------------

    def _build_settings_card(self):
        c = self.canvas
        y1, y2 = 160, 306

        c.create_polygon(
            rr_points(28, y1, self.W - 28, y2, 14),
            smooth=True, fill=SURFACE, outline=BORDER, width=1
        )
        c.create_line(44, y1 + 1, self.W - 44, y1 + 1,
                      fill=hex_mix(BORDER, "#ffffff", 0.10))

        rows = [
            ("Автосортировка", "Новые файлы сортируются автоматически",
             self.on_auto),
            ("Дата в имени", "Добавлять дату к имени файла",
             self.on_rename),
            ("Автозапуск", "Запускать вместе с Windows",
             self.on_autostart),
        ]

        self.toggles = []
        for i, (title, desc, handler) in enumerate(rows):
            cy = y1 + 25 + i * 48
            t_item = c.create_text(48, cy, text=title, anchor="w",
                                   font=F_BODY_B, fill=TEXT)
            d_item = c.create_text(48, cy + 17, text=desc, anchor="w",
                                   font=F_TINY, fill=SECONDARY)
            tg = WinToggle(c, self.root, self.W - 76, cy + 2, handler)
            self.toggles.append(tg)

            for item in (t_item, d_item):
                c.tag_bind(item, "<ButtonPress-1>",
                           lambda e, tg=tg: tg.set_value(not tg.value, True))
                c.tag_bind(item, "<Enter>",
                           lambda e: c.configure(cursor="hand2"))
                c.tag_bind(item, "<Leave>",
                           lambda e: c.configure(cursor=""))

        self.tg_auto, self.tg_rename, self.tg_start = self.toggles
        self.tg_rename.set_value(self.settings.get("rename", False))
        self.tg_start.set_value(get_autostart())

    # --------------------------------------------------------
    # Кнопки действий
    # --------------------------------------------------------

    def _build_actions(self):
        c = self.canvas
        y = 318

        GlassButton(c, self.root, 28, y, 288, 50,
                    "▶   Разобрать сейчас", self.sort_now, primary=True)
        GlassButton(c, self.root, 328, y, 150, 50,
                    "Отменить", self.undo_last)
        GlassButton(c, self.root, 490, y, 162, 50,
                    "Открыть папку", self.open_folder)

    # --------------------------------------------------------
    # Chips категорий
    # --------------------------------------------------------

    def _build_chips(self):
        c = self.canvas
        c.create_text(28, 392, text="КУДА РАСКЛАДЫВАТЬ", anchor="w",
                      font=F_CAPS, fill=SECONDARY)

        self.chips = {}
        x, y = 28, 408
        for cat in list(CATEGORIES) + ["Другое"]:
            label = f"{CHIP_ICONS[cat]}  {cat}"
            w = len(label) * 7 + 34
            if x + w > self.W - 28:
                x = 28
                y += 36
            chip = {
                "cat": cat,
                "x1": x, "y1": y, "x2": x + w, "y2": y + 30,
                "hv": Anim(self.root, 0.0, 0.22),
            }
            chip["hv"].cb = lambda _v, ch=chip: self._draw_chip(ch)
            chip["shape"] = c.create_polygon(
                rr_points(x, y, x + w, y + 30, 10),
                smooth=True, fill=SURFACE, outline=BORDER, width=1
            )
            chip["text"] = c.create_text(
                x + w / 2, y + 15, text=label, font=F_SMALL, fill=SECONDARY
            )
            chip["badge"] = c.create_text(
                x + w - 12, y + 15, text="", font=F_TINY, fill=PRIMARY_HI
            )
            for item in (chip["shape"], chip["text"], chip["badge"]):
                c.tag_bind(item, "<Enter>",
                           lambda e, ch=chip: (ch["hv"].to(1.0),
                                               c.configure(cursor="hand2")))
                c.tag_bind(item, "<Leave>",
                           lambda e, ch=chip: (ch["hv"].to(0.0),
                                               c.configure(cursor="")))
                c.tag_bind(item, "<ButtonPress-1>",
                           lambda e, ch=chip: self._chip_click(ch))
            self.chips[cat] = chip
            x += w + 8

        self.chips_bottom = y + 30

    def _draw_chip(self, chip):
        cat = chip["cat"]
        active = self.cat_counts[cat] > 0
        hv = chip["hv"].v
        if active:
            fill = hex_mix("#171329", "#1d1735", hv)
            outline = hex_mix(PRIMARY_LO, PRIMARY_HI, hv)
            text = hex_mix("#c9bcff", "#ffffff", hv)
        else:
            fill = hex_mix(SURFACE, SURFACE_HI, hv)
            outline = hex_mix(BORDER, BORDER_HI, hv)
            text = hex_mix(SECONDARY, TEXT, hv)
        self.canvas.itemconfig(chip["shape"], fill=fill, outline=outline)
        self.canvas.itemconfig(chip["text"], fill=text)
        count = self.cat_counts[cat]
        self.canvas.itemconfig(
            chip["badge"],
            text=str(count) if count else "",
            fill=PRIMARY_HI
        )

    def _chip_click(self, chip):
        folder = self.folder / chip["cat"]
        if folder.is_dir():
            os.startfile(str(folder))
        else:
            self.journal.add("info", f"Папка «{chip['cat']}» ещё не создана")

    def refresh_chips(self):
        for chip in self.chips.values():
            self._draw_chip(chip)

    # --------------------------------------------------------
    # Layout / окно
    # --------------------------------------------------------

    def on_journal_changed(self):
        self.jh_anim.to(self.journal.height_target())

    def _apply_height(self, v):
        self.j_h = v
        self.journal.layout(v)
        self._sync_layout()

    def _sync_layout(self):
        status_y = self.j_top + self.j_h + 22
        self.canvas.coords(self.status_dot,
                           30, status_y - 4, 38, status_y + 4)
        self.canvas.coords(self.status_text, 48, status_y)
        self.canvas.coords(self.status_check, self.W - 28, status_y)
        self.root.geometry(f"{self.W}x{int(status_y + 26)}")

    def _enable_win11_look(self):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            dark = ctypes.c_int(1)
            rounded = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(dark), 4)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(rounded), 4)
            # Тёмный бесшовный title bar (Windows 11)
            def cref(hexcolor):
                r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
                return ctypes.c_int(b << 16 | g << 8 | r)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(cref("#0B0F17")), 4)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 36, ctypes.byref(cref("#9aa3b2")), 4)
        except Exception:
            pass

    def _fade(self, a):
        a = min(1.0, a + 0.09)
        self.root.attributes("-alpha", a)
        if a < 1.0:
            self.root.after(16, lambda: self._fade(a))

    # --------------------------------------------------------
    # Статус
    # --------------------------------------------------------

    def set_status(self, text, color, revert_ms=None):
        self.canvas.itemconfig(self.status_dot, fill=color)
        self.canvas.itemconfig(self.status_text, text=text, fill=SECONDARY)
        if self._status_job:
            self.root.after_cancel(self._status_job)
            self._status_job = None
        if revert_ms:
            self._status_job = self.root.after(
                revert_ms, self.set_status_default)

    def set_status_default(self):
        if self.auto_on:
            folder = str(self.folder)
            if len(folder) > 34:
                folder = "..." + folder[-31:]
            self.set_status(f"Сортировка активна • отслеживается {folder}",
                            SUCCESS)
        else:
            self.set_status("Сортировка остановлена", MUTED)

    def set_last_check(self):
        self.last_check = datetime.now().strftime("%H:%M:%S")
        self.canvas.itemconfig(
            self.status_check,
            text=f"Последняя проверка: {self.last_check}"
        )

    # --------------------------------------------------------
    # Настройки (логика без изменений)
    # --------------------------------------------------------

    def load_settings(self):
        self.settings = {}
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        self.folder = Path(self.settings.get(
            "folder", str(Path.home() / "Downloads")))

    def save_settings(self):
        self.settings["folder"] = str(self.folder)
        self.settings["rename"] = self.tg_rename.value
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def on_closing(self):
        self.auto_on = False
        self.save_settings()
        self.root.destroy()

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Выбери папку")
        if folder:
            self.folder = Path(folder)
            self.refresh_path()
            self.save_settings()
            self.journal.add("info", "Папка изменена", str(self.folder))
            self.set_status_default()

    def open_folder(self):
        if self.folder.is_dir():
            os.startfile(str(self.folder))
        else:
            self.journal.add("error", "Папка не найдена", str(self.folder))

    # --------------------------------------------------------
    # Тумблеры
    # --------------------------------------------------------

    def on_auto(self, value):
        if value:
            if not self.folder.is_dir():
                self.journal.add("error", "Папка не найдена",
                                 str(self.folder))
                self.toasts.show("Ошибка", "Папка не найдена", "error")
                self.tg_auto.set_value(False)
                return
            self.auto_on = True
            self.pending = {}
            self.journal.add("process", "Автосортировка включена",
                             f"Отслеживаю {self.folder}")
            self.set_status_default()
            self.tick()
        else:
            self.auto_on = False
            self.journal.add("info", "Автосортировка остановлена")
            self.set_status_default()

    def on_rename(self, value):
        self.save_settings()
        self.journal.add(
            "info",
            "Дата в имени включена" if value else "Дата в имени выключена"
        )

    def on_autostart(self, value):
        if set_autostart(value):
            self.journal.add(
                "success" if value else "info",
                "Автозапуск включён" if value else "Автозапуск выключен",
                "Значение в реестре Windows обновлено"
            )
        else:
            self.tg_start.set_value(not value)
            self.journal.add("error", "Не удалось изменить автозапуск")

    # --------------------------------------------------------
    # СОРТИРОВКА (логика не изменена)
    # --------------------------------------------------------

    def sort_file(self, path: Path):
        ext = path.suffix.lower()

        category = "Другое"
        for cat, exts in CATEGORIES.items():
            if ext in exts:
                category = cat
                break

        dest_dir = path.parent / category
        dest_dir.mkdir(exist_ok=True)

        name = path.stem

        if self.tg_rename.value:
            date_str = datetime.fromtimestamp(
                path.stat().st_mtime).strftime("%Y-%m-%d")
            name = f"{date_str}_{name}"

        dest = dest_dir / f"{name}{ext}"
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{name}_{counter}{ext}"
            counter += 1

        try:
            shutil.move(str(path), str(dest))
        except (PermissionError, OSError) as e:
            self.journal.add("error", f"Не удалось переместить {path.name}",
                             str(e))
            return None

        self.count += 1
        self.journal.set_counter(self.count)
        self.cat_counts[category] += 1
        self.refresh_chips()
        self.journal.add("success", path.name, f"→ {category}")

        return (path, dest)

    def sort_now(self):
        if not self.folder.is_dir():
            self.journal.add("error", "Папка не найдена", str(self.folder))
            self.set_status("Во время сортировки возникла ошибка", ERROR,
                            3000)
            return

        self.journal.add("process", "Проверяю файлы…")
        self.set_status("Выполняется сортировка…", PRIMARY)
        self.set_last_check()

        batch = []
        skipped = 0

        for path in sorted(self.folder.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() in TEMP_EXTS:
                continue
            if is_file_locked(path):
                skipped += 1
                continue
            result = self.sort_file(path)
            if result:
                batch.append(result)
            self.pending.pop(path, None)

        if batch:
            self.undo_batches.append(batch)

        if skipped:
            self.journal.add("warn", f"Пропущено файлов: {skipped}",
                             "Они открыты другим процессом")

        if batch:
            self.journal.add("success", "Сортировка завершена",
                             f"Перемещено: {len(batch)}")
            self.set_status(f"Готово • перемещено {len(batch)}",
                            SUCCESS, 4000)
            if len(batch) == 1:
                cat = batch[0][1].parent.name
                self.toasts.show("Готово",
                                 f"Файл перемещён в «{cat}»", "success")
            else:
                self.toasts.show("Готово",
                                 f"Перемещено файлов: {len(batch)}",
                                 "success")
        else:
            self.journal.add("info", "Разбирать нечего",
                             "В папке уже порядок")
            self.set_status_default()

    def tick(self):
        if not self.auto_on:
            return

        self.set_last_check()

        if self.folder.is_dir():
            batch = []

            for path in list(self.pending.keys()):
                if not path.exists():
                    del self.pending[path]

            for path in self.folder.iterdir():
                if not path.is_file():
                    continue
                if path.suffix.lower() in TEMP_EXTS:
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue

                if path in self.pending:
                    if self.pending[path] == size and not is_file_locked(path):
                        result = self.sort_file(path)
                        if result:
                            batch.append(result)
                            self.pending.pop(path, None)
                            continue
                    self.pending[path] = size
                else:
                    self.pending[path] = size

            if batch:
                self.undo_batches.append(batch)
                self.journal.add("success", "Сортировка завершена",
                                 f"Перемещено: {len(batch)}")
                self.set_status(f"Готово • перемещено {len(batch)}",
                                SUCCESS, 3000)
                if len(batch) == 1:
                    cat = batch[0][1].parent.name
                    self.toasts.show("Готово",
                                     f"Файл перемещён в «{cat}»", "success")
                else:
                    self.toasts.show("Готово",
                                     f"Перемещено файлов: {len(batch)}",
                                     "success")

        self.root.after(AUTO_INTERVAL_MS, self.tick)

    def undo_last(self):
        if not self.undo_batches:
            self.journal.add("info", "Отменять нечего")
            return

        batch = self.undo_batches.pop()
        restored = 0

        for src, dest in reversed(batch):
            if dest.exists():
                try:
                    shutil.move(str(dest), str(src))
                    restored += 1
                    cat = dest.parent.name
                    if cat in self.cat_counts:
                        self.cat_counts[cat] = max(
                            0, self.cat_counts[cat] - 1)
                except OSError as e:
                    self.journal.add("error",
                                     f"Отмена не удалась: {dest.name}",
                                     str(e))

        self.count = max(0, self.count - restored)
        self.journal.set_counter(self.count)
        self.refresh_chips()
        self.journal.add("info", "Отмена выполнена",
                         f"Возвращено файлов: {restored}")


# ============================================================
# ЗАПУСК
# ============================================================

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()