from __future__ import annotations

import os
import queue
import threading
import time
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from ..config import APP_DESCRIPTOR, APP_NAME, LOGO_PATH, VERSION
from ..database import Database
from ..date_utils import display_bytes, display_date, display_datetime
from ..services.auth_service import AuthService, UserSession
from ..services.audit_service import AuditService
from ..services.backup_service import BackupService
from ..services.dashboard_service import DashboardService
from ..services.entry_service import EntryService
from ..services.inventory_service import InventoryService
from ..services.product_service import ProductService
from ..services.report_service import ReportService
from ..services.sale_service import SaleService
from ..services.settings_service import SettingsService
from .widgets import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    BORDER,
    CARD,
    CARD_HOVER,
    DANGER,
    DANGER_BG,
    FIELD,
    MUTED,
    PANEL,
    SIDEBAR,
    SUCCESS,
    SURFACE,
    TEXT,
    TEXT_SOFT,
    WARNING,
    Badge,
    CalendarField,
    CardFrame,
    Column,
    DarkTable,
    LabeledCombo,
    LabeledEntry,
    NumberStepper,
    PageHeader,
    PasswordField,
    SearchableSelector,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def open_path(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif os.name == "posix":
            import subprocess
            subprocess.Popen(["xdg-open", str(path.parent)])
    except Exception:
        pass


def make_modal(master, title: str, width: int = 560, height: int = 420) -> ctk.CTkToplevel:
    modal = ctk.CTkToplevel(master)
    modal.title(title)
    modal.geometry(f"{width}x{height}")
    modal.configure(fg_color=BG)
    modal.transient(master.winfo_toplevel())
    modal.grab_set()
    modal.resizable(False, False)
    modal.bind("<Escape>", lambda _e: modal.destroy())
    modal.update_idletasks()
    x = master.winfo_toplevel().winfo_rootx() + max(0, (master.winfo_toplevel().winfo_width() - width) // 2)
    y = master.winfo_toplevel().winfo_rooty() + max(0, (master.winfo_toplevel().winfo_height() - height) // 2)
    modal.geometry(f"{width}x{height}+{x}+{y}")
    return modal


def themed_confirm(
    master,
    title: str,
    message: str,
    *,
    confirm_text: str = "Continuar",
    cancel_text: str = "Cancelar",
    danger: bool = False,
) -> bool:
    """Confirmación modal coherente con el tema de la aplicación."""
    result = {"confirmed": False}
    modal = make_modal(master, title, 520, 260)
    modal.protocol("WM_DELETE_WINDOW", lambda: finish(False))

    ctk.CTkLabel(
        modal,
        text=title,
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=TEXT,
    ).pack(anchor="w", padx=26, pady=(26, 8))
    ctk.CTkLabel(
        modal,
        text=message,
        text_color=TEXT_SOFT,
        font=ctk.CTkFont(size=13),
        wraplength=465,
        justify="left",
    ).pack(anchor="w", padx=26, pady=(0, 20))

    actions = ctk.CTkFrame(modal, fg_color="transparent")
    actions.pack(fill="x", padx=26, pady=(6, 24), side="bottom")

    def finish(value: bool) -> None:
        result["confirmed"] = value
        try:
            modal.grab_release()
        except Exception:
            pass
        modal.destroy()

    ctk.CTkButton(
        actions,
        text=cancel_text,
        width=150,
        height=40,
        fg_color="transparent",
        hover_color=CARD_HOVER,
        text_color=TEXT,
        border_width=1,
        border_color=BORDER,
        command=lambda: finish(False),
    ).pack(side="left")
    ctk.CTkButton(
        actions,
        text=confirm_text,
        width=165,
        height=40,
        fg_color=DANGER if danger else ACCENT,
        hover_color=("#DC2626", "#b91c1c") if danger else ACCENT_HOVER,
        command=lambda: finish(True),
    ).pack(side="right")

    modal.bind("<Escape>", lambda _e: finish(False))
    modal.bind("<Return>", lambda _e: finish(True))
    modal.after(60, lambda: modal.focus_force())
    master.wait_window(modal)
    return bool(result["confirmed"])


class LoginWindow(ctk.CTk):
    """Acceso principal de FarmaStock.

    El único recurso gráfico persistente es el logotipo de FarmaStock. El
    fondo azul se genera dinámicamente y los textos/tarjetas son elementos de
    interfaz reales, por lo que el diseño se adapta sin depender de una
    captura o composición rasterizada.
    """

    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.auth = AuthService(db)
        self.settings = SettingsService(db)
        self.session: UserSession | None = None

        self._brand_logo: Image.Image | None = self._load_logo()
        self._hero_bg_photo: ImageTk.PhotoImage | None = None
        self._hero_logo_photo: ImageTk.PhotoImage | None = None
        self._window_icon_photo: ImageTk.PhotoImage | None = None
        self._hero_resize_after: str | None = None

        self.title(f"{APP_NAME} - Acceso")
        self.configure(fg_color=BG)
        self.minsize(1240, 740)
        self.resizable(True, True)
        self.grid_columnconfigure(0, weight=56)
        self.grid_columnconfigure(1, weight=44)
        self.grid_rowconfigure(0, weight=1)
        self._set_window_icon()

        # Panel de marca: degradado generado en tiempo de ejecución. No usa
        # fotografías ni capturas; únicamente el logo suministrado por el equipo.
        self.hero_canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg="#07162C")
        self.hero_canvas.grid(row=0, column=0, sticky="nsew")
        self.hero_canvas.bind("<Configure>", self._schedule_hero_redraw)

        right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")

        self.theme_btn = ctk.CTkButton(
            right,
            text="",
            width=42,
            height=38,
            fg_color="transparent",
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
            command=self._toggle_theme,
        )
        self.theme_btn.place(relx=0.965, rely=0.035, anchor="ne")
        self._update_theme_button()

        card = ctk.CTkFrame(
            right,
            width=500,
            height=610,
            fg_color=CARD,
            corner_radius=26,
            border_width=1,
            border_color=BORDER,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=46, pady=38)

        ctk.CTkLabel(
            content,
            text="ACCESO AL SISTEMA",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            content,
            text="Bienvenido",
            font=ctk.CTkFont(size=34, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w", pady=(10, 6))
        ctk.CTkLabel(
            content,
            text="Ingrese sus credenciales para acceder a FarmaStock.",
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=14),
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(0, 28))

        self.user_field = LabeledEntry(content, "Usuario", "Ingrese su usuario")
        self.user_field.pack(fill="x", pady=(0, 16))
        self.password_field = PasswordField(content, "Contraseña", "Ingrese su contraseña")
        self.password_field.pack(fill="x", pady=(0, 22))

        ctk.CTkButton(
            content,
            text="Iniciar sesión   →",
            height=48,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._login,
        ).pack(fill="x")

        separator = ctk.CTkFrame(content, height=1, fg_color=BORDER)
        separator.pack(fill="x", pady=(28, 18))

        helper = ctk.CTkFrame(
            content,
            fg_color=PANEL,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
        )
        helper.pack(fill="x")
        helper.grid_columnconfigure(1, weight=1)

        shield = ctk.CTkFrame(
            helper,
            width=48,
            height=48,
            corner_radius=14,
            fg_color=("#DDF7F2", "#11384A"),
        )
        shield.grid(row=0, column=0, rowspan=2, padx=(14, 12), pady=14)
        shield.grid_propagate(False)
        ctk.CTkLabel(
            shield,
            text="✓",
            text_color=("#059669", "#2DD4BF"),
            font=ctk.CTkFont(size=22, weight="bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(
            helper,
            text="Acceso seguro",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT,
        ).grid(row=0, column=1, sticky="sw", pady=(15, 0))
        ctk.CTkLabel(
            helper,
            text="Credenciales asignadas por el administrador del sistema.",
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=11),
            wraplength=325,
            justify="left",
        ).grid(row=1, column=1, sticky="nw", padx=(0, 14), pady=(2, 15))

        ctk.CTkLabel(
            content,
            text=f"Sistema local · {APP_NAME} · Versión {VERSION}",
            text_color=MUTED,
            font=ctk.CTkFont(size=11),
        ).pack(side="bottom", pady=(20, 0))

        self.bind("<Return>", lambda _e: self._login())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(80, self._maximize_on_start)
        self.after(180, self.user_field.focus_set)

    @staticmethod
    def _load_logo() -> Image.Image | None:
        try:
            return Image.open(LOGO_PATH).convert("RGBA")
        except Exception:
            return None

    def _set_window_icon(self) -> None:
        if self._brand_logo is None:
            return
        try:
            # El símbolo ocupa la zona superior del logo; se extrae en memoria
            # para usarlo como icono sin crear otro archivo gráfico en el repo.
            alpha = self._brand_logo.getchannel("A")
            bbox = alpha.getbbox()
            base = self._brand_logo.crop(bbox) if bbox else self._brand_logo
            symbol_height = max(1, int(base.height * 0.73))
            symbol = base.crop((0, 0, base.width, symbol_height))
            sb = symbol.getchannel("A").getbbox()
            if sb:
                symbol = symbol.crop(sb)
            symbol.thumbnail((64, 64), Image.Resampling.LANCZOS)
            self._window_icon_photo = ImageTk.PhotoImage(symbol)
            self.iconphoto(True, self._window_icon_photo)
        except Exception:
            pass

    @staticmethod
    def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def _make_gradient(self, width: int, height: int) -> Image.Image:
        width = max(2, width)
        height = max(2, height)
        c0 = (3, 17, 42)
        c1 = (7, 49, 106)
        c2 = (10, 92, 172)
        strip = Image.new("RGB", (width, 1))
        px = strip.load()
        for x in range(width):
            t = x / max(1, width - 1)
            if t < 0.58:
                color = self._mix(c0, c1, t / 0.58)
            else:
                color = self._mix(c1, c2, (t - 0.58) / 0.42)
            px[x, 0] = color
        bg = strip.resize((width, height))

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        # Formas abstractas que recuerdan el lenguaje visual del dashboard.
        draw.ellipse((-int(width * .22), -int(height * .20), int(width * .45), int(height * .48)), fill=(30, 116, 255, 45))
        draw.ellipse((int(width * .50), -int(height * .28), int(width * 1.12), int(height * .36)), fill=(0, 214, 190, 24))
        draw.ellipse((int(width * .40), int(height * .58), int(width * 1.18), int(height * 1.28)), fill=(22, 97, 255, 38))
        # Líneas y cruz médica muy sutiles.
        line = (89, 163, 255, 32)
        for offset in (0, 16, 32):
            draw.arc((int(width*.66)-offset, int(height*.13)-offset, int(width*1.04)+offset, int(height*.55)+offset), 190, 325, fill=line, width=2)
        cx, cy = int(width * .86), int(height * .42)
        s = max(34, int(min(width, height) * .055))
        draw.rounded_rectangle((cx-s//3, cy-s, cx+s//3, cy+s), radius=8, outline=(73, 145, 255, 35), width=3)
        draw.rounded_rectangle((cx-s, cy-s//3, cx+s, cy+s//3), radius=8, outline=(73, 145, 255, 35), width=3)
        return Image.alpha_composite(bg.convert("RGBA"), overlay)

    @staticmethod
    def _rounded_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, radius: float, **kwargs):
        r = min(radius, (x2-x1)/2, (y2-y1)/2)
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    def _schedule_hero_redraw(self, event) -> None:
        if self._hero_resize_after is not None:
            try:
                self.after_cancel(self._hero_resize_after)
            except Exception:
                pass
        width = max(1, int(event.width))
        height = max(1, int(event.height))
        self._hero_resize_after = self.after(70, lambda: self._draw_hero(width, height))

    def _draw_hero(self, width: int, height: int) -> None:
        """Dibuja un hero minimalista y estable, sin fotografías ni UI rasterizada."""
        self._hero_resize_after = None
        canvas = self.hero_canvas
        canvas.delete("all")
        if width < 2 or height < 2:
            return

        bg = self._make_gradient(width, height)
        self._hero_bg_photo = ImageTk.PhotoImage(bg)
        canvas.create_image(0, 0, image=self._hero_bg_photo, anchor="nw")

        scale = max(0.86, min(1.14, height / 900))
        margin = max(56, int(width * 0.075))
        content_width = min(int(width * 0.76), 720)
        y = max(72, int(height * 0.10))

        # Usamos únicamente el símbolo del logo como elemento de marca. El nombre
        # se dibuja como texto real para mantener máxima nitidez y legibilidad.
        if self._brand_logo is not None:
            try:
                alpha = self._brand_logo.getchannel("A")
                bbox = alpha.getbbox()
                base = self._brand_logo.crop(bbox) if bbox else self._brand_logo.copy()
                # El símbolo ocupa aproximadamente el 70 % superior del archivo.
                symbol = base.crop((0, 0, base.width, max(1, int(base.height * 0.70))))
                sb = symbol.getchannel("A").getbbox()
                if sb:
                    symbol = symbol.crop(sb)
                target = max(72, int(92 * scale))
                symbol.thumbnail((target, target), Image.Resampling.LANCZOS)
                self._hero_logo_photo = ImageTk.PhotoImage(symbol)
                canvas.create_image(margin, y, image=self._hero_logo_photo, anchor="nw")
                y += symbol.height + int(18 * scale)
            except Exception:
                pass

        canvas.create_text(
            margin, y, text=APP_NAME, anchor="nw", fill="#F8FAFC",
            font=("Segoe UI", int(42 * scale), "bold")
        )
        y += int(58 * scale)
        canvas.create_text(
            margin, y, text=APP_DESCRIPTOR, anchor="nw", fill="#D8E7FB",
            font=("Segoe UI", int(17 * scale), "bold")
        )
        y += int(38 * scale)
        canvas.create_text(
            margin, y,
            text="Control de productos, lotes, ventas y vencimientos en una sola aplicación.",
            anchor="nw", fill="#BFD1E8", font=("Segoe UI", int(13 * scale)),
            width=content_width,
        )

        # Beneficios compactos, sin tarjetas pesadas: mejoran la lectura y
        # mantienen el acceso visualmente limpio.
        y += int(78 * scale)
        benefits = [
            ("▣", "Inventario al día", "Existencias actualizadas con cada movimiento.", "#2DD4BF"),
            ("◫", "Lotes y vencimientos", "Seguimiento por lote y control de caducidad.", "#60A5FA"),
            ("▤", "Reportes y respaldos", "Información local protegida y disponible.", "#A78BFA"),
        ]
        for icon, title, subtitle, accent in benefits:
            icon_x = margin
            icon_y = y + int(8 * scale)
            canvas.create_oval(
                icon_x, icon_y, icon_x + int(42 * scale), icon_y + int(42 * scale),
                fill="#103E78", outline="#2A5E95", width=1
            )
            canvas.create_text(
                icon_x + int(21 * scale), icon_y + int(21 * scale),
                text=icon, fill=accent, font=("Segoe UI", int(17 * scale), "bold")
            )
            tx = icon_x + int(58 * scale)
            canvas.create_text(
                tx, y, text=title, anchor="nw", fill="#F8FAFC",
                font=("Segoe UI", int(13 * scale), "bold")
            )
            canvas.create_text(
                tx, y + int(27 * scale), text=subtitle, anchor="nw",
                fill="#9EB9D8", font=("Segoe UI", int(11 * scale)), width=content_width - int(70 * scale)
            )
            y += int(78 * scale)

        # Línea final discreta: branding, no contenido publicitario.
        footer_y = min(height - int(54 * scale), y + int(26 * scale))
        canvas.create_line(margin, footer_y, margin + min(content_width, 430), footer_y, fill="#245A94", width=1)
        canvas.create_text(
            margin, footer_y + int(16 * scale),
            text="Gestión local · simple · segura", anchor="nw", fill="#7FA7D1",
            font=("Segoe UI", int(10 * scale))
        )

    def _maximize_on_start(self) -> None:
        """Maximiza el acceso en Windows y usa un fallback multiplataforma."""
        try:
            self.state("zoomed")
            return
        except Exception:
            pass
        try:
            self.attributes("-zoomed", True)
            return
        except Exception:
            pass
        try:
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        except Exception:
            pass

    def _update_theme_button(self) -> None:
        current = ctk.get_appearance_mode().lower()
        self.theme_btn.configure(text="☀" if current == "dark" else "☾")

    def _toggle_theme(self) -> None:
        current = ctk.get_appearance_mode().lower()
        target = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(target)
        try:
            self.settings.set_theme(target)
        except Exception:
            pass
        self._update_theme_button()
        # El panel de marca permanece azul en ambos temas, tal como se definió.
        try:
            self._draw_hero(self.hero_canvas.winfo_width(), self.hero_canvas.winfo_height())
        except Exception:
            pass

    def _login(self) -> None:
        session = self.auth.login(self.user_field.get(), self.password_field.get())
        if not session:
            messagebox.showerror("Acceso", "Usuario o contraseña incorrectos.", parent=self)
            return
        self.session = session
        self.withdraw()
        self.quit()

    def prepare_for_login(self) -> None:
        """Restablece la pantalla de acceso para iniciar una nueva sesión."""
        self.session = None
        try:
            self.user_field.delete(0, "end")
            self.password_field.delete(0, "end")
            if getattr(self.password_field, "visible", False):
                self.password_field.visible = False
                self.password_field.entry.configure(show="•")
                self.password_field.toggle.configure(text="👁")
        except Exception:
            pass
        self.deiconify()
        self.after(40, self._maximize_on_start)
        try:
            self.lift()
            self.focus_force()
            self.after(120, self.user_field.focus_set)
        except Exception:
            pass


class BaseFrame(ctk.CTkFrame):
    def __init__(self, master, app: "MainApp") -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app

    def refresh(self) -> None:
        pass


class KpiCard(ctk.CTkFrame):
    def __init__(self, master, title: str, accent: str, icon_text: str = "•", command=None) -> None:
        super().__init__(master, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        self.command = command
        self.base_color = CARD
        self.accent = accent
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(15, 0))
        icon_box = ctk.CTkFrame(top, width=38, height=38, corner_radius=11, fg_color=("#E8EEF8", "#1a2b47"))
        icon_box.pack(side="left")
        icon_box.pack_propagate(False)
        self.icon = ctk.CTkLabel(icon_box, text=icon_text, text_color=accent, font=ctk.CTkFont(size=17, weight="bold"))
        self.icon.pack(expand=True)
        self.title_label = ctk.CTkLabel(top, text=title, text_color=TEXT_SOFT, font=ctk.CTkFont(size=11, weight="bold"))
        self.title_label.pack(side="left", padx=(10, 0))
        self.value = ctk.CTkLabel(self, text="0", text_color=TEXT, font=ctk.CTkFont(size=35, weight="bold"))
        self.value.pack(anchor="w", padx=18, pady=(10, 3))
        self.hint = ctk.CTkLabel(self, text="Ver detalle →" if command else "", text_color=accent, font=ctk.CTkFont(size=10))
        self.hint.pack(anchor="w", padx=18, pady=(0, 14))
        if command:
            for widget in (self, top, icon_box, self.title_label, self.icon, self.value, self.hint):
                widget.bind("<Button-1>", lambda _e: command())
                widget.bind("<Enter>", lambda _e: self.configure(fg_color=CARD_HOVER, border_color=accent))
                widget.bind("<Leave>", lambda _e: self.configure(fg_color=self.base_color, border_color=BORDER))

    def set(self, value: str) -> None:
        self.value.configure(text=value)


class DashboardFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        PageHeader(self, "Inicio", "Resumen general del negocio y del estado actual del inventario.", action=self.show_help).pack(fill="x", padx=24, pady=(22, 12))
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=24)
        for c in range(3):
            stats.grid_columnconfigure(c, weight=1)
        items = [
            ("products", "Productos activos", SUCCESS, "▦", lambda: self.app.show("Productos") if self.app.session.is_admin else self.app.show("Inventario")),
            ("sales_today", "Ventas del día", ACCENT, "🛒", lambda: self.app.show("Ventas")),
            ("sales_total_today", "Total vendido hoy", "#8b5cf6", "$", lambda: self.app.show("Ventas")),
            ("low_stock", "Productos con stock bajo", DANGER, "!", lambda: self.app.show("Alertas")),
            ("expiring", "Lotes por vencer (90 días)", WARNING, "⌛", lambda: self.app.show("Alertas")),
            ("expired", "Lotes vencidos", DANGER, "⚠", lambda: self.app.show("Alertas")),
        ]
        self.cards: dict[str, KpiCard] = {}
        for i, (key, title, color, icon_text, cmd) in enumerate(items):
            card = KpiCard(stats, title, color, icon_text, cmd)
            card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=8, pady=8)
            self.cards[key] = card

        lower = ctk.CTkFrame(self, fg_color="transparent")
        lower.pack(fill="both", expand=True, padx=24, pady=(10, 20))
        lower.grid_columnconfigure((0, 1), weight=1)
        lower.grid_rowconfigure(0, weight=1)

        latest_card = CardFrame(lower, "Últimas ventas", "Movimientos de venta registrados recientemente.")
        latest_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.latest_table = DarkTable(latest_card, [Column("id", "Venta", 1, "center"), Column("fecha", "Fecha", 2, "center"), Column("total", "Total", 1, "center"), Column("estado", "Estado", 1, "center")], height=220)
        self.latest_table.pack(fill="both", expand=True, padx=16, pady=(12, 16))

        attention = CardFrame(lower, "Requiere atención", "Acciones pendientes que conviene revisar hoy.")
        attention.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.attention = ctk.CTkFrame(attention, fg_color="transparent")
        self.attention.pack(fill="both", expand=True, padx=18, pady=(14, 8))
        quick = ctk.CTkFrame(attention, fg_color="transparent")
        quick.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkButton(quick, text="Nueva venta", height=40, command=lambda: self.app.show("Ventas")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(quick, text="Registrar entrada", height=40, fg_color="#0f766e", hover_color="#0d5f58", command=lambda: self.app.show("Entradas")).pack(side="left")

    def show_help(self):
        messagebox.showinfo("Inicio", "Las tarjetas superiores son interactivas. Puede abrir directamente la sección relacionada haciendo clic sobre cada indicador. Los valores de stock consideran únicamente existencias vendibles y separan los lotes vencidos.")

    def refresh(self):
        data = self.app.dashboard_service.summary()
        for key, value in data.items():
            self.cards[key].set(f"${value:.2f}" if key == "sales_total_today" else str(value))
        latest = []
        for r in self.app.dashboard_service.latest_sales(5):
            latest.append({"id": r["id"], "fecha": display_datetime(r["fecha_hora"]), "total": f"${r['total']:.2f}", "estado": r["estado"]})
        self.latest_table.set_rows(latest, badge_resolver=lambda key, row: (row[key].title(), "success" if row[key] == "CONFIRMADA" else "danger") if key == "estado" else None)
        for child in self.attention.winfo_children():
            child.destroy()
        notes = [
            (f"{data['expired']} lote(s) vencido(s)", "danger" if data["expired"] else "neutral"),
            (f"{data['low_stock']} producto(s) con stock bajo", "danger" if data["low_stock"] else "neutral"),
            (f"{data['expiring']} lote(s) próximo(s) a vencer", "warning" if data["expiring"] else "neutral"),
        ]
        for text, kind in notes:
            row = ctk.CTkFrame(self.attention, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
            row.pack(fill="x", pady=5)
            Badge(row, "Atención" if kind != "neutral" else "OK", kind).pack(side="left", padx=10, pady=9)
            ctk.CTkLabel(row, text=text, text_color=TEXT).pack(side="left", padx=4)


class ProductsFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        self._search_after_id = None
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(22, 12))
        PageHeader(header, "Productos", "Catálogo de medicamentos y artículos disponibles en el sistema.").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(header, text="+ Nuevo producto", height=40, width=150, command=self.open_product_modal).pack(side="right", pady=(14, 0))

        toolbar = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        toolbar.pack(fill="x", padx=24, pady=(0, 12))
        search_wrap = ctk.CTkFrame(toolbar, fg_color="transparent")
        search_wrap.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        ctk.CTkLabel(search_wrap, text="⌕", text_color=MUTED, font=ctk.CTkFont(size=18)).pack(side="left", padx=(0, 8))
        self.search = ctk.CTkEntry(search_wrap, placeholder_text="Buscar por nombre, ubicación o unidad...", height=38, fg_color=FIELD, border_width=1, border_color=BORDER, text_color=TEXT, placeholder_text_color=MUTED)
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda _e: self._schedule_search_refresh())
        self.count_label = ctk.CTkLabel(toolbar, text="0 productos", text_color=TEXT_SOFT)
        self.count_label.pack(side="right", padx=16)

        list_card = CardFrame(self, "Listado de productos", "Use las acciones de cada fila para editar o cambiar el estado sin perder el historial.")
        list_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DarkTable(list_card, [Column("id", "ID", 1, "center"), Column("nombre", "Producto", 3), Column("unidad", "Unidad", 1, "center"), Column("precio", "Precio", 1, "center"), Column("minimo", "Mínimo", 1, "center"), Column("ubicacion", "Ubicación", 2), Column("total", "Total", 1, "center"), Column("vendible", "Vendible", 1, "center"), Column("estado", "Estado", 1, "center"), Column("__actions__", "Acciones", 2, "center")], height=500)
        self.table.pack(fill="both", expand=True, padx=16, pady=(12, 16))

    def _schedule_search_refresh(self):
        if self._search_after_id is not None:
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self._search_after_id = self.after(180, self._run_search_refresh)

    def _run_search_refresh(self):
        self._search_after_id = None
        self.refresh()

    def open_product_modal(self, product_id: int | None = None):
        editing = product_id is not None
        product = self.app.product_service.get_product(product_id) if editing else None
        modal = make_modal(self, "Editar producto" if editing else "Nuevo producto", 650, 500)
        ctk.CTkLabel(modal, text="Editar producto" if editing else "Nuevo producto", font=ctk.CTkFont(size=25, weight="bold"), text_color=TEXT).pack(anchor="w", padx=26, pady=(24, 3))
        ctk.CTkLabel(modal, text="Complete la información base. El inventario se modifica mediante entradas, ventas y ajustes.", text_color=TEXT_SOFT, wraplength=590, justify="left").pack(anchor="w", padx=26)
        form = ctk.CTkFrame(modal, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=18)
        form.grid_columnconfigure((0, 1), weight=1)
        name = LabeledEntry(form, "Nombre del producto", "Ej. Palagrip")
        unit = LabeledCombo(form, "Unidad de control", ["Blíster", "Unidad"])
        price = LabeledEntry(form, "Precio de venta", "Ej. 4.00")
        minimum = LabeledEntry(form, "Stock mínimo", "Ej. 5")
        location = LabeledEntry(form, "Ubicación", "Ej. Vitrina 1")
        name.grid(row=0, column=0, columnspan=2, padx=6, pady=8, sticky="ew")
        unit.grid(row=1, column=0, padx=6, pady=8, sticky="ew")
        price.grid(row=1, column=1, padx=6, pady=8, sticky="ew")
        minimum.grid(row=2, column=0, padx=6, pady=8, sticky="ew")
        location.grid(row=2, column=1, padx=6, pady=8, sticky="ew")
        if product:
            name.set(product["nombre"]); unit.set(product["unidad_control"]); price.set(str(product["precio"])); minimum.set(str(product["stock_minimo"])); location.set(product["ubicacion"] or "")
            if self.app.product_service.has_history(product_id):
                unit.set_enabled(False)
                ctk.CTkLabel(
                    form,
                    text="La unidad de control está bloqueada porque este producto ya tiene historial de inventario.",
                    text_color=("#92400E", "#fcd34d"),
                    font=ctk.CTkFont(size=10),
                    wraplength=560,
                    justify="left",
                ).grid(row=3, column=0, columnspan=2, padx=6, pady=(2, 0), sticky="w")
        else:
            unit.set("Blíster")
        actions = ctk.CTkFrame(modal, fg_color="transparent")
        actions.pack(fill="x", padx=26, pady=(0, 22))
        ctk.CTkButton(actions, text="Cancelar", width=110, height=40, fg_color="transparent", hover_color=CARD_HOVER, border_width=1, border_color=BORDER, command=modal.destroy).pack(side="right", padx=(8, 0))
        def save():
            try:
                precio = float(price.get() or 0)
                minimo = int(minimum.get() or 0)
                if editing:
                    self.app.product_service.update_product(product_id, name.get(), unit.get(), precio, minimo, location.get())
                    self.app.audit_service.log("EDITAR_PRODUCTO", user_id=self.app.session.id, entity="PRODUCTO", entity_id=product_id, detail=name.get())
                else:
                    new_id = self.app.product_service.create_product(name.get(), unit.get(), precio, minimo, location.get())
                    self.app.audit_service.log("CREAR_PRODUCTO", user_id=self.app.session.id, entity="PRODUCTO", entity_id=new_id, detail=name.get())
                modal.destroy(); self.app.refresh_dependents()
                self.app.toast("Producto actualizado correctamente." if editing else "Producto registrado correctamente.", "success")
            except Exception as exc:
                messagebox.showerror("Productos", str(exc), parent=modal)
        ctk.CTkButton(actions, text="Guardar cambios" if editing else "Crear producto", width=140, height=40, command=save).pack(side="right")
        modal.bind("<Return>", lambda _e: save())

    def toggle_product(self, product_id: int):
        p = self.app.product_service.get_product(product_id)
        if not p:
            return
        new_state = not bool(p["activo"])
        action = "activar" if new_state else "desactivar"
        if not messagebox.askyesno("Productos", f"¿Desea {action} el producto {p['nombre']}?"):
            return
        try:
            self.app.product_service.set_active(product_id, new_state)
            self.app.audit_service.log(
                "ACTIVAR_PRODUCTO" if new_state else "DESACTIVAR_PRODUCTO",
                user_id=self.app.session.id,
                entity="PRODUCTO",
                entity_id=product_id,
                detail=str(p["nombre"]),
            )
            self.app.refresh_dependents()
            self.app.toast(f"Producto {action}do correctamente.", "success")
        except Exception as exc:
            messagebox.showerror("Productos", str(exc), parent=self)

    def refresh(self):
        term = self.search.get().strip().lower()
        rows = []
        for p in self.app.product_service.list_products(include_inactive=True):
            haystack = f"{p['nombre']} {p['unidad_control']} {p['ubicacion'] or ''}".lower()
            if term and term not in haystack:
                continue
            rows.append({"id": p["id"], "nombre": p["nombre"], "unidad": p["unidad_control"], "precio": f"${p['precio']:.2f}", "minimo": p["stock_minimo"], "ubicacion": p["ubicacion"] or "—", "total": p["stock_total"], "vendible": p["stock_vendible"], "estado": "Activo" if p["activo"] else "Inactivo", "activo": bool(p["activo"])})
        self.count_label.configure(text=f"{len(rows)} producto{'s' if len(rows) != 1 else ''}")
        def actions(parent, row):
            ctk.CTkButton(parent, text="Editar", width=62, height=28, fg_color="#31445f", hover_color="#3b5272", command=lambda rid=row["id"]: self.open_product_modal(rid)).pack(side="left", padx=3)
            has_stock = int(row["total"]) > 0
            if row["activo"] and has_stock:
                ctk.CTkButton(parent, text="Con stock", width=82, height=28, state="disabled", fg_color="#475569").pack(side="left", padx=3)
            else:
                ctk.CTkButton(parent, text="Desactivar" if row["activo"] else "Activar", width=82, height=28, fg_color="#334155" if row["activo"] else "#0f766e", hover_color="#475569" if row["activo"] else "#0d5f58", command=lambda rid=row["id"]: self.toggle_product(rid)).pack(side="left", padx=3)
        self.table.set_rows(rows, badge_resolver=lambda key, row: (row["estado"], "success" if row["activo"] else "neutral") if key == "estado" else None, action_builder=actions)


class EntriesFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(22, 12))
        PageHeader(header, "Entradas de mercadería", "Historial de lotes recibidos, vencimientos y responsables de registro.").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(header, text="+ Registrar entrada", height=40, width=150, command=self.open_entry_modal).pack(side="right", pady=(14, 0))

        summary = ctk.CTkFrame(self, fg_color="transparent")
        summary.pack(fill="x", padx=24, pady=(0, 12))
        summary.grid_columnconfigure((0, 1, 2), weight=1)
        self.stat_entries = self._mini_stat(summary, 0, "Entradas registradas", "0", ACCENT)
        self.stat_active = self._mini_stat(summary, 1, "Lotes con existencia", "0", SUCCESS)
        self.stat_expiring = self._mini_stat(summary, 2, "Próximos a vencer", "0", WARNING)

        history = CardFrame(self, "Historial de entradas", "Use Observación para complementar información o Anular cuando el lote no tenga movimientos posteriores.")
        history.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DarkTable(history, [Column("id", "Entrada", 1, "center"), Column("fecha", "Fecha", 2, "center"), Column("producto", "Producto", 2), Column("unidad", "Unidad", 1, "center"), Column("lote", "Lote interno", 2, "center"), Column("ingreso", "Ingresó", 1, "center"), Column("actual", "Actual", 1, "center"), Column("vence", "Vence", 2, "center"), Column("estado", "Estado", 1, "center"), Column("usuario", "Usuario", 2), Column("__actions__", "Acciones", 2, "center")], height=480)
        self.table.pack(fill="both", expand=True, padx=16, pady=(12, 16))

    def _mini_stat(self, master, col, title, value, color):
        card = ctk.CTkFrame(master, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        card.grid(row=0, column=col, sticky="ew", padx=6)
        ctk.CTkLabel(card, text=title, text_color=TEXT_SOFT, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(11, 0))
        lbl = ctk.CTkLabel(card, text=value, text_color=color, font=ctk.CTkFont(size=24, weight="bold"))
        lbl.pack(anchor="w", padx=14, pady=(2, 11))
        return lbl

    def _product_items(self):
        # En Entradas se muestran TODOS los productos activos, incluso con stock
        # 0, porque precisamente este módulo sirve para reponer existencias.
        items = []
        for p in self.app.product_service.list_products():
            items.append({
                "label": f"{p['nombre']} ({p['unidad_control']}) · stock actual {int(p['stock_total'])}",
                "value": int(p["id"]),
                "enabled": True,
            })
        return items

    def open_entry_modal(self, product_id: int | None = None):
        modal = make_modal(self, "Registrar entrada", 720, 560)
        ctk.CTkLabel(modal, text="Registrar entrada de mercadería", font=ctk.CTkFont(size=25, weight="bold"), text_color=TEXT).pack(anchor="w", padx=26, pady=(24, 3))
        ctk.CTkLabel(modal, text="Seleccione un producto activo y registre la cantidad recibida. Aquí se muestran también los productos con stock 0, porque este módulo se utiliza para reponer existencias. El sistema generará el correlativo interno del lote automáticamente.", text_color=TEXT_SOFT, wraplength=650, justify="left").pack(anchor="w", padx=26)
        form = ctk.CTkFrame(modal, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=18)
        form.grid_columnconfigure((0, 1), weight=1)
        product = SearchableSelector(form, "Producto", "Escriba para buscar y seleccionar")
        product.set_items(self._product_items())
        qty = NumberStepper(form, "Cantidad recibida", "0", minimum=1)
        exp = CalendarField(form, "Vencimiento")
        manufacturer = LabeledEntry(form, "Lote fabricante", "Opcional")
        notes = LabeledEntry(form, "Observación", "Opcional")
        product.grid(row=0, column=0, columnspan=2, padx=6, pady=8, sticky="ew")
        qty.grid(row=1, column=0, padx=6, pady=8, sticky="ew")
        exp.grid(row=1, column=1, padx=6, pady=8, sticky="ew")
        manufacturer.grid(row=2, column=0, padx=6, pady=8, sticky="ew")
        notes.grid(row=2, column=1, padx=6, pady=8, sticky="ew")
        if product_id:
            product.set_by_value(product_id)
        actions = ctk.CTkFrame(modal, fg_color="transparent")
        actions.pack(fill="x", padx=26, pady=(0, 22))
        ctk.CTkButton(actions, text="Cancelar", width=110, height=40, fg_color="transparent", hover_color=CARD_HOVER, border_width=1, border_color=BORDER, command=modal.destroy).pack(side="right", padx=(8, 0))
        def register():
            try:
                pid = product.get_value()
                if not pid:
                    raise ValueError("Seleccione un producto de la lista de resultados.")
                result = self.app.entry_service.register_entry(pid, qty.get_int(), exp.get_iso(), self.app.session.id, manufacturer.get(), notes.get())
                modal.destroy(); self.app.refresh_dependents()
                self.app.toast(f"Entrada registrada correctamente · Lote {result['internal_code']}", "success")
            except Exception as exc:
                messagebox.showerror("Entrada", str(exc), parent=modal)
        ctk.CTkButton(actions, text="Registrar entrada", width=150, height=40, command=register).pack(side="right")
        modal.bind("<Return>", lambda _e: register())

    def preselect_product(self, product_id: int):
        self.open_entry_modal(product_id)

    def edit_metadata(self, row):
        modal = make_modal(self, f"Entrada #{row['id']}", 540, 390)
        ctk.CTkLabel(modal, text="Editar datos descriptivos", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT).pack(anchor="w", padx=24, pady=(22, 6))
        ctk.CTkLabel(
            modal,
            text="Puede corregir el lote del fabricante y la observación sin alterar cantidades, vencimiento ni movimientos de inventario.",
            text_color=TEXT_SOFT,
            wraplength=490,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 8))
        manufacturer = LabeledEntry(modal, "Lote fabricante", "Opcional")
        manufacturer.pack(fill="x", padx=24, pady=(10, 6))
        manufacturer.set(row.get("lote_fabricante", ""))
        observation = LabeledEntry(modal, "Observación", "Ingrese una observación")
        observation.pack(fill="x", padx=24, pady=6)
        observation.set(row.get("observacion", ""))
        actions = ctk.CTkFrame(modal, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(16, 18))
        ctk.CTkButton(actions, text="Cancelar", width=100, height=38, fg_color="transparent", hover_color=CARD_HOVER, border_width=1, border_color=BORDER, command=modal.destroy).pack(side="right", padx=(8, 0))
        def save():
            try:
                self.app.entry_service.update_entry_metadata(row["id"], manufacturer.get(), observation.get())
                self.app.audit_service.log("EDITAR_ENTRADA_METADATA", user_id=self.app.session.id, entity="ENTRADA", entity_id=row["id"], detail="Corrección de lote fabricante/observación")
                modal.destroy()
                self.refresh()
                self.app.toast("Datos descriptivos actualizados correctamente.", "success")
            except Exception as exc:
                messagebox.showerror("Entrada", str(exc), parent=modal)
        ctk.CTkButton(actions, text="Guardar cambios", width=130, height=38, command=save).pack(side="right")
        modal.bind("<Return>", lambda _e: save())

    def cancel_entry(self, row):
        modal = make_modal(self, f"Anular entrada #{row['id']}", 540, 350)
        ctk.CTkLabel(modal, text="Anular entrada", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT).pack(anchor="w", padx=24, pady=(22, 4))
        ctk.CTkLabel(modal, text=f"{row['producto']} · {row['lote']} · ingresó {row['ingreso']} {row['unidad']}", text_color=TEXT_SOFT).pack(anchor="w", padx=24)
        ctk.CTkLabel(modal, text="Solo se permitirá la anulación si el lote no tuvo ventas ni ajustes posteriores.", text_color=("#92400E", "#fcd34d"), wraplength=470, justify="left").pack(anchor="w", padx=24, pady=(14, 4))
        reason = LabeledEntry(modal, "Motivo de anulación", "Explique el error de registro")
        reason.pack(fill="x", padx=24, pady=12)
        def confirm():
            try:
                self.app.entry_service.cancel_entry(row["id"], reason.get(), self.app.session.id); modal.destroy(); self.app.refresh_dependents(); self.app.toast("Entrada anulada correctamente.", "success")
            except Exception as exc:
                messagebox.showerror("Entrada", str(exc), parent=modal)
        ctk.CTkButton(modal, text="Confirmar anulación", fg_color=DANGER, hover_color="#dc2626", command=confirm).pack(anchor="e", padx=24, pady=12)

    def refresh(self):
        today = date.today(); rows = []; active=0; expiring=0
        records = self.app.entry_service.list_entries()
        for r in records:
            exp_iso = r["fecha_vencimiento"]; urgency = "normal"
            if exp_iso:
                d = date.fromisoformat(exp_iso); days = (d - today).days
                urgency = "expired" if days < 0 else "soon" if days <= 90 else "normal"
                if 0 <= days <= 90 and r["estado"] == "ACTIVA" and int(r["cantidad_actual"]) > 0: expiring += 1
            if r["estado"] == "ACTIVA" and int(r["cantidad_actual"]) > 0:
                active += 1
            rows.append({"id": r["id"], "fecha": display_datetime(r["fecha_hora"]), "producto": r["producto"], "unidad": r["unidad_control"], "lote": r["codigo_interno"], "ingreso": r["cantidad_inicial"], "actual": r["cantidad_actual"], "vence": display_date(exp_iso), "estado": r["estado"].title(), "usuario": r["usuario"], "urgency": urgency, "observacion": r["observacion"] or "", "lote_fabricante": r["lote_fabricante"] or "", "raw_estado": r["estado"], "can_cancel": bool(r["puede_anular"])})
        self.stat_entries.configure(text=str(len(records))); self.stat_active.configure(text=str(active)); self.stat_expiring.configure(text=str(expiring))
        def badges(key, row):
            if key == "estado": return (row["estado"], "success" if row["raw_estado"] == "ACTIVA" else "danger")
            if key == "vence" and row["urgency"] == "expired": return (row["vence"], "danger")
            if key == "vence" and row["urgency"] == "soon": return (row["vence"], "warning")
            return None
        def actions(parent, row):
            if row["raw_estado"] == "ACTIVA":
                ctk.CTkButton(parent, text="Editar", width=62, height=28, fg_color="#31445f", hover_color="#3b5272", command=lambda rr=row: self.edit_metadata(rr)).pack(side="left", padx=3)
                if self.app.session.is_admin:
                    if row["can_cancel"]:
                        ctk.CTkButton(parent, text="Anular", width=62, height=28, fg_color=DANGER, hover_color="#dc2626", command=lambda rr=row: self.cancel_entry(rr)).pack(side="left", padx=3)
                    else:
                        ctk.CTkButton(parent, text="No anulable", width=82, height=28, state="disabled", fg_color="#475569").pack(side="left", padx=3)
            else:
                ctk.CTkButton(parent, text="Historial", width=72, height=28, state="disabled", fg_color="#475569").pack(side="left", padx=3)
        self.table.set_rows(rows, badge_resolver=badges, action_builder=actions)


class SalesFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.cart: list[dict[str, int]] = []
        self._confirming = False
        PageHeader(self, "Ventas", "Busque productos vendibles, agregue cantidades al carrito y confirme al finalizar.").pack(fill="x", padx=24, pady=(22, 12))
        layout = ctk.CTkFrame(self, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        layout.grid_columnconfigure(0, weight=3)
        layout.grid_columnconfigure(1, weight=2)
        layout.grid_rowconfigure(0, weight=1)

        new_card = CardFrame(layout, "Nueva venta", "Solo se muestran productos activos con stock vendible. Los lotes dentro del margen de bloqueo por vencimiento no se ofrecen para venta.")
        new_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        form = ctk.CTkFrame(new_card, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(14, 10))
        self.product = SearchableSelector(form, "Producto", "Escriba para buscar el producto")
        self.product.set_on_select(lambda _value: self._update_sale_actions())
        self.product.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.qty = NumberStepper(form, "Cantidad", "0", minimum=1)
        self.qty.pack(side="left", fill="x", padx=8)
        self.qty.entry.bind("<Return>", lambda _e: self.add_item())
        self.add_btn = ctk.CTkButton(form, text="Agregar", width=120, height=40, state="disabled", command=self.add_item)
        self.add_btn.pack(side="left", padx=(8, 0), pady=(18, 0))
        self.cart_table = DarkTable(new_card, [Column("producto", "Producto", 3), Column("cantidad", "Cantidad", 1, "center"), Column("unidad", "Unidad", 1, "center"), Column("precio", "Precio", 1, "center"), Column("subtotal", "Subtotal", 1, "center"), Column("__actions__", "Acciones", 2, "center")], height=330, row_key="product_id")
        self.cart_table.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        footer = ctk.CTkFrame(new_card, fg_color="transparent")
        footer.pack(fill="x", padx=18, pady=(0, 18))
        self.total_label = ctk.CTkLabel(footer, text="Total: $0.00", font=ctk.CTkFont(size=31, weight="bold"), text_color=TEXT)
        self.total_label.pack(side="left")
        self.confirm_btn = ctk.CTkButton(footer, text="Confirmar venta", width=165, height=42, state="disabled", command=self.confirm_sale)
        self.confirm_btn.pack(side="right")

        hist_card = CardFrame(layout, "Historial reciente", "Consulte el detalle de cada venta. Las anulaciones solicitan motivo y confirmación.")
        hist_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.sales_table = DarkTable(hist_card, [Column("id", "Venta", 1, "center"), Column("fecha", "Fecha", 2, "center"), Column("total", "Total", 1, "center"), Column("estado", "Estado", 2, "center"), Column("usuario", "Usuario", 2), Column("__actions__", "Acciones", 3, "center")], height=420)
        self.sales_table.pack(fill="both", expand=True, padx=16, pady=(12, 16))

    def _update_sale_actions(self):
        if hasattr(self, "add_btn"):
            self.add_btn.configure(state="normal" if self.product.get_value() else "disabled")
        if hasattr(self, "confirm_btn"):
            self.confirm_btn.configure(state="disabled" if self._confirming or not self.cart else "normal")

    def refresh_products(self):
        items = []
        for p in self.app.product_service.list_products():
            stock = int(p["stock_vendible"])
            if stock <= 0:
                continue
            suffix = f"stock {stock} {p['unidad_control']} · ${p['precio']:.2f}"
            items.append({"label": f"{p['nombre']} · {suffix}", "value": int(p["id"]), "enabled": True})
        current = self.product.get_value()
        self.product.set_items(items)
        if current is not None:
            self.product.set_by_value(current)
        self._update_sale_actions()

    def add_item(self):
        try:
            pid = self.product.get_value()
            if not pid:
                raise ValueError("Seleccione un producto con stock disponible.")
            qty = self.qty.get_int()
            p = self.app.product_service.get_product(pid)
            if not p or int(p["stock_vendible"]) <= 0:
                raise ValueError("El producto seleccionado no tiene stock vendible.")
            existing = next((x for x in self.cart if x["product_id"] == pid), None)
            new_qty = qty + (existing["quantity"] if existing else 0)
            if new_qty > int(p["stock_vendible"]):
                raise ValueError(f"Stock vendible insuficiente. Disponible: {p['stock_vendible']}.")
            if existing:
                existing["quantity"] = new_qty
            else:
                self.cart.append({"product_id": pid, "quantity": qty})
            # Dejar el formulario listo para capturar el siguiente producto.
            self.product.clear()
            self.qty.clear()
            self.render_cart()
            self.product.focus_input()
            self._update_sale_actions()
        except Exception as exc:
            messagebox.showerror("Venta", str(exc))

    def remove_item(self, product_id: int):
        self.cart = [x for x in self.cart if x["product_id"] != product_id]
        self.render_cart()

    def change_cart_quantity(self, product_id: int, delta: int):
        """Edita la cantidad en el carrito sin obligar a quitar y buscar de nuevo."""
        item = next((x for x in self.cart if x["product_id"] == product_id), None)
        if not item:
            return
        p = self.app.product_service.get_product(product_id)
        if not p:
            messagebox.showerror("Venta", "El producto ya no está disponible.")
            return
        new_qty = int(item["quantity"]) + int(delta)
        if new_qty < 1:
            return
        available = int(p["stock_vendible"])
        if new_qty > available:
            messagebox.showwarning("Venta", f"No puede superar el stock vendible. Disponible: {available}.")
            return
        item["quantity"] = new_qty
        self.render_cart()

    def render_cart(self):
        rows = []
        total = 0.0
        valid_cart = []
        for item in self.cart:
            p = self.app.product_service.get_product(item["product_id"])
            if not p or not p["activo"]:
                continue
            valid_cart.append(item)
            subtotal = round(float(p["precio"]) * item["quantity"], 2)
            total += subtotal
            rows.append({"product_id": item["product_id"], "producto": p["nombre"], "cantidad": item["quantity"], "unidad": p["unidad_control"], "precio": f"${p['precio']:.2f}", "subtotal": f"${subtotal:.2f}"})
        self.cart = valid_cart
        def actions(parent, row):
            pid = int(row["product_id"])
            current = int(row["cantidad"])
            product = self.app.product_service.get_product(pid)
            available = int(product["stock_vendible"]) if product else current
            ctk.CTkButton(
                parent,
                text="−",
                width=30,
                height=28,
                fg_color="#31445f",
                hover_color="#3b5272",
                state="normal" if current > 1 else "disabled",
                command=lambda rid=pid: self.change_cart_quantity(rid, -1),
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                parent,
                text="+",
                width=30,
                height=28,
                fg_color="#31445f",
                hover_color="#3b5272",
                state="normal" if current < available else "disabled",
                command=lambda rid=pid: self.change_cart_quantity(rid, 1),
            ).pack(side="left", padx=2)
            ctk.CTkButton(parent, text="Quitar", width=58, height=28, fg_color="#475569", hover_color="#334155", command=lambda rid=pid: self.remove_item(rid)).pack(side="left", padx=(4, 2))
        self.cart_table.set_rows(rows, action_builder=actions)
        self.total_label.configure(text=f"Total: ${total:.2f}")
        self._update_sale_actions()

    def confirm_sale(self):
        if self._confirming:
            return
        if not self.cart:
            messagebox.showwarning("Venta", "Agregue al menos un producto antes de confirmar.")
            return
        self._confirming = True
        self._update_sale_actions()
        try:
            sale_id = self.app.sale_service.create_sale(self.cart, self.app.session.id)
            self.cart = []
            self.render_cart()
            self.app.refresh_dependents()
            self.app.toast(f"Venta #{sale_id} registrada correctamente.", "success")
            self.product.clear()
            self.qty.clear()
            self.product.focus_input()
        except Exception as exc:
            messagebox.showerror("Venta", str(exc))
        finally:
            self._confirming = False
            self._update_sale_actions()

    def show_sale_detail(self, row):
        sale, items = self.app.sale_service.get_sale_details(row["id"])
        if not sale:
            return
        modal = make_modal(self, f"Detalle de venta #{row['id']}", 700, 520)
        ctk.CTkLabel(modal, text=f"Venta #{sale['id']}", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT).pack(anchor="w", padx=24, pady=(22, 2))
        ctk.CTkLabel(modal, text=f"{display_datetime(sale['fecha_hora'])} · {sale['usuario']} · Total ${sale['total']:.2f}", text_color=TEXT_SOFT).pack(anchor="w", padx=24)
        Badge(modal, sale["estado"].title(), "success" if sale["estado"] == "CONFIRMADA" else "danger").pack(anchor="w", padx=24, pady=12)
        if sale["estado"] == "ANULADA" and sale["motivo_anulacion"]:
            ctk.CTkLabel(modal, text=f"Motivo: {sale['motivo_anulacion']}", text_color=("#991B1B", "#fca5a5"), wraplength=640, justify="left").pack(anchor="w", padx=24, pady=(0, 8))
        table = DarkTable(modal, [Column("producto", "Producto", 3), Column("cantidad", "Cantidad", 1, "center"), Column("unidad", "Unidad", 1, "center"), Column("precio", "Precio", 1, "center"), Column("subtotal", "Subtotal", 1, "center")], height=260)
        table.pack(fill="both", expand=True, padx=24, pady=12)
        rows = [{"producto": i["nombre"], "cantidad": i["cantidad"], "unidad": i["unidad_control"], "precio": f"${i['precio_unitario']:.2f}", "subtotal": f"${i['subtotal']:.2f}"} for i in items]
        table.set_rows(rows)
        ctk.CTkButton(modal, text="Cerrar", fg_color="#475569", hover_color="#334155", command=modal.destroy).pack(anchor="e", padx=24, pady=(0, 18))

    def cancel_sale(self, row):
        modal = make_modal(self, f"Anular venta #{row['id']}", 560, 350)
        ctk.CTkLabel(modal, text="Anular venta", font=ctk.CTkFont(size=23, weight="bold"), text_color=TEXT).pack(anchor="w", padx=24, pady=(22, 4))
        ctk.CTkLabel(modal, text=f"Venta #{row['id']} · {row['fecha']} · {row['total']} · {row['usuario']}", text_color=TEXT_SOFT).pack(anchor="w", padx=24)
        reason = LabeledEntry(modal, "Motivo de anulación", "Explique por qué se anula la venta")
        reason.pack(fill="x", padx=24, pady=18)
        def confirm():
            try:
                self.app.sale_service.cancel_sale(row["id"], reason.get(), self.app.session.id)
                modal.destroy()
                self.app.refresh_dependents()
                self.app.toast("Venta anulada y existencias restauradas.", "success")
            except Exception as exc:
                messagebox.showerror("Venta", str(exc), parent=modal)
        ctk.CTkButton(modal, text="Confirmar anulación", fg_color=DANGER, hover_color="#dc2626", command=confirm).pack(anchor="e", padx=24)

    def refresh(self):
        self.refresh_products()
        self.render_cart()
        rows = []
        for r in self.app.sale_service.list_sales():
            rows.append({"id": r["id"], "fecha": display_datetime(r["fecha_hora"]), "total": f"${r['total']:.2f}", "estado": r["estado"], "usuario": r["usuario"]})
        def badges(key, row):
            return (row["estado"].title(), "success" if row["estado"] == "CONFIRMADA" else "danger") if key == "estado" else None
        def actions(parent, row):
            ctk.CTkButton(parent, text="Detalle", width=66, height=28, fg_color="#475569", hover_color="#334155", command=lambda rr=row: self.show_sale_detail(rr)).pack(side="left", padx=3)
            if row["estado"] == "CONFIRMADA" and self.app.session.is_admin:
                ctk.CTkButton(parent, text="Anular", width=62, height=28, fg_color=DANGER, hover_color="#dc2626", command=lambda rr=row: self.cancel_sale(rr)).pack(side="left", padx=3)
        self.sales_table.set_rows(rows, badge_resolver=badges, action_builder=actions)


class InventoryFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.selected_product_id: int | None = None
        self.selected_lot_id: int | None = None
        self.selected_product_name = ""
        self.selected_lot_row: dict[str, Any] | None = None
        PageHeader(self, "Inventario y conteo físico", "Consulte existencias por producto y revise el detalle de sus lotes.").pack(fill="x", padx=24, pady=(22, 12))
        summary = CardFrame(self, "Resumen de inventario", "Seleccione una fila para mantener el producto resaltado y ver sus lotes en la parte inferior.")
        summary.pack(fill="x", padx=24, pady=(0, 14))
        self.products_table = DarkTable(summary, [Column("id", "ID", 1, "center"), Column("producto", "Producto", 3), Column("unidad", "Unidad", 1, "center"), Column("total", "Total", 1, "center"), Column("vendible", "Vendible", 1, "center"), Column("bloqueado", "Bloqueado", 1, "center"), Column("vencido", "Vencido", 1, "center"), Column("minimo", "Mínimo", 1, "center"), Column("ubicacion", "Ubicación", 2)], height=190)
        self.products_table.pack(fill="x", padx=16, pady=(12, 16))
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=2)
        bottom.grid_rowconfigure(0, weight=1)
        lots_card = CardFrame(bottom, "Lotes del producto seleccionado", "Seleccione un lote para habilitar el ajuste de conteo físico.")
        lots_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.context = ctk.CTkLabel(lots_card, text="Ningún producto seleccionado", text_color=TEXT_SOFT)
        self.context.pack(anchor="w", padx=18, pady=(12, 2))
        self.lots_table = DarkTable(lots_card, [Column("id", "ID", 1, "center"), Column("codigo", "Código interno", 2), Column("fabricante", "Lote fabricante", 2), Column("inicial", "Inicial", 1, "center"), Column("actual", "Actual", 1, "center"), Column("vence", "Vencimiento", 2, "center")], height=290)
        self.lots_table.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        adjust_card = CardFrame(bottom, "Ajuste de conteo físico", "El formulario se habilita únicamente después de seleccionar un lote específico.")
        adjust_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.adjusting = ctk.CTkLabel(adjust_card, text="Seleccione un lote para continuar", text_color=MUTED, wraplength=420, justify="left")
        self.adjusting.pack(anchor="w", padx=18, pady=(14, 8))
        self.physical = NumberStepper(adjust_card, "Cantidad física encontrada", "0", minimum=0)
        self.physical.pack(fill="x", padx=18, pady=8)
        self.reason = LabeledEntry(adjust_card, "Motivo del ajuste", "Describa la diferencia encontrada")
        self.reason.pack(fill="x", padx=18, pady=8)
        self.adjust_btn = ctk.CTkButton(adjust_card, text="Registrar ajuste", height=40, command=self.adjust)
        self.adjust_btn.pack(fill="x", padx=18, pady=(8, 18))
        self.set_adjust_enabled(False)

    def set_adjust_enabled(self, enabled: bool):
        if not self.app.session.is_admin:
            enabled = False
            self.adjusting.configure(text="Los ajustes de inventario requieren un usuario Administrador.")
        self.physical.set_enabled(enabled)
        self.reason.set_enabled(enabled)
        self.adjust_btn.configure(state="normal" if enabled else "disabled")

    def _clear_lot_context(self):
        self.selected_lot_id = None
        self.selected_lot_row = None
        self.adjusting.configure(text="Seleccione un lote para continuar")
        self.physical.set(0)
        self.reason.delete(0, "end")
        self.set_adjust_enabled(False)

    def select_product(self, row):
        self.selected_product_id = int(row["id"])
        self.selected_product_name = row["producto"]
        self._clear_lot_context()
        self.refresh_lots()

    def select_lot(self, row):
        if not self.selected_product_id or int(row.get("product_id", self.selected_product_id)) != int(self.selected_product_id):
            self._clear_lot_context()
            return
        self.selected_lot_id = int(row["id"])
        self.selected_lot_row = row
        self.adjusting.configure(text=f"Ajustando lote: {row['codigo']} · {self.selected_product_name} · actual {row['actual']} · vence {row['vence']}")
        # Precargar la cantidad registrada ahorra digitación durante el conteo.
        # El usuario solo modifica el valor cuando realmente encontró diferencia.
        self.physical.set(int(row["actual"]))
        self.set_adjust_enabled(True)

    def preselect_product(self, product_id: int, lot_id: int | None = None):
        self.selected_product_id = product_id
        p = self.app.product_service.get_product(product_id)
        self.selected_product_name = p["nombre"] if p else ""
        self.refresh()
        if lot_id:
            for l in self.app.inventory_service.lots_for_product(product_id):
                if int(l["id"]) == int(lot_id):
                    self.select_lot({"id": l["id"], "product_id": product_id, "codigo": l["codigo_interno"], "fabricante": l["lote_fabricante"] or "—", "inicial": l["cantidad_inicial"], "actual": l["cantidad_actual"], "vence": display_date(l["fecha_vencimiento"])})
                    break

    def refresh_lots(self):
        if not self.selected_product_id:
            self.context.configure(text="Ningún producto seleccionado")
            self.lots_table.set_rows([])
            self._clear_lot_context()
            return
        p = self.app.product_service.get_product(self.selected_product_id)
        self.context.configure(text=f"Lotes de {self.selected_product_name} · Existencia total: {p['stock_total']} {p['unidad_control']}")
        rows = []
        for l in self.app.inventory_service.lots_for_product(self.selected_product_id):
            rows.append({"id": l["id"], "product_id": self.selected_product_id, "codigo": l["codigo_interno"], "fabricante": l["lote_fabricante"] or "—", "inicial": l["cantidad_inicial"], "actual": l["cantidad_actual"], "vence": display_date(l["fecha_vencimiento"]), "raw_exp": l["fecha_vencimiento"]})
        def badges(key, row):
            if key == "vence" and row["raw_exp"]:
                days = (date.fromisoformat(row["raw_exp"]) - date.today()).days
                if days < 0:
                    return (row["vence"], "danger")
                if days <= 90:
                    return (row["vence"], "warning")
            return None
        if not rows:
            self._clear_lot_context()
        self.lots_table.set_rows(rows, selected_key=self.selected_lot_id, on_row_click=self.select_lot, badge_resolver=badges)
        if self.selected_lot_id is not None:
            current = next((row for row in rows if int(row["id"]) == int(self.selected_lot_id)), None)
            if current:
                self.selected_lot_row = current
                self.adjusting.configure(
                    text=f"Ajustando lote: {current['codigo']} · {self.selected_product_name} · actual {current['actual']} · vence {current['vence']}"
                )
                self.physical.set(int(current["actual"]))
                self.set_adjust_enabled(True)
            else:
                self.selected_lot_id = None
                self.selected_lot_row = None
                self.adjusting.configure(text="Seleccione un lote para continuar")
                self.set_adjust_enabled(False)

    def adjust(self):
        if not self.selected_lot_id or not self.selected_lot_row:
            messagebox.showwarning("Ajuste", "Seleccione un lote antes de registrar un ajuste.")
            return
        try:
            physical = self.physical.get_int()
            current = int(self.selected_lot_row["actual"])
            diff = physical - current
            reason = self.reason.get().strip()
            if not reason:
                raise ValueError("Debe indicar el motivo del ajuste.")
            if not messagebox.askyesno("Confirmar ajuste", f"Lote: {self.selected_lot_row['codigo']}\nSistema: {current}\nConteo físico: {physical}\nDiferencia: {diff:+d}\n\n¿Registrar este ajuste?"):
                return
            aid = self.app.inventory_service.adjust_lot(self.selected_lot_id, physical, reason, self.app.session.id)
            self._clear_lot_context()
            self.app.refresh_dependents()
            self.app.toast(f"Ajuste #{aid} registrado correctamente.", "success")
        except Exception as exc:
            messagebox.showerror("Ajuste", str(exc))

    def refresh(self):
        rows = []
        for r in self.app.inventory_service.inventory_rows():
            rows.append({"id": r["id"], "producto": r["nombre"], "unidad": r["unidad_control"], "total": r["stock_total"], "vendible": r["stock_vendible"], "bloqueado": r["stock_bloqueado"], "vencido": r["stock_vencido"], "minimo": r["stock_minimo"], "ubicacion": r["ubicacion"] or "—", "low": int(r["stock_vendible"]) <= int(r["stock_minimo"])})
        def badges(key, row):
            if key == "vencido" and int(row["vencido"]) > 0:
                return (str(row["vencido"]), "danger")
            if key == "bloqueado" and int(row["bloqueado"]) > 0:
                return (str(row["bloqueado"]), "warning")
            if key == "vendible" and row["low"]:
                return (str(row["vendible"]), "warning" if int(row["vendible"]) > 0 else "danger")
            return None
        valid_ids = {int(row["id"]) for row in rows}
        if self.selected_product_id is not None and int(self.selected_product_id) not in valid_ids:
            self.selected_product_id = None
            self.selected_product_name = ""
            self._clear_lot_context()
        self.products_table.set_rows(rows, selected_key=self.selected_product_id, on_row_click=self.select_product, badge_resolver=badges)
        if self.selected_product_id:
            self.refresh_lots()


class AlertsFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        PageHeader(self, "Alertas", "Priorice lo que requiere atención y actúe directamente desde el panel.").pack(fill="x", padx=24, pady=(22, 12))
        self.summary = ctk.CTkFrame(self, fg_color="transparent")
        self.summary.pack(fill="x", padx=24)
        for c in range(3):
            self.summary.grid_columnconfigure(c, weight=1)
        self.summary_labels = {}
        for idx, (key, title, color) in enumerate((("expired", "Vencidos", DANGER), ("low", "Stock bajo", WARNING), ("expiring", "Por vencer", "#facc15"))):
            card = ctk.CTkFrame(self.summary, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
            card.grid(row=0, column=idx, sticky="ew", padx=8, pady=4)
            ctk.CTkLabel(card, text=title, text_color=TEXT_SOFT).pack(anchor="w", padx=16, pady=(12, 2))
            lbl = ctk.CTkLabel(card, text="0", text_color=color, font=ctk.CTkFont(size=28, weight="bold"))
            lbl.pack(anchor="w", padx=16, pady=(0, 12))
            self.summary_labels[key] = lbl

        expired_card = CardFrame(self, "Productos vencidos", "Máxima prioridad: estos lotes ya no forman parte del stock vendible.")
        expired_card.pack(fill="x", padx=24, pady=(10, 12))
        self.expired_table = DarkTable(expired_card, [Column("producto", "Producto", 3), Column("lote", "Lote", 2), Column("cantidad", "Cantidad", 1, "center"), Column("vence", "Venció", 2, "center"), Column("__actions__", "Acciones", 3, "center")], height=140)
        self.expired_table.pack(fill="x", padx=16, pady=(12, 16))

        lower = ctk.CTkFrame(self, fg_color="transparent")
        lower.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        lower.grid_columnconfigure((0, 1), weight=1)
        lower.grid_rowconfigure(0, weight=1)
        low_card = CardFrame(lower, "Existencias bajas", "Reponga los productos cuyo stock vendible ya alcanzó el mínimo configurado.")
        low_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.low_table = DarkTable(low_card, [Column("producto", "Producto", 3), Column("disponible", "Disponible", 1, "center"), Column("minimo", "Mínimo", 1, "center"), Column("unidad", "Unidad", 1, "center"), Column("__actions__", "Acción", 2, "center")], height=260)
        self.low_table.pack(fill="both", expand=True, padx=16, pady=(12, 16))
        exp_card = CardFrame(lower, "Próximos a vencer", "Los colores indican el nivel de urgencia: crítico, alto o seguimiento.")
        exp_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.exp_table = DarkTable(exp_card, [Column("producto", "Producto", 3), Column("lote", "Lote", 2), Column("cantidad", "Cantidad", 1, "center"), Column("vence", "Vence", 2, "center"), Column("estado_vencimiento", "Estado", 2, "center"), Column("__actions__", "Acción", 2, "center")], height=260)
        self.exp_table.pack(fill="both", expand=True, padx=16, pady=(12, 16))

    def go_entry(self, product_id: int):
        self.app.show("Entradas")
        self.app.frames["Entradas"].preselect_product(product_id)

    def go_inventory(self, product_id: int, lot_id: int | None = None):
        self.app.show("Inventario")
        self.app.frames["Inventario"].preselect_product(product_id, lot_id)

    def discard_modal(self, row):
        modal = make_modal(self, "Registrar merma por vencimiento", 560, 420)
        ctk.CTkLabel(modal, text="Registrar merma", font=ctk.CTkFont(size=23, weight="bold"), text_color=TEXT).pack(anchor="w", padx=24, pady=(22, 4))
        ctk.CTkLabel(modal, text=f"{row['producto']} · {row['lote']} · venció {row['vence']} · disponible {row['cantidad']}", text_color=TEXT_SOFT).pack(anchor="w", padx=24)
        qty = NumberStepper(modal, "Cantidad a descartar", "0", minimum=1)
        qty.pack(fill="x", padx=24, pady=(18, 8))
        qty.set(row["cantidad"])
        reason = LabeledEntry(modal, "Motivo", "Ej. Producto vencido retirado de vitrina")
        reason.pack(fill="x", padx=24, pady=8)
        def confirm():
            try:
                self.app.inventory_service.discard_expired(row["lot_id"], qty.get_int(), reason.get(), self.app.session.id)
                modal.destroy()
                self.app.refresh_dependents()
                self.app.toast("Merma registrada correctamente.", "success")
            except Exception as exc:
                messagebox.showerror("Merma", str(exc), parent=modal)
        ctk.CTkButton(modal, text="Registrar merma", fg_color=DANGER, hover_color="#dc2626", command=confirm).pack(anchor="e", padx=24, pady=16)

    def refresh(self):
        low = self.app.inventory_service.low_stock()
        exp = self.app.inventory_service.expiring(90)
        expired = self.app.inventory_service.expired()
        self.summary_labels["low"].configure(text=str(len(low)))
        self.summary_labels["expiring"].configure(text=str(len(exp)))
        self.summary_labels["expired"].configure(text=str(len(expired)))
        low_rows = [{"id": r["id"], "product_id": r["id"], "producto": r["nombre"], "disponible": r["stock_vendible"], "minimo": r["stock_minimo"], "unidad": r["unidad_control"]} for r in low]
        def low_actions(parent, row):
            ctk.CTkButton(parent, text="Registrar entrada", width=108, height=28, command=lambda rr=row: self.go_entry(rr["product_id"])).pack()
        self.low_table.set_rows(low_rows, badge_resolver=lambda key, row: (str(row["disponible"]), "danger" if int(row["disponible"]) == 0 else "warning") if key == "disponible" else None, action_builder=low_actions)

        exp_rows = []
        block_days = self.app.settings_service.get_block_days()
        for r in exp:
            days = int(r["dias_restantes"])
            severity = "danger" if days <= block_days else "warning" if days <= 30 else "info"
            if days == 0:
                status = "Vence hoy · bloqueado"
            elif days <= block_days:
                status = f"Bloqueado · {days} días"
            elif days <= 30:
                status = f"Urgente · {days} días"
            else:
                status = f"Seguimiento · {days} días"
            exp_rows.append({"id": r["id"], "lot_id": r["id"], "product_id": r["producto_id"], "producto": r["nombre"], "lote": r["codigo_interno"], "cantidad": r["cantidad_actual"], "vence": display_date(r["fecha_vencimiento"]), "dias": days, "estado_vencimiento": status, "severity": severity})
        def exp_actions(parent, row):
            ctk.CTkButton(parent, text="Ver lote", width=72, height=28, fg_color="#475569", hover_color="#334155", command=lambda rr=row: self.go_inventory(rr["product_id"], rr["lot_id"])).pack()
        self.exp_table.set_rows(exp_rows, badge_resolver=lambda key, row: (row["estado_vencimiento"], row["severity"]) if key == "estado_vencimiento" else ((row["vence"], row["severity"]) if key == "vence" else None), action_builder=exp_actions)

        expired_rows = [{"id": r["id"], "lot_id": r["id"], "product_id": r["producto_id"], "producto": r["nombre"], "lote": r["codigo_interno"], "cantidad": r["cantidad_actual"], "vence": display_date(r["fecha_vencimiento"])} for r in expired]
        def expired_actions(parent, row):
            ctk.CTkButton(parent, text="Ver lote", width=70, height=28, fg_color="#475569", hover_color="#334155", command=lambda rr=row: self.go_inventory(rr["product_id"], rr["lot_id"])).pack(side="left", padx=3)
            if self.app.session.is_admin:
                ctk.CTkButton(parent, text="Registrar merma", width=108, height=28, fg_color=DANGER, hover_color="#dc2626", command=lambda rr=row: self.discard_modal(rr)).pack(side="left", padx=3)
        self.expired_table.set_rows(expired_rows, badge_resolver=lambda key, row: (row["vence"], "danger") if key == "vence" else ((str(row["cantidad"]), "danger") if key == "cantidad" else None), action_builder=expired_actions)


class ReportsFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        PageHeader(self, "Reportes", "Seleccione el reporte. Los filtros de fecha solo aparecen donde realmente se necesitan.").pack(fill="x", padx=24, pady=(22, 12))
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

        self.inventory_card = self.build_export_card(grid, "Inventario actual", "Estado del inventario al momento de generar el archivo.", 0, 0, "inventory")
        self.sales_card = self.build_export_card(grid, "Ventas", "Ventas confirmadas dentro del período seleccionado.", 0, 1, "sales", needs_range=True)
        self.mov_card = self.build_export_card(grid, "Movimientos", "Entradas, ventas, anulaciones y ajustes dentro del período seleccionado.", 1, 0, "movements", needs_range=True)
        self.exp_card = self.build_export_card(grid, "Vencimientos", "Incluye próximos a vencer, lotes bloqueados para venta y productos vencidos.", 1, 1, "exp")
        self.last = ctk.CTkLabel(self, text="", text_color=TEXT_SOFT, wraplength=1000, justify="left")
        self.last.pack(anchor="w", padx=28, pady=(0, 16))

    def build_export_card(self, parent, title, subtitle, row, col, kind, needs_range=False):
        card = CardFrame(parent, title, subtitle)
        card.grid(row=row, column=col, sticky="nsew", padx=(0, 8) if col == 0 else (8, 0), pady=(0, 8) if row == 0 else (8, 0))
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=(12, 18))
        config: dict[str, Any] = {"card": card, "kind": kind}
        if needs_range:
            use_range = ctk.CTkSwitch(content, text="Filtrar por período", text_color=TEXT, progress_color=ACCENT)
            use_range.pack(anchor="w", pady=(0, 8))
            dates = ctk.CTkFrame(content, fg_color="transparent")
            dates.pack(fill="x", pady=(0, 8))
            start = CalendarField(dates, "Desde")
            end = CalendarField(dates, "Hasta")
            start.pack(side="left", fill="x", expand=True, padx=(0, 6))
            end.pack(side="left", fill="x", expand=True, padx=(6, 0))
            start.set_enabled(False)
            end.set_enabled(False)

            presets = ctk.CTkFrame(content, fg_color="transparent")
            presets.pack(fill="x", pady=(0, 8))
            ctk.CTkLabel(presets, text="Rangos rápidos:", text_color=MUTED, font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 6))

            def set_preset(mode: str):
                today = date.today()
                if mode == "all":
                    use_range.deselect()
                    start.set_enabled(False)
                    end.set_enabled(False)
                    return
                use_range.select()
                start.set_enabled(True)
                end.set_enabled(True)
                if mode == "today":
                    first = today
                elif mode == "month":
                    first = today.replace(day=1)
                else:
                    first = today - timedelta(days=29)
                start.set_date(first)
                end.set_date(today)

            for label, mode in (("Hoy", "today"), ("Este mes", "month"), ("Últimos 30 días", "30"), ("Todo", "all")):
                ctk.CTkButton(
                    presets,
                    text=label,
                    width=82 if label != "Últimos 30 días" else 116,
                    height=28,
                    fg_color="#31445f",
                    hover_color="#3b5272",
                    command=lambda m=mode: set_preset(m),
                ).pack(side="left", padx=3)

            def toggle():
                enabled = bool(use_range.get())
                start.set_enabled(enabled)
                end.set_enabled(enabled)
            use_range.configure(command=toggle)
            config.update({"use_range": use_range, "start": start, "end": end})
        actions = ctk.CTkFrame(content, fg_color="transparent")
        actions.pack(anchor="w", pady=(8, 0))
        pdf = ctk.CTkButton(actions, text="PDF", width=110, height=40, command=lambda: self.export_async(kind, "pdf", pdf))
        pdf.pack(side="left", padx=(0, 8))
        xlsx = ctk.CTkButton(actions, text="Excel", width=110, height=40, fg_color="#0f766e", hover_color="#0d5f58", command=lambda: self.export_async(kind, "xlsx", xlsx))
        xlsx.pack(side="left")
        config["buttons"] = (pdf, xlsx)
        setattr(self, f"_{kind}_config", config)
        return card

    def _range(self, kind: str):
        cfg = getattr(self, f"_{kind}_config")
        if not cfg.get("use_range") or not cfg["use_range"].get():
            return None, None
        start = cfg["start"].get_iso()
        end = cfg["end"].get_iso()
        if start > end:
            raise ValueError("La fecha Desde no puede ser posterior a la fecha Hasta.")
        return start, end

    def export_async(self, kind: str, fmt: str, button: ctk.CTkButton):
        try:
            start, end = self._range(kind)
        except Exception as exc:
            messagebox.showerror("Reportes", str(exc))
            return
        original = button.cget("text")
        button.configure(state="disabled", text="Generando...")
        self.last.configure(text="Generando reporte, espere un momento...")

        result_queue: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)

        def worker():
            try:
                user = self.app.session.nombre
                if kind == "inventory":
                    path = self.app.report_service.export_inventory(fmt, generated_by=user)
                elif kind == "sales":
                    path = self.app.report_service.export_sales(start, end, fmt, generated_by=user)
                elif kind == "movements":
                    path = self.app.report_service.export_movements(start, end, fmt, generated_by=user)
                else:
                    path = self.app.report_service.export_expirations(90, fmt, generated_by=user)
                result_queue.put(("ok", path))
            except Exception as exc:
                result_queue.put(("error", exc))

        def poll_result():
            if not self.winfo_exists():
                return
            try:
                status, payload = result_queue.get_nowait()
            except queue.Empty:
                self.after(100, poll_result)
                return
            if status == "ok":
                self._export_done(button, original, payload)
            else:
                self._export_error(button, original, payload)

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, poll_result)

    def _export_done(self, button, original, path):
        button.configure(state="normal", text=original)
        self.last.configure(text=f"Generado correctamente: {path}")
        self.app.toast(f"Reporte generado correctamente: {Path(path).name}", "success")
        open_path(path)

    def _export_error(self, button, original, exc):
        button.configure(state="normal", text=original)
        self.last.configure(text="No fue posible generar el reporte.")
        messagebox.showerror("Reportes", str(exc))


class BackupFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        PageHeader(self, "Respaldos", "Copias automáticas, manuales y restauración segura de la información.").pack(fill="x", padx=24, pady=(22, 12))
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(0, 14))
        top.grid_columnconfigure((0, 1), weight=1)

        left = CardFrame(
            top,
            "Protección automática",
            "El sistema mantiene una fotografía de inicio del día y una copia del último cierre normal.",
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(
            left,
            text=(
                "• Snapshot de inicio: se crea una vez por día y no se sobrescribe.\n"
                "• Último cierre: se actualiza automáticamente cada vez que la aplicación cierra correctamente.\n"
                "• Se conservan los últimos 7 snapshots diarios; los respaldos manuales no se eliminan."
            ),
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=13),
            wraplength=590,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(16, 8))
        self.last_backup = ctk.CTkLabel(
            left,
            text="Sin respaldos registrados.",
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=13),
            wraplength=590,
            justify="left",
        )
        self.last_backup.pack(anchor="w", padx=18, pady=(0, 12))
        left_actions = ctk.CTkFrame(left, fg_color="transparent")
        left_actions.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkButton(left_actions, text="Crear respaldo manual", height=40, command=self.backup).pack(side="left")
        ctk.CTkButton(
            left_actions,
            text="Abrir carpeta automática",
            height=40,
            fg_color="transparent",
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=BORDER,
            command=lambda: open_path(self.app.backup_service.backup_dir),
        ).pack(side="left", padx=(8, 0))

        right = CardFrame(top, "Restaurar desde respaldo", "Operación de emergencia con copia preventiva antes de reemplazar los datos actuales.")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkButton(
            right,
            text="Restaurar respaldo",
            height=42,
            fg_color="transparent",
            hover_color=DANGER_BG,
            border_width=1,
            border_color=DANGER,
            text_color=("#991B1B", "#fca5a5"),
            command=self.restore,
        ).pack(anchor="w", padx=18, pady=(20, 12))
        ctk.CTkLabel(
            right,
            text="La restauración exige escribir CONFIRMAR. Antes de reemplazar la base se guarda automáticamente el estado actual y luego se solicita iniciar sesión nuevamente.",
            text_color=("#991B1B", "#fca5a5"),
            font=ctk.CTkFont(size=13),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 20))

        history = CardFrame(self, "Historial reciente", "Las rutas completas quedan disponibles mediante la acción Abrir carpeta.")
        history.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DarkTable(
            history,
            [
                Column("fecha", "Fecha", 2, "center"),
                Column("archivo", "Archivo", 3),
                Column("tipo", "Tipo", 2, "center"),
                Column("tamano", "Tamaño", 1, "center"),
                Column("ubicacion", "Ubicación", 2),
                Column("__actions__", "Acción", 2, "center"),
            ],
            height=260,
        )
        self.table.pack(fill="both", expand=True, padx=16, pady=(12, 16))

    def backup(self):
        folder = filedialog.askdirectory(title="Seleccione dónde guardar el respaldo manual")
        if not folder:
            return
        try:
            path = self.app.backup_service.create_backup(folder, kind="MANUAL")
            self.app.audit_service.log("RESPALDO_MANUAL", user_id=self.app.session.id, entity="RESPALDO", detail=str(path))
            self.refresh()
            self.app.toast("Respaldo manual creado correctamente.", "success")
            open_path(Path(path).parent)
        except Exception as exc:
            messagebox.showerror("Respaldo", str(exc), parent=self)

    def restore(self):
        path = filedialog.askopenfilename(title="Seleccione un respaldo", filetypes=[("Base de datos SQLite", "*.db"), ("Todos los archivos", "*.*")])
        if not path:
            return
        modal = make_modal(self, "Confirmar restauración", 620, 430)
        ctk.CTkLabel(modal, text="Restaurar respaldo", font=ctk.CTkFont(size=25, weight="bold"), text_color=TEXT).pack(anchor="w", padx=24, pady=(22, 5))
        ctk.CTkLabel(modal, text=f"Archivo seleccionado:\n{Path(path).name}", text_color=TEXT_SOFT, font=ctk.CTkFont(size=13), wraplength=560, justify="left").pack(anchor="w", padx=24)
        ctk.CTkLabel(modal, text="La información actual será reemplazada. Antes de hacerlo, el sistema creará una copia preventiva.", text_color=("#991B1B", "#fca5a5"), font=ctk.CTkFont(size=13), wraplength=560, justify="left").pack(anchor="w", padx=24, pady=(16, 6))
        confirm = LabeledEntry(modal, "Escriba CONFIRMAR", "CONFIRMAR")
        confirm.pack(fill="x", padx=24, pady=14)
        btn = ctk.CTkButton(modal, text="Restaurar", state="disabled", fg_color=DANGER, hover_color="#dc2626")
        btn.pack(anchor="e", padx=24, pady=8)

        def check(_e=None):
            btn.configure(state="normal" if confirm.get().strip().upper() == "CONFIRMAR" else "disabled")
        confirm.entry.bind("<KeyRelease>", check)

        def do_restore():
            try:
                safety = self.app.backup_service.restore_backup(path)
                self.app.audit_service.log("RESTAURAR_RESPALDO", user_id=self.app.session.id, entity="RESPALDO", detail=str(path))
                modal.destroy()
                messagebox.showinfo(
                    "Respaldo",
                    f"Restauración completada.\n\nEl estado anterior quedó protegido en:\n{Path(safety).name}\n\nEl sistema volverá a la pantalla de acceso para iniciar sesión nuevamente.",
                    parent=self,
                )
                self.app.logout(force=True, modal=None)
            except Exception as exc:
                messagebox.showerror("Respaldo", str(exc), parent=modal)
        btn.configure(command=do_restore)

    @staticmethod
    def _location_label(row) -> str:
        kind = str(row["tipo"])
        if kind in {"AUTOMATICO_INICIO", "AUTOMATICO_CIERRE", "PREVIO_RESTAURACION"}:
            return "Carpeta automática"
        try:
            parent = Path(str(row["ubicacion"])).parent
            return parent.name or str(parent)
        except Exception:
            return "Ubicación externa"

    def refresh(self):
        rows = []
        history = self.app.backup_service.history(12)
        labels = {
            "AUTOMATICO_INICIO": "Inicio del día",
            "AUTOMATICO_CIERRE": "Último cierre",
            "AUTOMATICO": "Automático legado",
            "MANUAL": "Manual",
            "PREVIO_RESTAURACION": "Previo a restauración",
            "RESTAURADO": "Restaurado",
            "CREADO": "Manual",
            "SEGURIDAD_PRE_RESTAURACION": "Previo a restauración",
        }
        for r in history:
            raw_type = str(r["tipo"])
            rows.append({
                "id": r["id"],
                "fecha": display_datetime(r["fecha_hora"]),
                "archivo": r["archivo"],
                "tipo": labels.get(raw_type, raw_type.replace("_", " ").title()),
                "tamano": display_bytes(r["tamano_bytes"]),
                "ubicacion": self._location_label(r),
                "full_path": r["ubicacion"],
                "raw_type": raw_type,
            })

        def badge(key, row):
            if key != "tipo":
                return None
            if row["raw_type"] in {"AUTOMATICO_INICIO", "AUTOMATICO_CIERRE", "AUTOMATICO", "MANUAL", "CREADO"}:
                return row["tipo"], "success"
            return row["tipo"], "warning"

        def actions(parent, row):
            ctk.CTkButton(
                parent,
                text="Abrir carpeta",
                width=90,
                height=28,
                fg_color="#31445f",
                hover_color="#3b5272",
                command=lambda rr=row: open_path(Path(rr["full_path"]).parent),
            ).pack()

        self.table.set_rows(rows, badge_resolver=badge, action_builder=actions)
        start_snapshots = [r for r in rows if r["raw_type"] == "AUTOMATICO_INICIO"]
        closes = [r for r in rows if r["raw_type"] == "AUTOMATICO_CIERRE"]
        lines = []
        if start_snapshots:
            lines.append(f"Snapshot de inicio: {start_snapshots[0]['fecha']}")
        if closes:
            lines.append(f"Último cierre protegido: {closes[0]['fecha']}")
        self.last_backup.configure(text="\n".join(lines) if lines else "Sin respaldos automáticos registrados.")


class UsersFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(22, 12))
        PageHeader(header, "Usuarios", "Credenciales, roles y estado de acceso al sistema.").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(header, text="+ Nuevo usuario", height=40, width=145, command=self.open_create_modal).pack(side="right", pady=(14, 0))
        info = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        info.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(info, text="Administradores", text_color=TEXT_SOFT, font=ctk.CTkFont(size=11)).pack(side="left", padx=(16, 8), pady=12)
        self.admin_count = Badge(info, "0", "info"); self.admin_count.pack(side="left", pady=10)
        ctk.CTkLabel(info, text="Operadores", text_color=TEXT_SOFT, font=ctk.CTkFont(size=11)).pack(side="left", padx=(22, 8), pady=12)
        self.operator_count = Badge(info, "0", "neutral"); self.operator_count.pack(side="left", pady=10)
        ctk.CTkLabel(info, text="El operador no administra usuarios, respaldos, reportes ni ajustes.", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(side="right", padx=16)
        list_card = CardFrame(self, "Listado de usuarios", "Edite datos, restablezca contraseñas o desactive cuentas sin borrar su trazabilidad.")
        list_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DarkTable(list_card, [Column("id", "ID", 1, "center"), Column("nombre", "Nombre", 3), Column("usuario", "Usuario", 2), Column("rol", "Rol", 2, "center"), Column("estado", "Estado", 1, "center"), Column("creado", "Creado", 2, "center"), Column("__actions__", "Acciones", 3, "center")], height=480)
        self.table.pack(fill="both", expand=True, padx=16, pady=(12, 16))

    def open_create_modal(self):
        modal = make_modal(self, "Nuevo usuario", 660, 560)
        ctk.CTkLabel(modal, text="Crear usuario", font=ctk.CTkFont(size=25, weight="bold"), text_color=TEXT).pack(anchor="w", padx=26, pady=(24, 3))
        ctk.CTkLabel(modal, text="Asigne un rol de acuerdo con las tareas que realizará la persona dentro del sistema.", text_color=TEXT_SOFT, wraplength=590, justify="left").pack(anchor="w", padx=26)
        form = ctk.CTkFrame(modal, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=18); form.grid_columnconfigure((0,1), weight=1)
        name=LabeledEntry(form,"Nombre completo","Nombre visible"); username=LabeledEntry(form,"Usuario","Nombre de usuario"); role=LabeledCombo(form,"Rol",["OPERADOR","ADMIN"]); password=PasswordField(form,"Contraseña","Mínimo 6 caracteres"); confirm=PasswordField(form,"Confirmar contraseña","Repita la contraseña")
        name.grid(row=0,column=0,columnspan=2,padx=6,pady=8,sticky="ew"); username.grid(row=1,column=0,padx=6,pady=8,sticky="ew"); role.grid(row=1,column=1,padx=6,pady=8,sticky="ew"); password.grid(row=2,column=0,padx=6,pady=8,sticky="ew"); confirm.grid(row=2,column=1,padx=6,pady=8,sticky="ew"); role.set("OPERADOR")
        actions=ctk.CTkFrame(modal,fg_color="transparent"); actions.pack(fill="x",padx=26,pady=(0,22))
        ctk.CTkButton(actions,text="Cancelar",width=110,height=40,fg_color="transparent",hover_color=CARD_HOVER,border_width=1,border_color=BORDER,command=modal.destroy).pack(side="right",padx=(8,0))
        def create():
            try:
                if password.get()!=confirm.get(): raise ValueError("Las contraseñas no coinciden.")
                uid = self.app.auth_service.create_user(name.get(),username.get(),password.get(),role.get()); self.app.audit_service.log("CREAR_USUARIO", user_id=self.app.session.id, entity="USUARIO", entity_id=uid, detail=username.get()); modal.destroy(); self.refresh(); self.app.toast("Usuario creado correctamente.", "success")
            except Exception as exc: messagebox.showerror("Usuarios",str(exc),parent=modal)
        ctk.CTkButton(actions,text="Crear usuario",width=130,height=40,command=create).pack(side="right")
        modal.bind("<Return>", lambda _e: create())

    def edit_user(self, row):
        modal = make_modal(self, f"Editar usuario {row['usuario']}", 560, 430)
        ctk.CTkLabel(modal, text="Editar usuario", font=ctk.CTkFont(size=23, weight="bold"), text_color=TEXT).pack(anchor="w", padx=24, pady=(22, 4))
        name=LabeledEntry(modal,"Nombre","Nombre visible"); username=LabeledEntry(modal,"Usuario","Usuario"); role=LabeledCombo(modal,"Rol",["OPERADOR","ADMIN"])
        name.pack(fill="x",padx=24,pady=(12,6)); username.pack(fill="x",padx=24,pady=6); role.pack(fill="x",padx=24,pady=6); name.set(row["nombre"]); username.set(row["usuario"]); role.set(row["raw_role"])
        if int(row["id"]) == int(self.app.session.id):
            role.set_enabled(False)
            ctk.CTkLabel(modal, text="El rol de la sesión actual no puede modificarse hasta iniciar con otra cuenta administradora.", text_color=("#92400E", "#fcd34d"), wraplength=500, justify="left").pack(anchor="w", padx=24, pady=(4, 0))
        def save():
            try: self.app.auth_service.update_user(row["id"],name.get(),username.get(),role.get()); self.app.audit_service.log("EDITAR_USUARIO", user_id=self.app.session.id, entity="USUARIO", entity_id=row["id"], detail=username.get()); modal.destroy(); self.refresh(); self.app.toast("Usuario actualizado correctamente.", "success")
            except Exception as exc: messagebox.showerror("Usuarios",str(exc),parent=modal)
        ctk.CTkButton(modal,text="Guardar cambios",command=save).pack(anchor="e",padx=24,pady=16)
        modal.bind("<Return>", lambda _e: save())

    def reset_password(self,row):
        modal=make_modal(self,"Restablecer contraseña",540,360); ctk.CTkLabel(modal,text=f"Restablecer contraseña de {row['usuario']}",font=ctk.CTkFont(size=21,weight="bold"),text_color=TEXT).pack(anchor="w",padx=24,pady=(22,10)); p1=PasswordField(modal,"Nueva contraseña","Mínimo 6 caracteres"); p2=PasswordField(modal,"Confirmar contraseña","Repita la contraseña"); p1.pack(fill="x",padx=24,pady=8); p2.pack(fill="x",padx=24,pady=8)
        def save():
            try:
                if p1.get()!=p2.get(): raise ValueError("Las contraseñas no coinciden.")
                self.app.auth_service.change_password(row["id"],p1.get()); self.app.audit_service.log("CAMBIAR_CLAVE_USUARIO", user_id=self.app.session.id, entity="USUARIO", entity_id=row["id"], detail=row["usuario"]); modal.destroy(); self.app.toast("Contraseña actualizada.", "success")
            except Exception as exc: messagebox.showerror("Usuarios",str(exc),parent=modal)
        ctk.CTkButton(modal,text="Actualizar contraseña",command=save).pack(anchor="e",padx=24,pady=14)
        modal.bind("<Return>", lambda _e: save())

    def toggle_user(self,row):
        try:
            active=row["raw_active"]; action="desactivar" if active else "activar"
            if messagebox.askyesno("Usuarios",f"¿Desea {action} la cuenta {row['usuario']}?"):
                self.app.auth_service.set_active(row["id"],not active)
                self.app.audit_service.log("DESACTIVAR_USUARIO" if active else "ACTIVAR_USUARIO", user_id=self.app.session.id, entity="USUARIO", entity_id=row["id"], detail=row["usuario"])
                self.refresh()
                self.app.toast(f"Cuenta {action}da correctamente.", "success")
        except Exception as exc: messagebox.showerror("Usuarios",str(exc))

    def refresh(self):
        rows=[]; admins=0; operators=0
        for r in self.app.auth_service.list_users():
            if r["rol"]=="ADMIN": admins+=1
            else: operators+=1
            rows.append({"id":r["id"],"nombre":r["nombre"],"usuario":r["usuario"],"rol":"Administrador" if r["rol"]=="ADMIN" else "Operador","raw_role":r["rol"],"estado":"Activo" if r["activo"] else "Inactivo","raw_active":bool(r["activo"]),"creado":display_datetime(r["creado_en"])})
        self.admin_count.configure(text=str(admins)); self.operator_count.configure(text=str(operators))
        def actions(parent,row):
            ctk.CTkButton(parent,text="Editar",width=58,height=28,fg_color="#31445f",hover_color="#3b5272",command=lambda rr=row:self.edit_user(rr)).pack(side="left",padx=2)
            ctk.CTkButton(parent,text="Clave",width=55,height=28,fg_color="#31445f",hover_color="#3b5272",command=lambda rr=row:self.reset_password(rr)).pack(side="left",padx=2)
            if int(row["id"]) == int(self.app.session.id):
                ctk.CTkButton(parent,text="Sesión actual",width=86,height=28,state="disabled",fg_color="#334155").pack(side="left",padx=2)
            else:
                ctk.CTkButton(parent,text="Desactivar" if row["raw_active"] else "Activar",width=78,height=28,fg_color=DANGER if row["raw_active"] else "#0f766e",hover_color="#dc2626" if row["raw_active"] else "#0d5f58",command=lambda rr=row:self.toggle_user(rr)).pack(side="left",padx=2)
        self.table.set_rows(rows,badge_resolver=lambda key,row:(row["estado"],"success" if row["raw_active"] else "neutral") if key=="estado" else ((row["rol"],"info" if row["raw_role"]=="ADMIN" else "neutral") if key=="rol" else None),action_builder=actions)


class SettingsFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app)
        PageHeader(
            self,
            "Configuración",
            "Personalice reglas operativas y seguridad. El tema también puede cambiarse desde el icono del encabezado.",
        ).pack(fill="x", padx=24, pady=(22, 12))

        expiry = CardFrame(
            self,
            "Política de vencimiento para ventas",
            "Evita vender lotes demasiado cercanos a su fecha de vencimiento.",
        )
        expiry.pack(fill="x", padx=24, pady=(0, 14))
        body = ctk.CTkFrame(expiry, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(16, 18))
        body.grid_columnconfigure((0, 1), weight=1)
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.block_days = NumberStepper(left, "Bloquear venta cuando falten estos días o menos", "15", minimum=0)
        self.block_days.pack(fill="x")
        ctk.CTkLabel(
            left,
            text="Rango permitido: 0 a 90 días. Con 0 solo se bloquean lotes vencidos o que vencen hoy.",
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=12),
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))
        right = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(16, 0))
        ctk.CTkLabel(right, text="Comportamiento", text_color=TEXT, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=14, pady=(12, 6))
        self.policy_text = ctk.CTkLabel(right, text="", text_color=TEXT_SOFT, wraplength=500, justify="left", font=ctk.CTkFont(size=12))
        self.policy_text.pack(anchor="w", padx=14, pady=(0, 14))

        prefs = CardFrame(
            self,
            "Apariencia y seguridad de sesión",
            "El tema se aplica inmediatamente. El bloqueo por inactividad es opcional y no cierra la aplicación.",
        )
        prefs.pack(fill="x", padx=24, pady=(0, 14))
        pref_body = ctk.CTkFrame(prefs, fg_color="transparent")
        pref_body.pack(fill="x", padx=18, pady=(16, 18))
        pref_body.grid_columnconfigure((0, 1), weight=1)
        self.theme = LabeledCombo(pref_body, "Tema visual", ["Oscuro", "Claro"])
        self.theme.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.inactivity = NumberStepper(pref_body, "Bloquear sesión tras minutos de inactividad (0 = desactivado)", "0", minimum=0)
        self.inactivity.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        ctk.CTkLabel(
            pref_body,
            text="El modo claro usa fondos suaves, no blanco intenso. El bloqueo acepta de 0 a 240 minutos.",
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=12),
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        automation = CardFrame(
            self,
            "Automatizaciones activas",
            "Protecciones que funcionan sin que el usuario tenga que recordarlas.",
        )
        automation.pack(fill="x", padx=24, pady=(0, 14))
        ctk.CTkLabel(
            automation,
            text=(
                "• FEFO: las ventas descuentan primero del lote vendible que vence antes.\n"
                "• Alertas y stock vendible se recalculan después de cada movimiento.\n"
                "• Se mantiene un respaldo automático por día y se conservan los últimos 7 días.\n"
                "• Antes de restaurar se crea una copia preventiva del estado actual."
            ),
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=12),
            justify="left",
        ).pack(anchor="w", padx=18, pady=(14, 16))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 18))
        ctk.CTkButton(actions, text="Guardar configuración", width=180, height=42, command=self.save).pack(side="left")
        self.saved_hint = ctk.CTkLabel(actions, text="", text_color=MUTED, font=ctk.CTkFont(size=12))
        self.saved_hint.pack(side="left", padx=14)

    def _describe(self, days: int) -> str:
        warning_from = days + 1
        if days >= 30:
            warning_text = "No habrá una zona adicional de advertencia hasta 30 días porque el bloqueo ya cubre ese rango."
        else:
            warning_text = f"Entre {warning_from} y 30 días el lote seguirá apareciendo como próximo a vencer, pero podrá venderse."
        return (
            (f"• 0 días o vencido: no vendible.\n• 1 a {days} días: bloqueado para venta." if days > 0 else "• 0 días o vencido: bloqueado para venta.")
            + f"\n• {warning_text}\n• Más de 30 días: operación normal."
        )

    def save(self):
        try:
            days = self.block_days.get_int()
            inactivity = self.inactivity.get_int()
            if days > self.app.settings_service.MAX_BLOCK_DAYS:
                raise ValueError(f"El máximo permitido es {self.app.settings_service.MAX_BLOCK_DAYS} días.")
            if inactivity > self.app.settings_service.MAX_INACTIVITY_MINUTES:
                raise ValueError(f"El máximo de inactividad permitido es {self.app.settings_service.MAX_INACTIVITY_MINUTES} minutos.")
            theme_value = "light" if self.theme.get() == "Claro" else "dark"
            self.app.settings_service.set_block_days(days)
            self.app.settings_service.set_theme(theme_value)
            self.app.settings_service.set_inactivity_minutes(inactivity)
            ctk.set_appearance_mode(theme_value)
            self.app.update_theme_button()
            self.app.configure_inactivity(inactivity)
            self.policy_text.configure(text=self._describe(days))
            self.app.audit_service.log(
                "CAMBIO_CONFIGURACION",
                user_id=self.app.session.id,
                entity="CONFIGURACION",
                detail=f"vencimiento={days}; tema={theme_value}; inactividad={inactivity}",
            )
            self.app.refresh_dependents()
            self.saved_hint.configure(text="Configuración guardada.")
            self.app.toast("Configuración guardada y aplicada.", "success")
        except Exception as exc:
            messagebox.showerror("Configuración", str(exc))

    def refresh(self):
        days = self.app.settings_service.get_block_days()
        self.block_days.set(days)
        self.policy_text.configure(text=self._describe(days))
        self.theme.set("Claro" if self.app.settings_service.get_theme() == "light" else "Oscuro")
        self.inactivity.set(self.app.settings_service.get_inactivity_minutes())


class MainApp(ctk.CTkToplevel):
    NAV_ICONS = {"Inicio":"⌂", "Productos":"▦", "Entradas":"↓", "Ventas":"🛒", "Inventario":"▤", "Alertas":"!", "Reportes":"▥", "Respaldo":"↻", "Usuarios":"♙", "Configuración":"⚙"}

    def __init__(self, master: LoginWindow, db: Database, session: UserSession) -> None:
        super().__init__(master)
        self.root_master = master
        self.db = db
        self.session = session
        self.auth_service = AuthService(db)
        self.product_service = ProductService(db)
        self.entry_service = EntryService(db)
        self.sale_service = SaleService(db)
        self.inventory_service = InventoryService(db)
        self.report_service = ReportService(db)
        self.backup_service = BackupService(db)
        self.dashboard_service = DashboardService(db)
        self.settings_service = SettingsService(db)
        self.audit_service = AuditService(db)

        self._closing = False
        self.exit_reason = "close"
        self._locked = False
        self._last_activity = time.monotonic()
        self._inactivity_after_id = None
        self._inactivity_minutes = self.settings_service.get_inactivity_minutes()

        self.title(APP_NAME)
        self.geometry("1540x920")
        self.minsize(1280, 780)
        self.configure(fg_color=BG)
        self.after(80, self._maximize_on_start)
        self.protocol("WM_DELETE_WINDOW", self.close_application)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=248, corner_radius=0, fg_color=SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        shell = ctk.CTkFrame(self, corner_radius=0, fg_color=BG)
        shell.grid(row=0, column=1, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)
        self.topbar = ctk.CTkFrame(shell, height=68, corner_radius=0, fg_color=SURFACE, border_width=0)
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_propagate(False)
        self.content = ctk.CTkFrame(shell, corner_radius=0, fg_color=BG)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # Branding compacto para el sidebar. El logo completo se reserva para
        # login y reportes; aquí usamos un monograma limpio para no perder
        # legibilidad en tamaños pequeños.
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(18, 14))
        mark = ctk.CTkFrame(
            brand, width=42, height=42, corner_radius=12,
            fg_color=("#DDF7F2", "#103A52"), border_width=1, border_color=("#A7F3D0", "#1E647B")
        )
        mark.pack(side="left")
        mark.pack_propagate(False)
        ctk.CTkLabel(
            mark, text="FS", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#047857", "#5EEAD4")
        ).pack(expand=True)
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", fill="x", expand=True, padx=(10, 0))
        ctk.CTkLabel(
            brand_text, text=APP_NAME, font=ctk.CTkFont(size=19, weight="bold"), text_color=TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_text, text="Inventario de medicamentos", font=ctk.CTkFont(size=11), text_color=TEXT_SOFT
        ).pack(anchor="w")

        allowed = {"Inicio", "Entradas", "Ventas", "Inventario", "Alertas"}
        if session.is_admin:
            allowed = {"Inicio", "Productos", "Entradas", "Ventas", "Inventario", "Alertas", "Reportes", "Respaldo", "Usuarios", "Configuración"}
        self.allowed = allowed
        groups = [("PRINCIPAL", ["Inicio", "Productos", "Entradas", "Ventas"]), ("CONTROL", ["Inventario", "Alertas", "Reportes"]), ("ADMINISTRACIÓN", ["Respaldo", "Usuarios", "Configuración"])]
        nav = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        nav.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.nav_buttons = {}
        for group, names in groups:
            visible = [n for n in names if n in allowed]
            if not visible:
                continue
            ctk.CTkLabel(nav, text=group, text_color=MUTED, font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=12, pady=(15, 5))
            for name in visible:
                row = ctk.CTkButton(nav, text=f"  {self.NAV_ICONS.get(name,'•')}    {name}", anchor="w", height=42, corner_radius=10, fg_color="transparent", hover_color=CARD_HOVER, text_color=TEXT, font=ctk.CTkFont(size=13), command=lambda n=name: self.show(n))
                row.pack(fill="x", pady=2)
                self.nav_buttons[name] = row

        profile = ctk.CTkFrame(self.sidebar, fg_color=PANEL, corner_radius=14, border_width=1, border_color=BORDER)
        profile.pack(fill="x", padx=14, pady=(6, 10))
        initials = ''.join(part[0] for part in session.nombre.split()[:2]).upper() or 'U'
        avatar = ctk.CTkFrame(profile, width=38, height=38, corner_radius=19, fg_color=("#DBEAFE", "#243c68"))
        avatar.pack(side="left", padx=10, pady=10)
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=initials, text_color=("#1D4ED8", "#dbeafe"), font=ctk.CTkFont(size=13, weight="bold")).pack(expand=True)
        ptxt = ctk.CTkFrame(profile, fg_color="transparent")
        ptxt.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(ptxt, text=session.nombre, text_color=TEXT, font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(ptxt, text="Administrador" if session.is_admin else "Operador", text_color=TEXT_SOFT, font=ctk.CTkFont(size=11)).pack(anchor="w")
        session_actions = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        session_actions.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkButton(
            session_actions,
            text="↪  Cerrar sesión",
            height=38,
            anchor="w",
            fg_color="transparent",
            hover_color=CARD_HOVER,
            text_color=TEXT,
            border_width=1,
            border_color=BORDER,
            command=self.logout,
        ).pack(fill="x")
        ctk.CTkButton(
            self.sidebar,
            text="⏻  Cerrar aplicación",
            height=38,
            anchor="w",
            fg_color=("#DDE7F1", "#0e1728"),
            hover_color=CARD_HOVER,
            text_color=TEXT,
            border_width=1,
            border_color=BORDER,
            command=self.close_application,
        ).pack(fill="x", padx=14, pady=(0, 16))

        self.section_label = ctk.CTkLabel(self.topbar, text="Inicio", font=ctk.CTkFont(size=17, weight="bold"), text_color=TEXT)
        self.section_label.pack(side="left", padx=24)
        ctk.CTkFrame(self.topbar, width=1, height=26, fg_color=BORDER).pack(side="left")
        self.top_hint = ctk.CTkLabel(self.topbar, text="Sistema local · Disponible", text_color=TEXT_SOFT, font=ctk.CTkFont(size=13))
        self.top_hint.pack(side="left", padx=14)
        quick = ctk.CTkFrame(self.topbar, fg_color="transparent")
        quick.pack(side="right", padx=22)
        self.theme_btn = ctk.CTkButton(
            quick,
            text="",
            width=42,
            height=36,
            fg_color="transparent",
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
            command=self.toggle_theme,
        )
        self.theme_btn.pack(side="left", padx=(0, 6))
        self.update_theme_button()
        ctk.CTkButton(quick, text="+ Entrada", width=100, height=36, fg_color=("#0F766E", "#0f766e"), hover_color=("#115E59", "#0d5f58"), command=lambda: self._quick_entry()).pack(side="left", padx=4)
        ctk.CTkButton(quick, text="+ Nueva venta", width=120, height=36, command=lambda: self.show("Ventas")).pack(side="left", padx=4)

        self.frames = {
            "Inicio": DashboardFrame(self.content, self),
            "Productos": ProductsFrame(self.content, self),
            "Entradas": EntriesFrame(self.content, self),
            "Ventas": SalesFrame(self.content, self),
            "Inventario": InventoryFrame(self.content, self),
            "Alertas": AlertsFrame(self.content, self),
            "Reportes": ReportsFrame(self.content, self),
            "Respaldo": BackupFrame(self.content, self),
            "Usuarios": UsersFrame(self.content, self),
            "Configuración": SettingsFrame(self.content, self),
        }
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        self.bind_all("<KeyPress>", self._mark_activity, add="+")
        self.bind_all("<ButtonPress>", self._mark_activity, add="+")
        self.configure_inactivity(self._inactivity_minutes)
        self.show("Inicio")

    def _maximize_on_start(self) -> None:
        """Abre la ventana principal maximizada cuando la plataforma lo permite."""
        try:
            self.state("zoomed")
            return
        except Exception:
            pass
        try:
            self.attributes("-zoomed", True)
        except Exception:
            pass

    def update_theme_button(self) -> None:
        if not hasattr(self, "theme_btn"):
            return
        current = ctk.get_appearance_mode().lower()
        # El icono representa la acción disponible: sol = cambiar a claro,
        # luna = cambiar a oscuro.
        self.theme_btn.configure(text="☀" if current == "dark" else "☾")

    def toggle_theme(self) -> None:
        current = ctk.get_appearance_mode().lower()
        target = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(target)
        self.settings_service.set_theme(target)
        self.update_theme_button()
        settings_frame = self.frames.get("Configuración") if hasattr(self, "frames") else None
        if settings_frame is not None and hasattr(settings_frame, "theme"):
            settings_frame.theme.set("Claro" if target == "light" else "Oscuro")
        self.audit_service.log(
            "CAMBIO_TEMA",
            user_id=self.session.id,
            entity="CONFIGURACION",
            detail=f"tema={target}",
        )
        self.toast("Tema claro suave aplicado." if target == "light" else "Tema oscuro aplicado.", "info")

    def toast(self, message: str, kind: str = "success", duration_ms: int = 3200) -> None:
        """Notificación no bloqueante integrada al tema de la aplicación."""
        palette = {
            "success": SUCCESS,
            "warning": WARNING,
            "danger": DANGER,
            "info": ACCENT,
        }
        accent = palette.get(kind, ACCENT)
        toast = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12, border_width=1, border_color=accent)
        toast.place(relx=0.985, rely=0.085, anchor="ne")
        body = ctk.CTkFrame(toast, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=10)
        ctk.CTkLabel(body, text=message, text_color=TEXT, font=ctk.CTkFont(size=13, weight="bold"), wraplength=420, justify="left").pack(side="left")
        ctk.CTkButton(body, text="×", width=28, height=28, fg_color="transparent", hover_color=CARD_HOVER, text_color=TEXT, command=toast.destroy).pack(side="right", padx=(10, 0))
        toast.lift()
        self.after(duration_ms, lambda: toast.destroy() if toast.winfo_exists() else None)

    def _mark_activity(self, _event=None):
        self._last_activity = time.monotonic()

    def configure_inactivity(self, minutes: int) -> None:
        self._inactivity_minutes = int(minutes)
        self._last_activity = time.monotonic()
        if self._inactivity_after_id is not None:
            try:
                self.after_cancel(self._inactivity_after_id)
            except Exception:
                pass
        self._inactivity_after_id = self.after(30000, self._check_inactivity)

    def _check_inactivity(self):
        self._inactivity_after_id = None
        if not self._closing and not self._locked and self._inactivity_minutes > 0:
            elapsed = time.monotonic() - self._last_activity
            if elapsed >= self._inactivity_minutes * 60:
                self._lock_session()
        if not self._closing:
            self._inactivity_after_id = self.after(30000, self._check_inactivity)

    def _lock_session(self):
        if self._locked or self._closing:
            return
        self._locked = True
        modal = make_modal(self, "Sesión bloqueada", 500, 360)
        modal.protocol("WM_DELETE_WINDOW", lambda: None)
        ctk.CTkLabel(modal, text="Sesión bloqueada", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT).pack(anchor="w", padx=26, pady=(26, 6))
        ctk.CTkLabel(modal, text=f"Por seguridad, vuelva a ingresar la contraseña de {self.session.usuario}.", text_color=TEXT_SOFT, font=ctk.CTkFont(size=12), wraplength=440, justify="left").pack(anchor="w", padx=26)
        password = PasswordField(modal, "Contraseña", "Ingrese su contraseña")
        password.pack(fill="x", padx=26, pady=(22, 10))
        actions = ctk.CTkFrame(modal, fg_color="transparent")
        actions.pack(fill="x", padx=26, pady=(16, 22))
        ctk.CTkButton(actions, text="Cambiar usuario", width=130, fg_color="transparent", hover_color=CARD_HOVER, border_width=1, border_color=BORDER, command=lambda: self.logout(force=True, modal=modal)).pack(side="left")
        ctk.CTkButton(actions, text="Cerrar aplicación", width=130, fg_color="transparent", hover_color=CARD_HOVER, border_width=1, border_color=BORDER, command=lambda: self.close_application()).pack(side="left", padx=(8, 0))

        def unlock():
            session = self.auth_service.login(self.session.usuario, password.get())
            if not session:
                messagebox.showerror("Sesión", "Contraseña incorrecta.", parent=modal)
                return
            self._locked = False
            self._last_activity = time.monotonic()
            modal.grab_release()
            modal.destroy()
        ctk.CTkButton(actions, text="Desbloquear", width=120, command=unlock).pack(side="right")
        modal.bind("<Return>", lambda _e: unlock())
        password.focus_set()

    def logout(self, force: bool = False, modal=None) -> None:
        """Cierra solo la sesión actual y vuelve al acceso sin cerrar el programa."""
        if self._closing:
            return
        sales_frame = self.frames.get("Ventas") if hasattr(self, "frames") else None
        if not force and sales_frame is not None and getattr(sales_frame, "cart", None):
            if not themed_confirm(
                self,
                "Venta en preparación",
                "Hay productos pendientes en el carrito. Si cierra sesión, esa venta en preparación se descartará.",
                confirm_text="Cerrar sesión",
                cancel_text="Continuar trabajando",
                danger=True,
            ):
                return

        if modal is not None:
            try:
                modal.grab_release()
            except Exception:
                pass
            try:
                modal.destroy()
            except Exception:
                pass

        self._closing = True
        self.exit_reason = "logout"
        if self._inactivity_after_id is not None:
            try:
                self.after_cancel(self._inactivity_after_id)
            except Exception:
                pass
            self._inactivity_after_id = None
        try:
            self.audit_service.log(
                "CIERRE_SESION",
                user_id=self.session.id,
                entity="SESION",
                detail="Cierre de sesión solicitado por el usuario",
            )
        except Exception:
            pass
        try:
            self.unbind_all("<KeyPress>")
            self.unbind_all("<ButtonPress>")
        except Exception:
            pass
        self.destroy()

    def close_application(self, skip_backup: bool = False):
        if self._closing:
            return
        if not skip_backup:
            sales_frame = self.frames.get("Ventas") if hasattr(self, "frames") else None
            if sales_frame is not None and getattr(sales_frame, "cart", None):
                if not themed_confirm(
                    self,
                    "Venta en preparación",
                    "Hay productos pendientes en el carrito. Si cierra la aplicación, esa venta en preparación se descartará.",
                    confirm_text="Cerrar aplicación",
                    cancel_text="Continuar trabajando",
                    danger=True,
                ):
                    return
        self._closing = True
        if self._inactivity_after_id is not None:
            try:
                self.after_cancel(self._inactivity_after_id)
            except Exception:
                pass
        if not skip_backup:
            try:
                path = self.backup_service.automatic_backup()
                self.audit_service.log("RESPALDO_AUTOMATICO_CIERRE", user_id=self.session.id, entity="RESPALDO", detail=str(path))
            except Exception as exc:
                self._closing = False
                if not messagebox.askyesno("Respaldo automático", f"No se pudo crear el respaldo automático al cerrar:\n{exc}\n\n¿Desea cerrar la aplicación de todos modos?"):
                    self.configure_inactivity(self._inactivity_minutes)
                    return
                self._closing = True
        try:
            self.audit_service.log(
                "CIERRE_APLICACION",
                user_id=self.session.id,
                entity="SESION",
                detail="Cierre normal de la aplicación",
            )
        except Exception:
            pass
        self.exit_reason = "close"
        try:
            self.destroy()
        except Exception:
            pass

    def _quick_entry(self):
        self.show("Entradas")
        self.frames["Entradas"].open_entry_modal()

    def show(self, name: str):
        if name not in self.allowed:
            messagebox.showwarning("Acceso", "Su rol no tiene permiso para acceder a esta sección.")
            return
        for nav_name, btn in self.nav_buttons.items():
            btn.configure(
                fg_color=("#DBEAFE", "#1f3150") if nav_name == name else "transparent",
                hover_color=("#CFE0F7", "#273b5d") if nav_name == name else CARD_HOVER,
                text_color=("#1E3A8A", "#dbeafe") if nav_name == name else TEXT,
            )
        self.section_label.configure(text=name)
        frame = self.frames[name]
        frame.tkraise()
        frame.refresh()

    def refresh_dependents(self):
        errors: list[str] = []
        for name, frame in self.frames.items():
            try:
                frame.refresh()
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        if errors:
            messagebox.showwarning(
                "Actualización parcial",
                "La operación se guardó, pero una o más pantallas no pudieron actualizarse correctamente:\n\n" + "\n".join(errors[:4]),
            )


def launch_app(db: Database) -> None:
    db.initialize()
    auth = AuthService(db)
    auth.ensure_default_admin()
    settings = SettingsService(db)
    ctk.set_appearance_mode(settings.get_theme())

    backup_service = BackupService(db)
    startup_messages: list[str] = []
    issues = backup_service.health_check()
    if issues:
        startup_messages.append("Revisión automática de la base de datos:\n• " + "\n• ".join(issues))
    else:
        try:
            backup_service.ensure_daily_automatic_backup()
        except Exception as exc:
            startup_messages.append(f"No fue posible crear/verificar el respaldo automático del día: {exc}")

    login = LoginWindow(db)
    if startup_messages:
        login.after(500, lambda: messagebox.showwarning("Comprobación del sistema", "\n\n".join(startup_messages), parent=login))

    while True:
        login.prepare_for_login()
        login.mainloop()

        if not login.session:
            try:
                login.destroy()
            except Exception:
                pass
            return

        session = login.session
        try:
            AuditService(db).log(
                "INICIO_SESION",
                user_id=session.id,
                entity="SESION",
                detail=f"Inicio de sesión: {session.usuario}",
            )
        except Exception:
            pass

        app = MainApp(login, db, session)
        app.deiconify()
        try:
            app.lift()
            app.focus_force()
        except Exception:
            pass

        # wait_window mantiene activa la interfaz hasta que la ventana principal
        # se cierre. Si fue un logout, el ciclo vuelve a mostrar el login sin
        # terminar el proceso ni ejecutar el respaldo de cierre.
        login.wait_window(app)

        if getattr(app, "exit_reason", "close") == "logout":
            continue

        try:
            login.destroy()
        except Exception:
            pass
        return

