"""Interface gráfica do Renomeador Portátil para Windows."""
from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from create_icon import ensure_icon_assets
except ImportError:
    ensure_icon_assets = None

from renamer import (
    RenameItem,
    RenameOptions,
    apply_recursive_renames,
    create_plan,
    evaluate_plan,
    undo_last_renaming,
)


PALETTES = {
    "Escuro": {
        "app": "#0d1728",
        "surface": "#142238",
        "surface_alt": "#192b43",
        "navy": "#0a1424",
        "navy_light": "#1b304c",
        "ink": "#e7eef9",
        "muted": "#9aacc4",
        "border": "#30435d",
        "blue": "#4285ff",
        "blue_hover": "#2f70ee",
        "blue_soft": "#1e3558",
        "green": "#40d7a0",
        "green_soft": "#123e39",
        "red": "#ff7882",
        "red_soft": "#492936",
        "amber": "#f4bd58",
        "amber_soft": "#453721",
        "row_alt": "#172941",
        "log": "#081322",
        "log_text": "#d5e2f5",
        "heading": "#203149",
        "input": "#0f1c2f",
        "selection": "#274a78",
        "white": "#ffffff",
    },
    "Claro": {
        "app": "#eef2f7",
        "surface": "#ffffff",
        "surface_alt": "#f5f8fc",
        "navy": "#17365d",
        "navy_light": "#274b75",
        "ink": "#1c2c43",
        "muted": "#65748a",
        "border": "#d5dfeb",
        "blue": "#2864df",
        "blue_hover": "#174fca",
        "blue_soft": "#e8efff",
        "green": "#16835d",
        "green_soft": "#e4f5ec",
        "red": "#bd3444",
        "red_soft": "#fff0f1",
        "amber": "#9a6514",
        "amber_soft": "#fff4dc",
        "row_alt": "#f5f8fc",
        "log": "#142238",
        "log_text": "#d6e0f0",
        "heading": "#eaf0f7",
        "input": "#fbfcfe",
        "selection": "#d8e6ff",
        "white": "#ffffff",
    },
}


def resource_path(relative: str) -> Path:
    """Resolve arquivos de dados tanto no fonte quanto no executável PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


class ScrollableFrame(ttk.Frame):
    """Área de regras rolável para se adaptar a telas e janelas menores."""

    def __init__(self, parent: tk.Widget, app: "RenamerGUI", **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.app = app
        self.canvas = tk.Canvas(
            self,
            background=self.app.palette["app"],
            borderwidth=0,
            highlightthickness=0,
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="App.TFrame")
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.inner.bind("<Configure>", self._update_scrollregion)
        self.canvas.bind("<Configure>", self._resize_inner)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _update_scrollregion(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event) -> None:
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None and widget is not self:
            widget = getattr(widget, "master", None)
        if widget is self:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_theme(self) -> None:
        self.canvas.configure(background=self.app.palette["app"])


class RenamerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Renomeador Portátil")
        self.root.geometry("1280x850")
        self.root.minsize(1000, 700)
        self.theme_var = tk.StringVar(value="Escuro")
        self.palette = PALETTES[self.theme_var.get()]
        self.theme_widgets: dict[tk.Widget, str] = {}
        self.scrollable_frames: list[ScrollableFrame] = []
        self.current_items: list[RenameItem] = []
        self.current_folder: Path | None = None
        self.item_by_iid: dict[str, RenameItem] = {}
        self.app_icon_photo: tk.PhotoImage | None = None

        self.folder_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.remove_start_var = tk.StringVar(value="0")
        self.remove_end_var = tk.StringVar(value="0")
        self.remove_terms_var = tk.StringVar()
        self.replace_from_var = tk.StringVar()
        self.replace_to_var = tk.StringVar()
        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.case_var = tk.StringVar(value="Título inteligente (PT-BR/EN)")
        self.ignore_case_var = tk.BooleanVar(value=False)
        self.spellcheck_var = tk.BooleanVar(value=False)
        self.spell_language_var = tk.StringVar(value="Português (Brasil)")
        self.custom_words_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="Todos os itens")
        self.search_var = tk.StringVar()
        self.summary_var = tk.StringVar(value="Escolha uma pasta e pré-visualize as alterações")
        self.item_count_var = tk.StringVar(value="0 itens")
        self.folder_count_var = tk.StringVar(value="0 pastas")
        self.change_count_var = tk.StringVar(value="0 selecionados")
        self.conflict_count_var = tk.StringVar(value="0 conflitos")

        if ensure_icon_assets is not None:
            try:
                ensure_icon_assets()
            except Exception:
                # O aplicativo continua funcional se a geração do ícone falhar.
                pass

        self._configure_styles()
        self._build_ui()
        self._apply_tk_theme()
        self.search_var.trace_add("write", lambda *_: self._render_plan())
        self.filter_var.trace_add("write", lambda *_: self._render_plan())
        self.root.bind("<Control-Return>", lambda _event: self.preview())
        self._set_application_icon()
        self._log("Bem-vindo! Selecione uma pasta, configure as regras e clique em Pré-visualizar.")

        # Maximiza a janela por padrão no Windows.
        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _register_theme_widget(self, widget: tk.Widget, role: str) -> tk.Widget:
        self.theme_widgets[widget] = role
        return widget

    def _tk_frame(self, parent, role: str, **kwargs) -> tk.Frame:
        widget = tk.Frame(parent, bg=self.palette[role], **kwargs)
        self.theme_widgets[widget] = role
        return widget

    def _tk_label(self, parent, text: str, role: str, **kwargs) -> tk.Label:
        if role == "header_title":
            bg, fg = self.palette["navy"], self.palette["white"]
        elif role == "header_subtitle":
            bg, fg = self.palette["navy"], "#c5d3e6"
        elif role == "badge_info":
            bg, fg = self.palette["blue_soft"], self.palette["blue"]
        elif role == "badge_success":
            bg, fg = self.palette["green_soft"], self.palette["green"]
        elif role == "badge_warning":
            bg, fg = self.palette["amber_soft"], self.palette["amber"]
        elif role == "badge_error":
            bg, fg = self.palette["red_soft"], self.palette["red"]
        elif role == "logo":
            bg, fg = self.palette["blue"], self.palette["white"]
        elif role == "header_badge":
            bg, fg = self.palette["navy_light"], "#e3ecf9"
        else:
            bg, fg = self.palette["app"], self.palette["ink"]
        widget = tk.Label(parent, text=text, bg=bg, fg=fg, **kwargs)
        self.theme_widgets[widget] = role
        return widget

    def _configure_styles(self) -> None:
        p = self.palette
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=p["app"])
        style.configure("Card.TFrame", background=p["surface"], borderwidth=1, relief="solid")
        style.configure("CardInner.TFrame", background=p["surface"])
        style.configure("Header.TFrame", background=p["navy"])
        style.configure("Title.TLabel", background=p["navy"], foreground=p["white"], font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background=p["navy"], foreground="#c5d3e6", font=("Segoe UI", 9))
        style.configure("Eyebrow.TLabel", background=p["surface"], foreground=p["blue"], font=("Segoe UI", 8, "bold"))
        style.configure("Section.TLabel", background=p["surface"], foreground=p["ink"], font=("Segoe UI", 11, "bold"))
        style.configure("Hint.TLabel", background=p["surface"], foreground=p["muted"], font=("Segoe UI", 9))
        style.configure("Field.TLabel", background=p["surface"], foreground=p["ink"], font=("Segoe UI", 9, "bold"))
        style.configure("AppText.TLabel", background=p["app"], foreground=p["muted"], font=("Segoe UI", 9))
        style.configure("AppTitle.TLabel", background=p["app"], foreground=p["ink"], font=("Segoe UI", 12, "bold"))
        style.configure("TButton", font=("Segoe UI", 9), padding=(10, 7), background=p["surface_alt"], foreground=p["ink"], borderwidth=0)
        style.map("TButton", background=[("active", p["blue_soft"]), ("disabled", p["surface_alt"])])
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9), background=p["blue"], foreground=p["white"])
        style.map("Primary.TButton", background=[("active", p["blue_hover"]), ("pressed", p["blue_hover"])])
        style.configure("Preview.TButton", font=("Segoe UI", 10, "bold"), padding=(13, 9), background=p["blue_soft"], foreground=p["blue"])
        style.map("Preview.TButton", background=[("active", p["selection"])])
        style.configure("Undo.TButton", font=("Segoe UI", 9, "bold"), padding=(12, 9), background=p["amber_soft"], foreground=p["amber"])
        style.map("Undo.TButton", background=[("active", p["amber_soft"])])
        style.configure("Modern.TEntry", padding=(8, 6), fieldbackground=p["input"], foreground=p["ink"], bordercolor=p["border"], insertcolor=p["ink"])
        style.map("Modern.TEntry", fieldbackground=[("focus", p["surface"])], bordercolor=[("focus", p["blue"])])
        style.configure("Modern.TSpinbox", padding=(5, 5), fieldbackground=p["input"], foreground=p["ink"], bordercolor=p["border"], arrowcolor=p["muted"])
        style.configure("Modern.TCombobox", padding=(6, 6), fieldbackground=p["input"], foreground=p["ink"], bordercolor=p["border"], arrowcolor=p["muted"])
        style.map("Modern.TCombobox", fieldbackground=[("readonly", p["input"]), ("focus", p["surface"])], foreground=[("readonly", p["ink"])])
        style.configure("Card.TCheckbutton", background=p["surface"], foreground=p["ink"], font=("Segoe UI", 9), padding=(0, 3))
        style.map("Card.TCheckbutton", background=[("active", p["surface"])])
        style.configure("Treeview", background=p["surface"], fieldbackground=p["surface"], foreground=p["ink"], rowheight=29, bordercolor=p["border"], borderwidth=1, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=p["heading"], foreground=p["ink"], font=("Segoe UI", 9, "bold"), padding=(7, 9), relief="flat")
        style.map("Treeview", background=[("selected", p["selection"])], foreground=[("selected", p["ink"])])
        style.configure("Vertical.TScrollbar", background=p["surface_alt"], troughcolor=p["app"], bordercolor=p["app"], arrowcolor=p["muted"])

    def _apply_tk_theme(self) -> None:
        p = self.palette
        self.root.configure(bg=p["app"])
        for widget, role in list(self.theme_widgets.items()):
            try:
                if not widget.winfo_exists():
                    continue
                if isinstance(widget, (tk.Frame, tk.Canvas)):
                    if role in {"header", "header_text"}:
                        widget.configure(bg=p["navy"])
                    elif role == "accent":
                        widget.configure(bg=p["blue"])
                    elif role == "app":
                        widget.configure(bg=p["app"])
                    continue
                if role in {"header", "header_text", "header_title", "header_subtitle"}:
                    bg = p["navy"]
                    fg = p["white"] if role in {"header_title", "header_text"} else "#c5d3e6"
                elif role == "logo":
                    bg, fg = p["blue"], p["white"]
                elif role == "header_badge":
                    bg, fg = p["navy_light"], "#e3ecf9"
                elif role == "badge_info":
                    bg, fg = p["blue_soft"], p["blue"]
                elif role == "badge_success":
                    bg, fg = p["green_soft"], p["green"]
                elif role == "badge_warning":
                    bg, fg = p["amber_soft"], p["amber"]
                elif role == "badge_error":
                    bg, fg = p["red_soft"], p["red"]
                elif role == "log":
                    bg, fg = p["log"], p["log_text"]
                elif role == "app":
                    bg, fg = p["app"], p["ink"]
                elif role == "accent":
                    bg, fg = p["blue"], p["white"]
                else:
                    continue
                widget.configure(bg=bg, fg=fg)
            except tk.TclError:
                continue
        for scrollable in self.scrollable_frames:
            scrollable.set_theme()

    def _set_application_icon(self) -> None:
        try:
            icon_path = resource_path("assets/renomeador.png")
            self.app_icon_photo = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self.app_icon_photo)
            if hasattr(self, "logo_label"):
                self.logo_label.configure(image=self.app_icon_photo, text="")
                self.logo_label.image = self.app_icon_photo
        except (tk.TclError, OSError):
            # O ícone é gerado no processo de compilação; a interface continua funcional no fonte.
            pass

    def _card(self, parent: tk.Widget, padding: int = 11) -> ttk.Frame:
        return ttk.Frame(parent, style="Card.TFrame", padding=padding)

    def _rule_card(self, parent: tk.Widget, title: str, note: str | None = None) -> ttk.Frame:
        card = self._card(parent, padding=11)
        card.pack(fill="x", pady=(0, 8))
        ttk.Label(card, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 7))
        if note:
            ttk.Label(card, text=note, style="Hint.TLabel", wraplength=300, justify="left").pack(anchor="w", pady=(0, 7))
        return card

    def _field(self, parent: tk.Widget, label: str, variable: tk.StringVar) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w", pady=(0, 4))
        entry = ttk.Entry(parent, textvariable=variable, style="Modern.TEntry")
        entry.pack(fill="x")
        return entry

    def _build_ui(self) -> None:
        p = self.palette
        outer = ttk.Frame(self.root, style="App.TFrame", padding=(14, 12, 14, 12))
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        header = self._tk_frame(outer, "header", height=78)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 11))
        header.grid_propagate(False)
        accent = tk.Frame(header, bg=p["blue"], width=5)
        accent.pack(side="left", fill="y")
        logo_path = resource_path("assets/renomeador.png")
        try:
            self.app_icon_photo = tk.PhotoImage(file=str(logo_path))
        except (tk.TclError, OSError):
            self.app_icon_photo = None
        logo_label = self._tk_label(
            header, "R", "logo", font=("Segoe UI", 20, "bold"), width=3, height=1
        )
        self.logo_label = logo_label
        if self.app_icon_photo is not None:
            logo_label.configure(image=self.app_icon_photo, text="", width=56, height=56)
            logo_label.image = self.app_icon_photo
        logo_label.pack(side="left", padx=(14, 12), pady=10)
        heading = self._tk_frame(header, "header",)
        heading.pack(side="left", fill="both", expand=True, pady=12)
        title = self._tk_label(heading, "Renomeador Portátil", "header_title", font=("Segoe UI", 19, "bold"))
        title.pack(anchor="w")
        subtitle = self._tk_label(
            heading, "Renomeie arquivos e pastas com rapidez, controle e segurança.", "header_subtitle",
            font=("Segoe UI", 9),
        )
        subtitle.pack(anchor="w", pady=(2, 0))
        theme_frame = self._tk_frame(header, "header")
        theme_frame.pack(side="right", padx=(8, 16), pady=18)
        ttk.Button(theme_frame, text="☼ Claro / ☾ Escuro", command=self.toggle_theme).pack(side="left")
        ttk.Button(theme_frame, text="Sobre", command=self.show_about).pack(side="left", padx=(7, 0))
        self._register_theme_widget(accent, "accent")
        self._register_theme_widget(heading, "header")
        self._register_theme_widget(theme_frame, "header")
        self._register_theme_widget(title, "header_title")
        self._register_theme_widget(subtitle, "header_subtitle")

        folder_card = self._card(outer, padding=11)
        folder_card.grid(row=1, column=0, sticky="ew", pady=(0, 11))
        folder_card.columnconfigure(1, weight=1)
        folder_left = ttk.Frame(folder_card, style="CardInner.TFrame")
        folder_left.grid(row=0, column=0, sticky="w", padx=(0, 16))
        ttk.Label(folder_left, text="ETAPA 1", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(folder_left, text="Pasta de destino", style="Section.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Entry(folder_card, textvariable=self.folder_var, style="Modern.TEntry").grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        ttk.Button(folder_card, text="Procurar pasta…", command=self.browse_folder).grid(row=0, column=2)
        ttk.Checkbutton(
            folder_card,
            text="Incluir subpastas e arquivos dentro delas",
            variable=self.recursive_var,
            style="Card.TCheckbutton",
            command=self._recursive_changed,
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(7, 0))
        ttk.Label(
            folder_card,
            text="As pastas serão exibidas na prévia; renomear uma pasta também leva seus conteúdos junto.",
            style="Hint.TLabel",
        ).grid(row=2, column=1, columnspan=2, sticky="w", pady=(4, 0))

        workspace = ttk.Frame(outer, style="App.TFrame")
        workspace.grid(row=2, column=0, sticky="nsew", pady=(0, 11))
        workspace.columnconfigure(0, weight=0, minsize=330)
        workspace.columnconfigure(1, weight=1, minsize=510)
        workspace.rowconfigure(0, weight=1)

        left_panel = ttk.Frame(workspace, style="App.TFrame")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 11))
        left_panel.rowconfigure(1, weight=1)
        left_panel.columnconfigure(0, weight=1)
        left_intro = ttk.Frame(left_panel, style="App.TFrame")
        left_intro.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(left_intro, text="ETAPA 2", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(left_intro, text="Regras de renomeação", style="AppTitle.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Label(left_intro, text="Combine somente as opções de que precisa.", style="AppText.TLabel").pack(anchor="w", pady=(2, 0))

        scroller = ScrollableFrame(left_panel, self, style="App.TFrame")
        scroller.grid(row=1, column=0, sticky="nsew")
        self.scrollable_frames.append(scroller)
        rules = scroller.inner
        rules.columnconfigure(0, weight=1)

        cut = self._rule_card(rules, "✂  Cortar caracteres", "A extensão dos arquivos será preservada.")
        cut_row = ttk.Frame(cut, style="CardInner.TFrame")
        cut_row.pack(fill="x")
        cut_row.columnconfigure(1, weight=1)
        cut_row.columnconfigure(3, weight=1)
        ttk.Label(cut_row, text="Do início", style="Field.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Spinbox(cut_row, from_=0, to=255, textvariable=self.remove_start_var, style="Modern.TSpinbox", width=5).grid(
            row=0, column=1, sticky="ew", padx=(0, 10)
        )
        ttk.Label(cut_row, text="Do final", style="Field.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Spinbox(cut_row, from_=0, to=255, textvariable=self.remove_end_var, style="Modern.TSpinbox", width=5).grid(
            row=0, column=3, sticky="ew"
        )

        remove = self._rule_card(rules, "↔  Remover termos")
        self._field(remove, "Termos separados por vírgula", self.remove_terms_var)
        ttk.Checkbutton(remove, text="Ignorar maiúsculas/minúsculas", variable=self.ignore_case_var,
                        style="Card.TCheckbutton").pack(anchor="w", pady=(6, 0))

        replace = self._rule_card(rules, "⇄  Substituir texto")
        replace_row = ttk.Frame(replace, style="CardInner.TFrame")
        replace_row.pack(fill="x")
        replace_row.columnconfigure(0, weight=1)
        replace_row.columnconfigure(1, weight=1)
        ttk.Label(replace_row, text="De", style="Field.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 4))
        ttk.Label(replace_row, text="Para", style="Field.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(0, 4))
        ttk.Entry(replace_row, textvariable=self.replace_from_var, style="Modern.TEntry").grid(row=1, column=0, sticky="ew", padx=(0, 6))
        ttk.Entry(replace_row, textvariable=self.replace_to_var, style="Modern.TEntry").grid(row=1, column=1, sticky="ew", padx=(6, 0))

        additions = self._rule_card(rules, "＋  Prefixo e sufixo")
        add_row = ttk.Frame(additions, style="CardInner.TFrame")
        add_row.pack(fill="x")
        add_row.columnconfigure(0, weight=1)
        add_row.columnconfigure(1, weight=1)
        ttk.Label(add_row, text="Prefixo", style="Field.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 4))
        ttk.Label(add_row, text="Sufixo", style="Field.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(0, 4))
        ttk.Entry(add_row, textvariable=self.prefix_var, style="Modern.TEntry").grid(row=1, column=0, sticky="ew", padx=(0, 6))
        ttk.Entry(add_row, textvariable=self.suffix_var, style="Modern.TEntry").grid(row=1, column=1, sticky="ew", padx=(6, 0))

        formatting = self._rule_card(rules, "Aa  Capitalização e ortografia")
        ttk.Label(formatting, text="Estilo de capitalização", style="Field.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Combobox(
            formatting, textvariable=self.case_var, state="readonly", style="Modern.TCombobox",
            values=("Manter", "MAIÚSCULAS", "minúsculas", "Título inteligente (PT-BR)", "Title Case (English)", "Título inteligente (PT-BR/EN)", "Capitalizar palavras"),
        ).pack(fill="x")
        ttk.Checkbutton(formatting, text="Corrigir ortografia automaticamente", variable=self.spellcheck_var,
                        style="Card.TCheckbutton").pack(anchor="w", pady=(8, 4))
        ttk.Label(formatting, text="Idioma da correção", style="Field.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Combobox(
            formatting, textvariable=self.spell_language_var, state="readonly", style="Modern.TCombobox",
            values=("Português (Brasil)", "English"),
        ).pack(fill="x")
        ttk.Label(formatting, text="Vocabulário extra / palavras para preservar", style="Field.TLabel").pack(anchor="w", pady=(8, 4))
        ttk.Entry(formatting, textvariable=self.custom_words_var, style="Modern.TEntry").pack(fill="x")
        ttk.Label(formatting, text="Separe por vírgula. A correção é local e pode errar nomes próprios.",
                  style="Hint.TLabel", wraplength=300, justify="left").pack(anchor="w", pady=(5, 0))

        right_panel = ttk.Frame(workspace, style="App.TFrame")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        right_panel.rowconfigure(2, weight=0)

        stats = ttk.Frame(right_panel, style="App.TFrame")
        stats.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        for col in range(4):
            stats.columnconfigure(col, weight=1)
        self._make_badge(stats, self.item_count_var, "badge_info").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self._make_badge(stats, self.folder_count_var, "badge_info").grid(row=0, column=1, sticky="ew", padx=5)
        self._make_badge(stats, self.change_count_var, "badge_success").grid(row=0, column=2, sticky="ew", padx=5)
        self._make_badge(stats, self.conflict_count_var, "badge_error").grid(row=0, column=3, sticky="ew", padx=(5, 0))

        preview_card = self._card(right_panel, padding=11)
        preview_card.grid(row=1, column=0, sticky="nsew", pady=(0, 9))
        preview_card.columnconfigure(0, weight=1)
        preview_card.rowconfigure(2, weight=1)
        preview_header = ttk.Frame(preview_card, style="CardInner.TFrame")
        preview_header.grid(row=0, column=0, sticky="ew")
        preview_header.columnconfigure(0, weight=1)
        ttk.Label(preview_header, text="ETAPA 3", style="Eyebrow.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(preview_header, text="Pré-visualização de arquivos e pastas", style="Section.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(preview_header, text="Marque as linhas que deseja renomear. Pastas selecionadas levam seus conteúdos junto.",
                  style="Hint.TLabel").grid(row=2, column=0, sticky="w", pady=(3, 0))

        filter_row = ttk.Frame(preview_card, style="CardInner.TFrame")
        filter_row.grid(row=1, column=0, sticky="ew", pady=(10, 8))
        filter_row.columnconfigure(0, weight=1)
        ttk.Entry(filter_row, textvariable=self.search_var, style="Modern.TEntry").grid(row=0, column=0, sticky="ew", padx=(0, 7))
        ttk.Combobox(
            filter_row, textvariable=self.filter_var, state="readonly", style="Modern.TCombobox", width=19,
            values=("Todos os itens", "Para renomear", "Conflitos", "Somente arquivos", "Somente pastas", "Selecionados"),
        ).grid(row=0, column=1, sticky="ew")

        table_area = ttk.Frame(preview_card, style="CardInner.TFrame")
        table_area.grid(row=2, column=0, sticky="nsew")
        table_area.rowconfigure(0, weight=1)
        table_area.columnconfigure(0, weight=1)
        columns = ("select", "kind", "original", "proposed", "status")
        self.preview_tree = ttk.Treeview(table_area, columns=columns, show="headings", height=12, selectmode="browse")
        self.preview_tree.heading("select", text="✓")
        self.preview_tree.heading("kind", text="TIPO")
        self.preview_tree.heading("original", text="NOME ATUAL / CAMINHO")
        self.preview_tree.heading("proposed", text="NOVO NOME / CAMINHO")
        self.preview_tree.heading("status", text="SITUAÇÃO")
        self.preview_tree.column("select", width=44, minwidth=44, stretch=False, anchor="center")
        self.preview_tree.column("kind", width=76, minwidth=68, stretch=False)
        self.preview_tree.column("original", width=190, minwidth=130, stretch=True)
        self.preview_tree.column("proposed", width=205, minwidth=130, stretch=True)
        self.preview_tree.column("status", width=150, minwidth=120, stretch=True)
        self.preview_tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(table_area, orient="vertical", command=self.preview_tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(table_area, orient="horizontal", command=self.preview_tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.preview_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.preview_tree.tag_configure("conflict", foreground=p["red"], background=p["red_soft"])
        self.preview_tree.tag_configure("unchanged", foreground=p["muted"])
        self.preview_tree.tag_configure("changed", foreground=p["green"])
        self.preview_tree.tag_configure("alternate", background=p["row_alt"])
        self.preview_tree.bind("<Button-1>", self._on_tree_click)
        self.preview_tree.bind("<space>", self._on_space)

        select_row = ttk.Frame(preview_card, style="CardInner.TFrame")
        select_row.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(select_row, text="Selecionar alterações", command=self.select_changes).pack(side="left", padx=(0, 6))
        ttk.Button(select_row, text="Desmarcar tudo", command=self.deselect_all).pack(side="left", padx=(0, 6))
        ttk.Button(select_row, text="Inverter seleção", command=self.invert_selection).pack(side="left")
        ttk.Label(select_row, text="Clique na caixa ✓ ou use Espaço para alternar.",
                  style="Hint.TLabel").pack(side="right")

        log_card = self._card(right_panel, padding=10)
        log_card.grid(row=2, column=0, sticky="ew")
        log_card.columnconfigure(0, weight=1)
        log_head = ttk.Frame(log_card, style="CardInner.TFrame")
        log_head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(log_head, text="REGISTRO DE OPERAÇÕES", style="Eyebrow.TLabel").pack(side="left")
        ttk.Label(log_head, textvariable=self.summary_var, style="Hint.TLabel").pack(side="right")
        self.log_text = tk.Text(
            log_card, height=4, wrap="word", font=("Cascadia Code", 9),
            bg=p["log"], fg=p["log_text"], insertbackground=p["white"],
            selectbackground=p["blue"], relief="flat", borderwidth=0, padx=9, pady=7, state="disabled",
        )
        self.log_text.grid(row=1, column=0, sticky="ew")
        self.theme_widgets[self.log_text] = "log"
        log_scroll = ttk.Scrollbar(log_card, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        footer = ttk.Frame(outer, style="App.TFrame")
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.footer_note = ttk.Label(footer, text="✓  Confira a prévia antes de renomear. Ctrl + Enter abre a prévia.",
                                     style="AppText.TLabel")
        self.footer_note.grid(row=0, column=0, sticky="w")
        buttons = ttk.Frame(footer, style="App.TFrame")
        buttons.grid(row=0, column=1, sticky="e")
        ttk.Button(buttons, text="Pré-visualizar", style="Preview.TButton", command=self.preview).pack(side="left", padx=(0, 7))
        ttk.Button(buttons, text="Desfazer último lote", style="Undo.TButton", command=self.undo).pack(side="left", padx=(0, 7))
        ttk.Button(buttons, text="Renomear selecionados →", style="Primary.TButton", command=self.execute).pack(side="left")

    def _make_badge(self, parent: tk.Widget, variable: tk.StringVar, role: str) -> tk.Label:
        label = tk.Label(
            parent, textvariable=variable, font=("Segoe UI", 9, "bold"),
            padx=8, pady=8, relief="flat", borderwidth=0,
        )
        self.theme_widgets[label] = role
        return label

    def toggle_theme(self) -> None:
        self.theme_var.set("Claro" if self.theme_var.get() == "Escuro" else "Escuro")
        self.palette = PALETTES[self.theme_var.get()]
        self._configure_styles()
        self._apply_tk_theme()
        if self.current_items:
            self._render_plan()
        self._log(f"Modo {self.theme_var.get().lower()} ativado.")

    def show_about(self) -> None:
        messagebox.showinfo(
            "Sobre o Renomeador Portátil",
            "Renomeador Portátil\n\n"
            "Renomeia arquivos e pastas em lote, com pré-visualização, seleção individual, "
            "dicionários locais PT-BR/inglês e opção de desfazer o último lote.\n\n"
            "A operação é local. Confira os nomes propostos antes de confirmar.",
        )

    def _log(self, message: str) -> None:
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message.rstrip() + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def browse_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Selecione a pasta a analisar")
        if chosen:
            self.folder_var.set(chosen)
            self.current_folder = Path(chosen)
            self.current_items = []
            self._render_plan()
            self._log(f"Pasta selecionada: {chosen}")

    def _recursive_changed(self) -> None:
        if self.folder_var.get().strip():
            self.preview()

    def _get_folder(self) -> Path | None:
        text = self.folder_var.get().strip().strip('"')
        folder = Path(text) if text else None
        if folder is None or not folder.is_dir():
            messagebox.showerror("Pasta inválida", "Selecione uma pasta existente antes de continuar.")
            return None
        return folder

    def _get_options(self) -> RenameOptions | None:
        try:
            remove_start = int(self.remove_start_var.get())
            remove_end = int(self.remove_end_var.get())
            if remove_start < 0 or remove_end < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Valor inválido",
                "Os campos para cortar caracteres devem conter números inteiros iguais ou maiores que zero.",
            )
            return None

        return RenameOptions(
            remove_start=remove_start,
            remove_end=remove_end,
            remove_terms=[term.strip() for term in self.remove_terms_var.get().split(",") if term.strip()],
            replace_from=self.replace_from_var.get(),
            replace_to=self.replace_to_var.get(),
            prefix=self.prefix_var.get(),
            suffix=self.suffix_var.get(),
            case_mode=self.case_var.get(),
            ignore_case=self.ignore_case_var.get(),
            spellcheck=self.spellcheck_var.get(),
            spell_language=self.spell_language_var.get(),
            custom_words=[word.strip() for word in self.custom_words_var.get().split(",") if word.strip()],
        )

    def _make_plan(self, *, clear_log: bool) -> tuple[Path, list[RenameItem]] | None:
        folder = self._get_folder()
        if folder is None:
            return None
        options = self._get_options()
        if options is None:
            return None

        previous_selection: dict[str, bool] = {}
        if self.current_folder is not None and self.current_folder.resolve() == folder.resolve():
            previous_selection = {item.relative_path: item.selected for item in self.current_items}

        try:
            items = create_plan(folder, options, recursive=self.recursive_var.get())
            for item in items:
                if item.relative_path in previous_selection:
                    item.selected = previous_selection[item.relative_path]
            evaluate_plan(folder, items)
        except (OSError, ValueError, RuntimeError) as error:
            messagebox.showerror("Não foi possível analisar a pasta", str(error))
            return None

        self.current_folder = folder
        self.current_items = items
        self._render_plan()
        if clear_log:
            self._clear_log()
        conflicts = sum(bool(item.error) for item in items)
        changes = sum(item.path_changed and not item.error for item in items)
        self.summary_var.set(f"{len(items)} itens · {changes} caminhos alterados · {conflicts} conflitos")
        self._log(f"Pasta: {folder}")
        self._log(f"Itens analisados: {len(items)} | Mudanças de caminho: {changes} | Conflitos: {conflicts}")
        for item in items:
            if item.path_changed or item.error:
                label = "CONFLITO" if item.error else ("SELECIONADO" if item.selected and item.changed else "MOVIDO COM A PASTA")
                detail = f" — {item.error}" if item.error else ""
                self._log(f"[{label}] {item.relative_path} → {self._display_proposed_path(item)}{detail}")
        if not items:
            self._log("Nenhum arquivo ou subpasta foi encontrado.")
        return folder, items

    def _display_proposed_path(self, item: RenameItem) -> str:
        parts = list(Path(item.relative_path).parts)
        if not parts:
            return item.target_path
        by_path = {row.relative_path: row for row in self.current_items}
        displayed: list[str] = []
        for index, part in enumerate(parts):
            prefix = Path(*parts[:index + 1]).as_posix()
            if index < len(parts) - 1:
                ancestor = by_path.get(prefix)
                if ancestor and ancestor.is_directory and ancestor.selected and ancestor.changed:
                    displayed.append(ancestor.proposed)
                else:
                    displayed.append(part)
            else:
                displayed.append(item.proposed if item.changed else part)
        return "/".join(displayed)

    def _passes_filter(self, item: RenameItem) -> bool:
        query = self.search_var.get().strip().casefold()
        visible_name = f"{item.relative_path} {self._display_proposed_path(item)}".casefold()
        if query and query not in visible_name:
            return False
        choice = self.filter_var.get()
        if choice == "Para renomear":
            return item.path_changed and not item.error
        if choice == "Conflitos":
            return bool(item.error)
        if choice == "Somente arquivos":
            return not item.is_directory
        if choice == "Somente pastas":
            return item.is_directory
        if choice == "Selecionados":
            return item.selected and item.changed
        return True

    def _render_plan(self) -> None:
        if not hasattr(self, "preview_tree"):
            return
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.item_by_iid.clear()
        items = self.current_items
        files = sum(not item.is_directory for item in items)
        folders = sum(item.is_directory for item in items)
        selected_changes = sum(item.selected and item.changed and not item.error for item in items)
        inherited_changes = sum(
            item.path_changed and not (item.selected and item.changed) and not item.error
            for item in items
        )
        conflicts = sum(bool(item.error) for item in items)
        self.item_count_var.set(f"{files} arquivos")
        self.folder_count_var.set(f"{folders} pastas")
        self.change_count_var.set(f"{selected_changes} selecionados")
        self.conflict_count_var.set(f"{conflicts} conflitos")
        if conflicts:
            self.summary_var.set("Corrija os conflitos antes de executar")
        elif selected_changes or inherited_changes:
            self.summary_var.set(f"{selected_changes} nomes serão alterados · {inherited_changes} itens acompanham pastas")
        else:
            self.summary_var.set("Nenhuma alteração selecionada")

        for index, item in enumerate(items):
            if not self._passes_filter(item):
                continue
            iid = item.relative_path
            self.item_by_iid[iid] = item
            check = "☑" if item.selected and item.changed else "☐"
            kind = "Pasta" if item.is_directory else "Arquivo"
            proposed = self._display_proposed_path(item)
            if item.error:
                tag = "conflict"
                status = f"Conflito: {item.error}"
            elif item.path_changed and not (item.selected and item.changed):
                tag = "inherited"
                status = "Acompanha a pasta"
            elif item.selected and item.changed:
                tag = "changed"
                status = "Pasta selecionada" if item.is_directory else "Selecionado"
            elif item.changed:
                tag = "unselected"
                status = "Não selecionado"
            else:
                tag = "unchanged"
                status = "Sem alteração"
            tags = [tag]
            if index % 2:
                tags.append("alternate")
            self.preview_tree.insert(
                "", "end", iid=iid,
                values=(check, kind, item.relative_path, proposed, status),
                tags=tuple(tags),
            )

        p = self.palette
        self.preview_tree.tag_configure("conflict", foreground=p["red"], background=p["red_soft"])
        self.preview_tree.tag_configure("inherited", foreground=p["muted"])
        self.preview_tree.tag_configure("changed", foreground=p["green"])
        self.preview_tree.tag_configure("unselected", foreground=p["muted"])
        self.preview_tree.tag_configure("unchanged", foreground=p["muted"])
        self.preview_tree.tag_configure("alternate", background=p["row_alt"])

    def _on_tree_click(self, event):
        region = self.preview_tree.identify("region", event.x, event.y)
        column = self.preview_tree.identify_column(event.x)
        row = self.preview_tree.identify_row(event.y)
        if region == "cell" and column == "#1" and row in self.item_by_iid:
            item = self.item_by_iid[row]
            if item.changed:
                item.selected = not item.selected
                if self.current_folder:
                    evaluate_plan(self.current_folder, self.current_items)
                self._render_plan()
            return "break"
        return None

    def _on_space(self, _event=None):
        selection = self.preview_tree.selection() if hasattr(self, "preview_tree") else ()
        if selection and selection[0] in self.item_by_iid:
            item = self.item_by_iid[selection[0]]
            if item.changed:
                item.selected = not item.selected
                if self.current_folder:
                    evaluate_plan(self.current_folder, self.current_items)
                self._render_plan()
                return "break"
        return None

    def select_changes(self) -> None:
        for item in self.current_items:
            item.selected = item.changed
        if self.current_folder:
            evaluate_plan(self.current_folder, self.current_items)
        self._render_plan()
        self._log("Selecionadas todas as alterações propostas.")

    def deselect_all(self) -> None:
        for item in self.current_items:
            item.selected = False
        if self.current_folder:
            evaluate_plan(self.current_folder, self.current_items)
        self._render_plan()
        self._log("Todas as alterações foram desmarcadas.")

    def invert_selection(self) -> None:
        for item in self.current_items:
            if item.changed:
                item.selected = not item.selected
        if self.current_folder:
            evaluate_plan(self.current_folder, self.current_items)
        self._render_plan()
        self._log("Seleção invertida.")

    def preview(self) -> None:
        self._make_plan(clear_log=True)

    def execute(self) -> None:
        planned = self._make_plan(clear_log=True)
        if planned is None:
            return
        folder, items = planned
        conflicts = [item for item in items if item.error]
        moves = [
            (item.relative_path, item.proposed)
            for item in items
            if item.selected and item.changed
        ]
        if conflicts:
            messagebox.showerror(
                "Corrija os conflitos",
                "Há nomes inválidos ou destinos ocupados. Nenhum item foi renomeado.\n\n"
                "Consulte a coluna Situação e o registro de operações.",
            )
            return
        if not moves:
            messagebox.showinfo("Nada selecionado", "Selecione na pré-visualização os arquivos ou pastas a renomear.")
            return

        effected = sum(item.path_changed and not item.error for item in items)
        if not messagebox.askyesno(
            "Confirmar renomeação",
            f"{len(moves)} nome(s) serão alterados; {effected} caminho(s) serão afetados nesta pasta:\n\n"
            f"{folder}\n\nO programa salvará o histórico do lote para permitir desfazer. Continuar?",
            icon="warning",
        ):
            self._log("Operação cancelada pelo usuário.")
            return

        try:
            count = apply_recursive_renames(folder, moves)
        except (OSError, RuntimeError, ValueError) as error:
            self._log(f"[ERRO] {error}")
            messagebox.showerror("Renomeação não concluída", str(error))
            return

        self._log(f"Concluído: {count} nome(s) alterado(s). O último lote pode ser desfeito.")
        messagebox.showinfo("Renomeação concluída", f"{count} arquivo(s)/pasta(s) renomeado(s) com sucesso.")
        self._make_plan(clear_log=False)

    def undo(self) -> None:
        folder = self._get_folder()
        if folder is None:
            return
        if not messagebox.askyesno(
            "Desfazer último lote",
            f"Restaurar os nomes do último lote registrado nesta pasta?\n\n{folder}",
            icon="warning",
        ):
            return
        try:
            count, warning = undo_last_renaming(folder)
        except (OSError, RuntimeError, ValueError, FileNotFoundError) as error:
            messagebox.showerror("Não foi possível desfazer", str(error))
            self._log(f"[ERRO AO DESFAZER] {error}")
            return

        self._log(f"Desfeito: {count} nome(s) restaurado(s).")
        if warning:
            self._log("[AVISO] " + warning)
            messagebox.showwarning("Arquivos restaurados com aviso", warning)
        else:
            messagebox.showinfo("Operação desfeita", f"{count} arquivo(s)/pasta(s) restaurado(s).")
        self._make_plan(clear_log=False)


def main() -> None:
    root = tk.Tk()
    RenamerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
