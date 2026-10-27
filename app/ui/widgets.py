from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

import customtkinter as ctk
from tkcalendar import Calendar

BG = ("#EEF3F8", "#0b1220")
SIDEBAR = ("#E8EEF5", "#0e1728")
PANEL = ("#EAF0F6", "#111c2e")
CARD = ("#F7F9FC", "#142136")
CARD_HOVER = ("#E1E9F2", "#1b2b45")
FIELD = ("#F1F5F9", "#0f1a2b")
BORDER = ("#C9D5E2", "#263953")
BORDER_FOCUS = ("#4F7CFF", "#5b8cff")
TEXT = ("#1F2937", "#f7f9fc")
TEXT_SOFT = ("#526176", "#b7c3d6")
MUTED = ("#7A8798", "#7f8da3")
ACCENT = ("#2563EB", "#4f7cff")
ACCENT_HOVER = ("#1D4ED8", "#3a67e8")
SUCCESS = ("#16A34A", "#22c55e")
SUCCESS_BG = ("#DCFCE7", "#133c2a")
WARNING = ("#D97706", "#f59e0b")
WARNING_BG = ("#FEF3C7", "#4a3314")
DANGER = ("#DC2626", "#ef4444")
DANGER_BG = ("#FEE2E2", "#472127")
NEUTRAL_BG = ("#DCE6F0", "#28364b")
SURFACE = ("#F4F7FA", "#0d1626")
TABLE_HEADER = ("#DDE6F0", "#17263d")
TABLE_ROW_A = ("#F7F9FC", "#111d30")
TABLE_ROW_B = ("#EEF3F8", "#0f192a")
TABLE_ROW_HOVER = ("#E0E9F4", "#1b2d49")
TABLE_ROW_SELECTED = ("#D5E4F7", "#203a63")


def _resolve_color(value):
    """Devuelve el color real para widgets tkinter que no aceptan tuplas de CTk."""
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        return value[0] if ctk.get_appearance_mode().lower() == "light" else value[1]
    return value



@dataclass(frozen=True)
class Column:
    key: str
    title: str
    weight: int = 1
    anchor: str = "w"


class PageHeader(ctk.CTkFrame):
    def __init__(self, master, title: str, subtitle: str, action: Callable[[], None] | None = None, action_text: str = "?") -> None:
        super().__init__(master, fg_color="transparent")
        text_box = ctk.CTkFrame(self, fg_color="transparent")
        text_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text_box, text="GESTIÓN  /  " + title.upper(), font=ctk.CTkFont(size=13, weight="bold"), text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(text_box, text=title, font=ctk.CTkFont(size=29, weight="bold"), text_color=TEXT).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(text_box, text=subtitle, font=ctk.CTkFont(size=14), text_color=TEXT_SOFT, wraplength=880, justify="left").pack(anchor="w", pady=(4, 0))
        if action:
            ctk.CTkButton(self, text=action_text, width=40 if action_text == "?" else 120, height=38, corner_radius=10, fg_color=CARD, hover_color=CARD_HOVER, border_width=1, border_color=BORDER, command=action).pack(side="right", padx=(12, 0))


class CardFrame(ctk.CTkFrame):
    def __init__(self, master, title: str | None = None, subtitle: str | None = None, **kwargs) -> None:
        super().__init__(master, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER, **kwargs)
        if title:
            header = ctk.CTkFrame(self, fg_color="transparent")
            header.pack(fill="x", padx=18, pady=(15, 0))
            ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(anchor="w")
            if subtitle:
                ctk.CTkLabel(header, text=subtitle, font=ctk.CTkFont(size=13), text_color=TEXT_SOFT, wraplength=900, justify="left").pack(anchor="w", pady=(3, 0))


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label: str, placeholder: str = "", width: int | None = None, show: str | None = None) -> None:
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=label, text_color=TEXT_SOFT, font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 6))
        kwargs: dict[str, Any] = {
            "placeholder_text": placeholder,
            "height": 40,
            "show": show or "",
            "fg_color": FIELD,
            "border_width": 1,
            "border_color": BORDER,
            "text_color": TEXT,
            "placeholder_text_color": MUTED,
        }
        if width is not None:
            kwargs["width"] = width
        self.entry = ctk.CTkEntry(self, **kwargs)
        self.entry.pack(fill="x")
        self.entry.bind("<FocusIn>", lambda _e: self.entry.configure(border_color=BORDER_FOCUS))
        self.entry.bind("<FocusOut>", lambda _e: self.entry.configure(border_color=BORDER))

    def get(self) -> str:
        return self.entry.get()

    def insert(self, index: int, value: str) -> None:
        self.entry.insert(index, value)

    def delete(self, start: int, end: str = "end") -> None:
        self.entry.delete(start, end)

    def set(self, value: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, value)

    def focus_set(self) -> None:
        self.entry.focus_set()

    def set_enabled(self, enabled: bool) -> None:
        self.entry.configure(state="normal" if enabled else "disabled", border_color=BORDER if enabled else ("#CBD5E1", "#2b3545"))


class PasswordField(LabeledEntry):
    def __init__(self, master, label: str, placeholder: str = "") -> None:
        ctk.CTkFrame.__init__(self, master, fg_color="transparent")
        ctk.CTkLabel(self, text=label, text_color=TEXT_SOFT, font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 6))
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(fill="x")
        self.entry = ctk.CTkEntry(box, placeholder_text=placeholder, height=40, show="•", fg_color=FIELD, border_width=1, border_color=BORDER, text_color=TEXT, placeholder_text_color=MUTED)
        self.entry.pack(side="left", fill="x", expand=True)
        self.visible = False
        self.toggle = ctk.CTkButton(box, text="👁", width=42, height=40, fg_color=NEUTRAL_BG, hover_color=CARD_HOVER, command=self._toggle)
        self.toggle.pack(side="left", padx=(6, 0))
        self.entry.bind("<FocusIn>", lambda _e: self.entry.configure(border_color=BORDER_FOCUS))
        self.entry.bind("<FocusOut>", lambda _e: self.entry.configure(border_color=BORDER))

    def _toggle(self) -> None:
        self.visible = not self.visible
        self.entry.configure(show="" if self.visible else "•")
        self.toggle.configure(text="🙈" if self.visible else "👁")


class LabeledCombo(ctk.CTkFrame):
    def __init__(self, master, label: str, values: list[str], width: int | None = None) -> None:
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=label, text_color=TEXT_SOFT, font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 6))
        kwargs: dict[str, Any] = {
            "values": values,
            "height": 40,
            "fg_color": FIELD,
            "border_color": BORDER,
            "button_color": ACCENT,
            "button_hover_color": ACCENT_HOVER,
            "dropdown_fg_color": CARD,
            "dropdown_hover_color": CARD_HOVER,
            "dropdown_text_color": TEXT,
            "text_color": TEXT,
        }
        if width is not None:
            kwargs["width"] = width
        self.combo = ctk.CTkComboBox(self, **kwargs)
        self.combo.pack(fill="x")

    def get(self) -> str:
        return self.combo.get()

    def set(self, value: str) -> None:
        self.combo.set(value)

    def configure(self, **kwargs) -> None:
        self.combo.configure(**kwargs)

    def set_enabled(self, enabled: bool) -> None:
        self.combo.configure(state="normal" if enabled else "disabled")


class NumberStepper(ctk.CTkFrame):
    """Control numérico robusto para cantidades enteras.

    No usa ``StringVar`` para evitar que una variable Tcl quede asociada a una
    raíz distinta cuando la pantalla de acceso y la ventana principal conviven.
    El valor se lee y escribe directamente en el ``CTkEntry``.
    """

    def __init__(self, master, label: str, placeholder: str = "0", minimum: int = 0) -> None:
        super().__init__(master, fg_color="transparent")
        self.minimum = int(minimum)
        ctk.CTkLabel(self, text=label, text_color=TEXT_SOFT, font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 6))
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(fill="x")

        self.minus = ctk.CTkButton(
            box,
            text="−",
            width=38,
            height=40,
            fg_color=NEUTRAL_BG,
            hover_color=CARD_HOVER,
            command=self.decrement,
        )
        self.minus.pack(side="left")

        self.entry = ctk.CTkEntry(
            box,
            placeholder_text=placeholder,
            height=40,
            fg_color=FIELD,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=MUTED,
            justify="center",
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=6)
        self.set(self.minimum)

        self.plus = ctk.CTkButton(
            box,
            text="+",
            width=38,
            height=40,
            fg_color=NEUTRAL_BG,
            hover_color=CARD_HOVER,
            command=self.increment,
        )
        self.plus.pack(side="left")

        self.entry.bind("<KeyRelease>", self._sanitize)
        self.entry.bind("<FocusIn>", lambda _e: self.entry.configure(border_color=BORDER_FOCUS))
        self.entry.bind("<FocusOut>", lambda _e: self.entry.configure(border_color=BORDER))
        self.entry.bind("<Up>", lambda _e: self._keyboard_step(1))
        self.entry.bind("<Down>", lambda _e: self._keyboard_step(-1))

    def _sanitize(self, _event=None) -> None:
        value = self.entry.get()
        clean = "".join(ch for ch in value if ch.isdigit())
        if clean != value:
            self.entry.delete(0, "end")
            self.entry.insert(0, clean)

    def _current_value(self) -> int | None:
        raw = self.entry.get().strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def increment(self) -> None:
        current = self._current_value()
        value = self.minimum if current is None else max(self.minimum, current + 1)
        self.set(value)

    def decrement(self) -> None:
        current = self._current_value()
        value = self.minimum if current is None else max(self.minimum, current - 1)
        self.set(value)

    def _keyboard_step(self, delta: int):
        if delta > 0:
            self.increment()
        else:
            self.decrement()
        return "break"

    def get(self) -> str:
        return self.entry.get()

    def get_int(self) -> int:
        value = self.entry.get().strip()
        if not value:
            raise ValueError("Debe indicar una cantidad.")
        try:
            result = int(value)
        except ValueError as exc:
            raise ValueError("La cantidad debe ser un número entero.") from exc
        if result < self.minimum:
            raise ValueError(f"La cantidad mínima permitida es {self.minimum}.")
        return result

    def set(self, value: int | str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, str(value))

    def clear(self) -> None:
        self.set(self.minimum)

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.entry.configure(state=state)
        self.minus.configure(state=state)
        self.plus.configure(state=state)


class CalendarField(ctk.CTkFrame):
    """Campo de fecha oscuro con edición manual y calendario desplegable.

    El usuario puede escribir ``DD/MM/AAAA`` directamente o pulsar el botón
    de calendario. Internamente se devuelve siempre un ``date`` válido o ISO.
    """

    def __init__(self, master, label: str, initial: date | None = None, allow_empty: bool = False) -> None:
        super().__init__(master, fg_color="transparent")
        self.allow_empty = bool(allow_empty)
        self._enabled = True
        self._calendar_window: ctk.CTkToplevel | None = None

        ctk.CTkLabel(
            self,
            text=label,
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(0, 6))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        self.entry = ctk.CTkEntry(
            row,
            placeholder_text="DD/MM/AAAA",
            height=40,
            fg_color=FIELD,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=MUTED,
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<FocusIn>", lambda _e: self.entry.configure(border_color=BORDER_FOCUS))
        self.entry.bind("<FocusOut>", self._normalize_on_focus_out)
        self.entry.bind("<Return>", self._normalize_on_enter)

        self.calendar_button = ctk.CTkButton(
            row,
            text="📅",
            width=44,
            height=40,
            fg_color=NEUTRAL_BG,
            hover_color=CARD_HOVER,
            command=self.open_calendar,
        )
        self.calendar_button.pack(side="left", padx=(6, 0))

        if initial is None and not self.allow_empty:
            initial = date.today()
        if initial is not None:
            self.set_date(initial)

    @staticmethod
    def _parse_text(raw: str) -> date:
        raw = raw.strip()
        if not raw:
            raise ValueError("Debe indicar una fecha.")
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        raise ValueError("La fecha debe usar el formato DD/MM/AAAA.")

    def _normalize_on_focus_out(self, _event=None) -> None:
        try:
            raw = self.entry.get().strip()
            if not raw and self.allow_empty:
                self.entry.configure(border_color=BORDER)
                return
            value = self._parse_text(raw)
            self.set_date(value)
            self.entry.configure(border_color=BORDER)
        except ValueError:
            self.entry.configure(border_color=DANGER)

    def _normalize_on_enter(self, _event=None):
        try:
            value = self.get_date()
            if value is not None:
                self.set_date(value)
            self.entry.configure(border_color=BORDER_FOCUS)
        except ValueError:
            self.entry.configure(border_color=DANGER)
        return "break"

    def get_date(self) -> date | None:
        raw = self.entry.get().strip()
        if not raw and self.allow_empty:
            return None
        return self._parse_text(raw)

    def get_iso(self) -> str | None:
        value = self.get_date()
        return value.isoformat() if value is not None else None

    def set_date(self, value: date) -> None:
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.insert(0, value.strftime("%d/%m/%Y"))
        if not self._enabled:
            self.entry.configure(state="disabled")

    def clear(self) -> None:
        if not self.allow_empty:
            self.set_date(date.today())
            return
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        if not self._enabled:
            self.entry.configure(state="disabled")

    def open_calendar(self) -> None:
        if not self._enabled:
            return
        if self._calendar_window is not None:
            try:
                if self._calendar_window.winfo_exists():
                    self._calendar_window.lift()
                    self._calendar_window.focus_force()
                    return
            except Exception:
                self._calendar_window = None

        try:
            current = self.get_date() or date.today()
        except ValueError:
            current = date.today()

        top = ctk.CTkToplevel(self)
        self._calendar_window = top
        top.title("Seleccionar fecha")
        top.resizable(False, False)
        top.transient(self.winfo_toplevel())
        top.configure(fg_color=SURFACE)
        top.protocol("WM_DELETE_WINDOW", self._close_calendar)

        calendar = Calendar(
            top,
            selectmode="day",
            year=current.year,
            month=current.month,
            day=current.day,
            date_pattern="dd/mm/yyyy",
            background=_resolve_color(CARD),
            foreground=_resolve_color(TEXT),
            bordercolor=_resolve_color(BORDER),
            headersbackground=_resolve_color(TABLE_HEADER),
            headersforeground=_resolve_color(TEXT),
            selectbackground=_resolve_color(ACCENT),
            selectforeground="white",
            normalbackground=_resolve_color(FIELD),
            normalforeground=_resolve_color(TEXT),
            weekendbackground=_resolve_color(FIELD),
            weekendforeground=("#B91C1C" if ctk.get_appearance_mode().lower() == "light" else "#fca5a5"),
            othermonthbackground=_resolve_color(SURFACE),
            othermonthforeground=_resolve_color(MUTED),
            othermonthwebackground=_resolve_color(SURFACE),
            othermonthweforeground=_resolve_color(MUTED),
            disabledbackground=_resolve_color(SURFACE),
            disabledforeground=_resolve_color(MUTED),
            tooltipbackground=_resolve_color(CARD),
            tooltipforeground=TEXT,
            font=("Segoe UI", 10),
        )
        calendar.pack(padx=14, pady=(14, 8))

        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))

        def apply_date():
            self.set_date(calendar.selection_get())
            self.entry.configure(border_color=BORDER_FOCUS)
            self._close_calendar()
            try:
                self.entry.focus_set()
            except Exception:
                pass

        ctk.CTkButton(
            actions,
            text="Cancelar",
            width=100,
            height=36,
            fg_color="transparent",
            hover_color=CARD_HOVER,
            border_width=1,
            border_color=BORDER,
            command=self._close_calendar,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(actions, text="Usar fecha", width=110, height=36, command=apply_date).pack(side="right")

        top.update_idletasks()
        try:
            parent = self.winfo_toplevel()
            px = parent.winfo_rootx() + max(20, (parent.winfo_width() - top.winfo_reqwidth()) // 2)
            py = parent.winfo_rooty() + max(20, (parent.winfo_height() - top.winfo_reqheight()) // 2)
            top.geometry(f"+{px}+{py}")
        except Exception:
            pass
        try:
            top.grab_set()
            top.focus_force()
        except Exception:
            pass

    def _close_calendar(self) -> None:
        top = self._calendar_window
        self._calendar_window = None
        if top is not None:
            try:
                top.grab_release()
            except Exception:
                pass
            try:
                top.destroy()
            except Exception:
                pass

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        state = "normal" if enabled else "disabled"
        self.entry.configure(state=state, border_color=BORDER if enabled else ("#CBD5E1", "#2b3545"))
        self.calendar_button.configure(state=state)


class SearchableSelector(ctk.CTkFrame):
    """Selector buscable sin ventanas flotantes ni ``place``.

    Los resultados viven dentro del mismo componente. Esto evita pérdidas de
    foco y problemas de z-order en Windows. Al enfocar el campo se muestran
    sugerencias; al escribir se filtran; al pulsar una sugerencia se confirma
    ``selected_value``.
    """

    def __init__(self, master, label: str, placeholder: str = "Buscar producto...", max_results: int = 6) -> None:
        super().__init__(master, fg_color="transparent")
        self.items: list[dict[str, Any]] = []
        self.selected_value: Any = None
        self._visible_items: list[dict[str, Any]] = []
        self.max_results = max(1, int(max_results))
        self._results_visible = False
        self._on_select: Callable[[Any], None] | None = None

        ctk.CTkLabel(
            self,
            text=label,
            text_color=TEXT_SOFT,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(0, 6))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        self.entry = ctk.CTkEntry(
            row,
            placeholder_text=placeholder,
            height=40,
            fg_color=FIELD,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=MUTED,
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.toggle_button = ctk.CTkButton(
            row,
            text="⌄",
            width=42,
            height=40,
            fg_color=NEUTRAL_BG,
            hover_color=CARD_HOVER,
            command=self.toggle_results,
        )
        self.toggle_button.pack(side="left", padx=(6, 0))

        self.results = ctk.CTkFrame(
            self,
            fg_color=PANEL,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
        )

        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", lambda _e: self.entry.configure(border_color=BORDER))
        self.entry.bind("<Return>", self._select_first)
        self.entry.bind("<Down>", self._select_first)
        self.entry.bind("<Escape>", lambda _e: self.hide_results())

    def set_items(self, items: list[dict[str, Any]]) -> None:
        unique: list[dict[str, Any]] = []
        seen: set[Any] = set()
        for item in items:
            value = item.get("value")
            if value in seen:
                continue
            seen.add(value)
            unique.append(item)
        self.items = unique
        if self.selected_value is not None and not any(
            item.get("value") == self.selected_value and item.get("enabled", True)
            for item in self.items
        ):
            self.clear()
        elif self._results_visible:
            self.show_results()

    def get_value(self):
        return self.selected_value

    def set_on_select(self, callback: Callable[[Any], None] | None) -> None:
        self._on_select = callback

    def get_text(self) -> str:
        return self.entry.get()

    def _set_text(self, text: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def clear(self) -> None:
        self.selected_value = None
        self._set_text("")
        self.hide_results()
        if self._on_select:
            self._on_select(None)

    def focus_input(self) -> None:
        try:
            self.entry.focus_set()
            self.entry.icursor("end")
        except Exception:
            pass

    def set_by_value(self, value: Any) -> None:
        for item in self.items:
            if item.get("value") == value and item.get("enabled", True):
                self.selected_value = value
                self._set_text(str(item.get("label", "")))
                self.hide_results()
                if self._on_select:
                    self._on_select(value)
                return
        self.clear()

    def _filtered(self) -> list[dict[str, Any]]:
        term = self.entry.get().strip().casefold()
        if not term:
            return self.items[: self.max_results]
        return [
            item
            for item in self.items
            if term in str(item.get("label", "")).casefold()
        ][: self.max_results]

    def _on_focus_in(self, _event=None) -> None:
        self.entry.configure(border_color=BORDER_FOCUS)
        self.show_results()

    def _on_key(self, event=None) -> None:
        if event is not None and event.keysym in {"Return", "Down", "Escape", "Up"}:
            return
        current = self.entry.get().strip()
        exact = next(
            (
                item
                for item in self.items
                if str(item.get("label", "")).strip() == current and item.get("enabled", True)
            ),
            None,
        )
        self.selected_value = exact.get("value") if exact else None
        self.show_results()

    def toggle_results(self) -> None:
        if self._results_visible:
            self.hide_results()
        else:
            self.entry.focus_set()
            self.show_results()

    def show_results(self) -> None:
        for child in self.results.winfo_children():
            child.destroy()
        options = self._filtered()
        self._visible_items = options

        if not self._results_visible:
            self.results.pack(fill="x", pady=(5, 0))
            self._results_visible = True

        if not options:
            ctk.CTkLabel(
                self.results,
                text="No hay productos que coincidan con la búsqueda.",
                text_color=TEXT_SOFT,
                anchor="w",
            ).pack(fill="x", padx=10, pady=10)
            return

        for item in options:
            enabled = bool(item.get("enabled", True))
            label = str(item.get("label", ""))
            button = ctk.CTkButton(
                self.results,
                text=label,
                height=34,
                anchor="w",
                fg_color="transparent" if enabled else SURFACE,
                hover_color=TABLE_ROW_HOVER if enabled else SURFACE,
                text_color=TEXT if enabled else MUTED,
                state="normal" if enabled else "disabled",
                command=(lambda it=item: self._choose(it)) if enabled else None,
            )
            button.pack(fill="x", padx=4, pady=2)

    def hide_results(self) -> None:
        self._visible_items = []
        if self._results_visible:
            try:
                self.results.pack_forget()
            except Exception:
                pass
            self._results_visible = False

    def _choose(self, item: dict[str, Any]) -> None:
        if not item.get("enabled", True):
            return
        self.selected_value = item.get("value")
        self._set_text(str(item.get("label", "")))
        self.hide_results()
        if self._on_select:
            self._on_select(self.selected_value)
        try:
            self.entry.configure(border_color=BORDER_FOCUS)
            self.entry.focus_set()
            self.entry.icursor("end")
        except Exception:
            pass

    def _select_first(self, _event=None):
        options = self._filtered()
        item = next((it for it in options if it.get("enabled", True)), None)
        if item is not None:
            self._choose(item)
        return "break"


class Badge(ctk.CTkLabel):
    def __init__(self, master, text: str, kind: str = "neutral") -> None:
        palette = {
            "success": (SUCCESS_BG, ("#166534", "#86efac")),
            "warning": (WARNING_BG, ("#92400E", "#fcd34d")),
            "danger": (DANGER_BG, ("#991B1B", "#fca5a5")),
            "info": (("#DBEAFE", "#17365f"), ("#1D4ED8", "#93c5fd")),
            "neutral": (NEUTRAL_BG, ("#475569", "#cbd5e1")),
        }
        fg, text_color = palette.get(kind, palette["neutral"])
        super().__init__(master, text=text, fg_color=fg, text_color=text_color, corner_radius=8, padx=8, pady=3, font=ctk.CTkFont(size=13, weight="bold"))


class DarkTable(ctk.CTkFrame):
    """Tabla oscura reutilizable con columnas proporcionalmente alineadas.

    El encabezado y cada fila usan la misma distribución proporcional, evitando
    que el contenido de una fila desplace visualmente las columnas. Además se
    compensa el ancho de la barra de desplazamiento para que el encabezado quede
    alineado con las filas en Windows.
    """

    def __init__(self, master, columns: list[Column], height: int = 260, row_key: str = "id") -> None:
        super().__init__(master, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        self.columns = columns
        self.row_key = row_key
        self.selected_key: Any = None
        self.row_callback: Callable[[dict[str, Any]], None] | None = None
        self.rows_by_key: dict[Any, dict[str, Any]] = {}
        self.row_frames: dict[Any, ctk.CTkFrame] = {}
        self.row_base_colors: dict[Any, str] = {}
        self._uniform_group = f"darktable_{id(self)}"

        self.header = ctk.CTkFrame(self, fg_color=TABLE_HEADER, corner_radius=9)
        # La barra vertical del CTkScrollableFrame ocupa parte del ancho del body.
        # El margen derecho adicional mantiene las columnas visualmente alineadas.
        self.header.pack(fill="x", padx=(12, 30), pady=(12, 6))
        for idx, col in enumerate(columns):
            self.header.grid_columnconfigure(idx, weight=col.weight, uniform=self._uniform_group)
            ctk.CTkLabel(
                self.header,
                text=col.title,
                text_color=("#334155", "#dbeafe"),
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor=col.anchor,
            ).grid(row=0, column=idx, sticky="ew", padx=10, pady=10)

        self.body = ctk.CTkScrollableFrame(
            self,
            fg_color=PANEL,
            height=height,
            corner_radius=0,
            scrollbar_button_color=("#CBD5E1", "#32445f"),
            scrollbar_button_hover_color=("#94A3B8", "#415877"),
        )
        self.body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for idx, col in enumerate(columns):
            self.body.grid_columnconfigure(idx, weight=col.weight, uniform=self._uniform_group)

    def clear(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self.rows_by_key.clear()
        self.row_frames.clear()
        self.row_base_colors.clear()

    def set_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        selected_key: Any = None,
        on_row_click: Callable[[dict[str, Any]], None] | None = None,
        badge_resolver: Callable[[str, dict[str, Any]], tuple[str, str] | None] | None = None,
        action_builder: Callable[[ctk.CTkFrame, dict[str, Any]], None] | None = None,
        cell_style: Callable[[str, dict[str, Any]], dict[str, Any] | None] | None = None,
    ) -> None:
        self.clear()
        self.selected_key = selected_key
        self.row_callback = on_row_click
        if not rows:
            empty = ctk.CTkLabel(self.body, text="No hay registros para mostrar.", text_color=MUTED)
            empty.grid(row=0, column=0, columnspan=max(1, len(self.columns)), sticky="w", padx=12, pady=16)
            return
        for r_idx, row in enumerate(rows):
            key = row.get(self.row_key, r_idx)
            self.rows_by_key[key] = row
            base_color = TABLE_ROW_SELECTED if key == selected_key else (TABLE_ROW_A if r_idx % 2 == 0 else TABLE_ROW_B)
            row_frame = ctk.CTkFrame(self.body, fg_color=base_color, corner_radius=8)
            row_frame.grid(row=r_idx, column=0, columnspan=len(self.columns), sticky="ew", pady=3)
            self.row_frames[key] = row_frame
            self.row_base_colors[key] = TABLE_ROW_A if r_idx % 2 == 0 else TABLE_ROW_B
            for idx, col in enumerate(self.columns):
                row_frame.grid_columnconfigure(idx, weight=col.weight, uniform=self._uniform_group)
                if col.key == "__actions__" and action_builder:
                    cell = ctk.CTkFrame(row_frame, fg_color="transparent")
                    # Sin sticky EW: el grupo de botones queda centrado en la
                    # columna de acciones en vez de pegarse al borde izquierdo.
                    cell.grid(row=0, column=idx, sticky="", padx=8, pady=6)
                    action_builder(cell, row)
                    continue
                badge = badge_resolver(col.key, row) if badge_resolver else None
                if badge:
                    text, kind = badge
                    widget = Badge(row_frame, text, kind)
                    widget.grid(row=0, column=idx, sticky=("w" if col.anchor == "w" else "e" if col.anchor == "e" else ""), padx=10, pady=8)
                else:
                    style = cell_style(col.key, row) if cell_style else None
                    widget = ctk.CTkLabel(
                        row_frame,
                        text=str(row.get(col.key, "")),
                        text_color=(style or {}).get("text_color", TEXT),
                        font=ctk.CTkFont(size=13, weight=(style or {}).get("weight", "normal")),
                        anchor=col.anchor,
                    )
                    widget.grid(row=0, column=idx, sticky="ew", padx=10, pady=9)
                if on_row_click and col.key != "__actions__":
                    widget.bind("<Button-1>", lambda _e, rr=row, kk=key: self._select(rr, kk))
            if on_row_click:
                row_frame.bind("<Button-1>", lambda _e, rr=row, kk=key: self._select(rr, kk))
                row_frame.bind("<Enter>", lambda _e, f=row_frame, kk=key: f.configure(fg_color=TABLE_ROW_HOVER) if kk != self.selected_key else None)
                row_frame.bind("<Leave>", lambda _e, f=row_frame, kk=key, idx=r_idx: f.configure(fg_color=(TABLE_ROW_SELECTED if kk == self.selected_key else (TABLE_ROW_A if idx % 2 == 0 else TABLE_ROW_B))))

    def _select(self, row: dict[str, Any], key: Any) -> None:
        old = self.selected_key
        self.selected_key = key
        if old in self.row_frames:
            self.row_frames[old].configure(fg_color=self.row_base_colors.get(old, TABLE_ROW_A))
        if key in self.row_frames:
            self.row_frames[key].configure(fg_color=TABLE_ROW_SELECTED)
        if self.row_callback:
            self.row_callback(row)
