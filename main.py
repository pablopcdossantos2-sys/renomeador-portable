"""Interface gráfica moderna do Renomeador Portátil para Windows."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from renamer import (
    RenameItem,
    RenameOptions,
    apply_renames,
    create_plan,
    undo_last_renaming,
)


COLORS = {
    "app": "#eef2f7",
    "surface": "#ffffff",
    "navy": "#17263d",
    "navy_light": "#253955",
    "ink": "#1c2c43",
    "muted": "#65748a",
    "border": "#dbe3ee",
    "blue": "#3867e8",
    "blue_hover": "#2854cf",
    "blue_soft": "#eaf0ff",
    "green": "#16835d",
    "green_soft": "#e8f6ef",
    "red": "#bd3444",
    "red_soft": "#fff0f1",
    "amber": "#9a6514",
    "amber_soft": "#fff6df",
    "row_alt": "#f7f9fc",
    "log": "#142238",
    "log_text": "#d6e0f0",
}


class ScrollableFrame(ttk.Frame):
    """Área de regras rolável para não comprimir os controles em telas menores."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(
            self,
            background=COLORS["app"],
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
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.inner.bind("<Enter>", self._bind_mousewheel)
        self.inner.bind("<Leave>", self._unbind_mousewheel)

    def _update_scrollregion(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _bind_mousewheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class RenamerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Renomeador Portátil")
        self.root.geometry("1200x850")
        self.root.minsize(960, 700)
        self.root.configure(bg=COLORS["app"])

        self._configure_styles()

        self.folder_var = tk.StringVar()
        self.remove_start_var = tk.StringVar(value="0")
        self.remove_end_var = tk.StringVar(value="0")
        self.remove_terms_var = tk.StringVar()
        self.replace_from_var = tk.StringVar()
        self.replace_to_var = tk.StringVar()
        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.case_var = tk.StringVar(value="Manter")
        self.ignore_case_var = tk.BooleanVar(value=False)
        self.spellcheck_var = tk.BooleanVar(value=False)
        self.spell_language_var = tk.StringVar(value="Português (Brasil)")
        self.summary_var = tk.StringVar(value="Aguardando pré-visualização")
        self.file_count_var = tk.StringVar(value="0 arquivos")
        self.change_count_var = tk.StringVar(value="0 mudanças")
        self.conflict_count_var = tk.StringVar(value="0 conflitos")

        self._build_ui()
        self.root.bind("<Control-Return>", lambda _event: self.preview())
        self._log("Bem-vindo! Escolha uma pasta e clique em Pré-visualizar para conferir as mudanças.")

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=COLORS["app"])
        style.configure("Card.TFrame", background=COLORS["surface"])
        style.configure("CardInner.TFrame", background=COLORS["surface"])
        style.configure(
            "Title.TLabel",
            background=COLORS["navy"],
            foreground="#ffffff",
            font=("Segoe UI", 21, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["navy"],
            foreground="#c4d0e2",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Eyebrow.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["blue"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Section.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["ink"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Hint.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Field.TLabel",
            background=COLORS["surface"],
            foreground="#45556b",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "TButton",
            font=("Segoe UI", 10),
            padding=(11, 7),
            background="#e8edf5",
            foreground=COLORS["ink"],
            borderwidth=0,
        )
        style.map(
            "TButton",
            background=[("active", "#dce5f2"), ("disabled", "#edf0f4")],
            foreground=[("disabled", "#9aa5b4")],
        )
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 9),
            background=COLORS["blue"],
            foreground="#ffffff",
        )
        style.map(
            "Primary.TButton",
            background=[("active", COLORS["blue_hover"]), ("pressed", COLORS["blue_hover"])],
            foreground=[("disabled", "#e3e8f2")],
        )
        style.configure(
            "Preview.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
            background=COLORS["blue_soft"],
            foreground=COLORS["blue"],
        )
        style.map("Preview.TButton", background=[("active", "#dbe5ff")])
        style.configure(
            "Undo.TButton",
            font=("Segoe UI", 10),
            padding=(12, 9),
            background=COLORS["surface"],
            foreground=COLORS["ink"],
            bordercolor=COLORS["border"],
        )
        style.map("Undo.TButton", background=[("active", "#f2f5fa")])
        style.configure(
            "Modern.TEntry",
            padding=(8, 7),
            fieldbackground="#fbfcfe",
            foreground=COLORS["ink"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
            insertcolor=COLORS["ink"],
        )
        style.map(
            "Modern.TEntry",
            fieldbackground=[("focus", "#ffffff")],
            bordercolor=[("focus", COLORS["blue"])],
        )
        style.configure(
            "Modern.TSpinbox",
            padding=(5, 5),
            fieldbackground="#fbfcfe",
            foreground=COLORS["ink"],
            bordercolor=COLORS["border"],
        )
        style.configure(
            "Modern.TCombobox",
            padding=(6, 6),
            fieldbackground="#fbfcfe",
            foreground=COLORS["ink"],
            bordercolor=COLORS["border"],
            arrowcolor=COLORS["muted"],
        )
        style.map(
            "Modern.TCombobox",
            fieldbackground=[("readonly", "#fbfcfe"), ("focus", "#ffffff")],
            bordercolor=[("focus", COLORS["blue"])],
        )
        style.configure(
            "Card.TCheckbutton",
            background=COLORS["surface"],
            foreground=COLORS["ink"],
            font=("Segoe UI", 9),
            padding=(0, 3),
        )
        style.map("Card.TCheckbutton", background=[("active", COLORS["surface"])])
        style.configure(
            "Treeview",
            background=COLORS["surface"],
            fieldbackground=COLORS["surface"],
            foreground=COLORS["ink"],
            rowheight=29,
            bordercolor=COLORS["border"],
            borderwidth=1,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#f1f5fa",
            foreground="#43536a",
            font=("Segoe UI", 9, "bold"),
            padding=(8, 9),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", "#dbe7ff")],
            foreground=[("selected", COLORS["ink"])],
        )
        style.configure(
            "Vertical.TScrollbar",
            background="#e4eaf2",
            troughcolor=COLORS["app"],
            bordercolor=COLORS["app"],
            arrowcolor=COLORS["muted"],
        )

    def _card(self, parent: tk.Widget, padding: int = 12) -> ttk.Frame:
        return ttk.Frame(parent, style="Card.TFrame", padding=padding)

    def _section_header(
        self,
        parent: tk.Widget,
        eyebrow: str,
        title: str,
        description: str | None = None,
    ) -> None:
        ttk.Label(parent, text=eyebrow.upper(), style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(parent, text=title, style="Section.TLabel").pack(anchor="w", pady=(2, 0))
        if description:
            ttk.Label(
                parent,
                text=description,
                style="Hint.TLabel",
                wraplength=320,
                justify="left",
            ).pack(anchor="w", pady=(3, 0))

    def _rule_card(self, parent: tk.Widget, title: str) -> ttk.Frame:
        card = self._card(parent, padding=11)
        card.pack(fill="x", pady=(0, 9))
        ttk.Label(card, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        return card

    def _field(self, parent: tk.Widget, label: str, variable: tk.StringVar, **kwargs) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w", pady=(0, 4))
        entry = ttk.Entry(parent, textvariable=variable, style="Modern.TEntry", **kwargs)
        entry.pack(fill="x")
        return entry

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=(16, 14, 16, 12))
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        # Header visual with brand mark and concise product positioning.
        header = tk.Frame(outer, bg=COLORS["navy"], height=88, highlightthickness=0)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_propagate(False)
        tk.Frame(header, bg=COLORS["blue"], width=5).pack(side="left", fill="y")
        logo = tk.Label(
            header,
            text="R",
            bg=COLORS["blue"],
            fg="#ffffff",
            font=("Segoe UI", 21, "bold"),
            width=2,
            height=1,
        )
        logo.pack(side="left", padx=(16, 12), pady=18)
        heading = tk.Frame(header, bg=COLORS["navy"])
        heading.pack(side="left", fill="both", expand=True, pady=14)
        ttk.Label(heading, text="Renomeador Portátil", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            heading,
            text="Renomeie em lote com controle, prévia e opção de desfazer.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            header,
            text="WINDOWS  •  PORTÁTIL",
            bg=COLORS["navy_light"],
            fg="#dbe6f8",
            font=("Segoe UI", 8, "bold"),
            padx=12,
            pady=7,
        ).pack(side="right", padx=18, pady=26)

        # Folder selector as a full-width card.
        folder_card = self._card(outer, padding=12)
        folder_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        folder_card.columnconfigure(1, weight=1)
        folder_label = ttk.Frame(folder_card, style="CardInner.TFrame")
        folder_label.grid(row=0, column=0, sticky="w", padx=(0, 16))
        ttk.Label(folder_label, text="ETAPA 1", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(folder_label, text="Pasta dos arquivos", style="Section.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Entry(
            folder_card,
            textvariable=self.folder_var,
            style="Modern.TEntry",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(folder_card, text="Procurar pasta…", command=self.browse_folder).grid(
            row=0, column=2, sticky="ew"
        )
        ttk.Label(
            folder_card,
            text="Serão considerados apenas os arquivos diretamente nesta pasta; subpastas não serão alteradas.",
            style="Hint.TLabel",
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(7, 0))

        # Main workspace: scrollable rules on the left and results on the right.
        workspace = ttk.Frame(outer, style="App.TFrame")
        workspace.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        workspace.columnconfigure(0, weight=0, minsize=350)
        workspace.columnconfigure(1, weight=1, minsize=470)
        workspace.rowconfigure(0, weight=1)

        left_panel = ttk.Frame(workspace, style="App.TFrame")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left_panel.rowconfigure(1, weight=1)
        left_panel.columnconfigure(0, weight=1)
        left_intro = ttk.Frame(left_panel, style="App.TFrame")
        left_intro.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(left_intro, text="ETAPA 2", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(
            left_intro,
            text="Regras de renomeação",
            font=("Segoe UI", 12, "bold"),
            background=COLORS["app"],
            foreground=COLORS["ink"],
        ).pack(anchor="w", pady=(2, 0))
        ttk.Label(
            left_intro,
            text="Combine apenas as opções de que precisa.",
            font=("Segoe UI", 9),
            background=COLORS["app"],
            foreground=COLORS["muted"],
        ).pack(anchor="w", pady=(2, 0))

        scroller = ScrollableFrame(left_panel, style="App.TFrame")
        scroller.grid(row=1, column=0, sticky="nsew")
        rules = scroller.inner
        rules.columnconfigure(0, weight=1)

        cut = self._rule_card(rules, "Cortar caracteres")
        ttk.Label(
            cut,
            text="A extensão do arquivo será preservada.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 7))
        cut_row = ttk.Frame(cut, style="CardInner.TFrame")
        cut_row.pack(fill="x")
        cut_row.columnconfigure(1, weight=1)
        cut_row.columnconfigure(3, weight=1)
        ttk.Label(cut_row, text="Do início", style="Field.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Spinbox(
            cut_row,
            from_=0,
            to=255,
            textvariable=self.remove_start_var,
            style="Modern.TSpinbox",
            width=5,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Label(cut_row, text="Do final", style="Field.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Spinbox(
            cut_row,
            from_=0,
            to=255,
            textvariable=self.remove_end_var,
            style="Modern.TSpinbox",
            width=5,
        ).grid(row=0, column=3, sticky="ew")

        remove = self._rule_card(rules, "Remover termos")
        self._field(remove, "Termos separados por vírgula", self.remove_terms_var)
        ttk.Checkbutton(
            remove,
            text="Ignorar maiúsculas/minúsculas",
            variable=self.ignore_case_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(6, 0))

        replace = self._rule_card(rules, "Substituir texto")
        replace.columnconfigure(0, weight=1)
        replace.columnconfigure(1, weight=1)
        replace_row = ttk.Frame(replace, style="CardInner.TFrame")
        replace_row.pack(fill="x")
        replace_row.columnconfigure(0, weight=1)
        replace_row.columnconfigure(1, weight=1)
        ttk.Label(replace_row, text="De", style="Field.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 4))
        ttk.Label(replace_row, text="Para", style="Field.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(0, 4))
        ttk.Entry(replace_row, textvariable=self.replace_from_var, style="Modern.TEntry").grid(
            row=1, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Entry(replace_row, textvariable=self.replace_to_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", padx=(6, 0)
        )
        ttk.Label(
            replace,
            text="Deixe “De” vazio para desativar a substituição.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        additions = self._rule_card(rules, "Prefixo e sufixo")
        additions_row = ttk.Frame(additions, style="CardInner.TFrame")
        additions_row.pack(fill="x")
        additions_row.columnconfigure(0, weight=1)
        additions_row.columnconfigure(1, weight=1)
        ttk.Label(additions_row, text="Prefixo", style="Field.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 4))
        ttk.Label(additions_row, text="Sufixo", style="Field.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(0, 4))
        ttk.Entry(additions_row, textvariable=self.prefix_var, style="Modern.TEntry").grid(
            row=1, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Entry(additions_row, textvariable=self.suffix_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", padx=(6, 0)
        )

        formatting = self._rule_card(rules, "Formatação e idioma")
        self._field(formatting, "Capitalização", self.case_var)
        case_combo = formatting.winfo_children()[-1]
        case_combo.configure(
            state="readonly",
        )
        # Replace the generic entry above with the intended read-only selector.
        case_combo.destroy()
        ttk.Combobox(
            formatting,
            textvariable=self.case_var,
            state="readonly",
            style="Modern.TCombobox",
            values=(
                "Manter",
                "MAIÚSCULAS",
                "minúsculas",
                "Título inteligente (PT-BR)",
                "Title Case (English)",
            ),
        ).pack(fill="x")
        ttk.Checkbutton(
            formatting,
            text="Corrigir ortografia automaticamente",
            variable=self.spellcheck_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(9, 4))
        ttk.Label(formatting, text="Idioma da correção", style="Field.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Combobox(
            formatting,
            textvariable=self.spell_language_var,
            state="readonly",
            style="Modern.TCombobox",
            values=("Português (Brasil)", "English"),
        ).pack(fill="x")
        ttk.Label(
            formatting,
            text="A correção é local. Confira a prévia, pois nomes próprios podem ser alterados.",
            style="Hint.TLabel",
            wraplength=300,
            justify="left",
        ).pack(anchor="w", pady=(7, 0))

        # Result pane.
        right_panel = ttk.Frame(workspace, style="App.TFrame")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=4)
        right_panel.rowconfigure(1, weight=1)

        preview_card = self._card(right_panel, padding=12)
        preview_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        preview_card.columnconfigure(0, weight=1)
        preview_card.rowconfigure(2, weight=1)

        preview_head = ttk.Frame(preview_card, style="CardInner.TFrame")
        preview_head.grid(row=0, column=0, sticky="ew")
        preview_head.columnconfigure(0, weight=1)
        ttk.Label(preview_head, text="ETAPA 3", style="Eyebrow.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            preview_head,
            text="Pré-visualização dos arquivos",
            style="Section.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(
            preview_head,
            text="Nenhum arquivo é alterado antes da sua confirmação.",
            style="Hint.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(3, 0))

        badges = ttk.Frame(preview_card, style="CardInner.TFrame")
        badges.grid(row=1, column=0, sticky="ew", pady=(12, 10))
        self._make_badge(badges, self.file_count_var, "#edf2f8", "#41536c").pack(side="left", padx=(0, 6))
        self._make_badge(badges, self.change_count_var, COLORS["green_soft"], COLORS["green"]).pack(side="left", padx=(0, 6))
        self._make_badge(badges, self.conflict_count_var, COLORS["red_soft"], COLORS["red"]).pack(side="left")

        table_area = ttk.Frame(preview_card, style="CardInner.TFrame")
        table_area.grid(row=2, column=0, sticky="nsew")
        table_area.rowconfigure(0, weight=1)
        table_area.columnconfigure(0, weight=1)
        columns = ("original", "proposed", "status")
        self.preview_tree = ttk.Treeview(table_area, columns=columns, show="headings", height=10)
        self.preview_tree.heading("original", text="NOME ATUAL")
        self.preview_tree.heading("proposed", text="NOVO NOME")
        self.preview_tree.heading("status", text="SITUAÇÃO")
        self.preview_tree.column("original", width=190, minwidth=120, stretch=True)
        self.preview_tree.column("proposed", width=205, minwidth=120, stretch=True)
        self.preview_tree.column("status", width=140, minwidth=95, stretch=True)
        self.preview_tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(table_area, orient="vertical", command=self.preview_tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(table_area, orient="horizontal", command=self.preview_tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.preview_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.preview_tree.tag_configure("conflict", foreground=COLORS["red"], background=COLORS["red_soft"])
        self.preview_tree.tag_configure("unchanged", foreground="#78869a")
        self.preview_tree.tag_configure("changed", foreground=COLORS["green"])
        self.preview_tree.tag_configure("alternate", background=COLORS["row_alt"])

        log_card = self._card(right_panel, padding=10)
        log_card.grid(row=1, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)
        log_heading = ttk.Frame(log_card, style="CardInner.TFrame")
        log_heading.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ttk.Label(log_heading, text="ATIVIDADE", style="Eyebrow.TLabel").pack(side="left")
        ttk.Label(log_heading, textvariable=self.summary_var, style="Hint.TLabel").pack(side="right")
        self.log_text = tk.Text(
            log_card,
            height=5,
            wrap="word",
            font=("Cascadia Code", 9),
            bg=COLORS["log"],
            fg=COLORS["log_text"],
            insertbackground="#ffffff",
            selectbackground=COLORS["blue"],
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=8,
            state="disabled",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_card, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        # Fixed bottom action bar keeps the most important actions easy to find.
        footer = ttk.Frame(outer, style="App.TFrame")
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        note = ttk.Frame(footer, style="App.TFrame")
        note.grid(row=0, column=0, sticky="w")
        tk.Label(
            note,
            text="✓",
            bg=COLORS["green_soft"],
            fg=COLORS["green"],
            font=("Segoe UI", 11, "bold"),
            width=2,
            pady=4,
        ).pack(side="left", padx=(0, 8))
        ttk.Label(
            note,
            text="Confira os nomes antes de executar. Ctrl + Enter faz a prévia.",
            font=("Segoe UI", 9),
            background=COLORS["app"],
            foreground=COLORS["muted"],
        ).pack(side="left")

        action_buttons = ttk.Frame(footer, style="App.TFrame")
        action_buttons.grid(row=0, column=1, sticky="e")
        ttk.Button(
            action_buttons,
            text="Pré-visualizar",
            style="Preview.TButton",
            command=self.preview,
        ).pack(side="left", padx=(0, 7))
        ttk.Button(
            action_buttons,
            text="Desfazer último lote",
            style="Undo.TButton",
            command=self.undo,
        ).pack(side="left", padx=(0, 7))
        ttk.Button(
            action_buttons,
            text="Renomear arquivos  →",
            style="Primary.TButton",
            command=self.execute,
        ).pack(side="left")

    def _make_badge(self, parent: tk.Widget, variable: tk.StringVar, background: str, foreground: str) -> tk.Label:
        return tk.Label(
            parent,
            textvariable=variable,
            bg=background,
            fg=foreground,
            font=("Segoe UI", 8, "bold"),
            padx=9,
            pady=5,
        )

    def _log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message.rstrip() + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def browse_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Selecione a pasta dos arquivos")
        if chosen:
            self.folder_var.set(chosen)
            self._log(f"Pasta selecionada: {chosen}")

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
        )

    def _show_plan(self, items: list[RenameItem]) -> None:
        self.preview_tree.delete(*self.preview_tree.get_children())
        changes = sum(item.changed for item in items)
        conflicts = sum(bool(item.error) for item in items)
        self.file_count_var.set(f"{len(items)} arquivo(s)")
        self.change_count_var.set(f"{changes} mudança(s)")
        self.conflict_count_var.set(f"{conflicts} conflito(s)")
        if conflicts:
            self.summary_var.set("Corrija os conflitos antes de executar")
        elif changes:
            self.summary_var.set("Prévia pronta para conferência")
        else:
            self.summary_var.set("Nenhuma mudança necessária")

        for index, item in enumerate(items):
            if item.error:
                tag = "conflict"
                status = f"Conflito — {item.error}"
            elif not item.changed:
                tag = "unchanged"
                status = "Sem alteração"
            else:
                tag = "changed"
                status = "Pronto"
            if index % 2 and not item.error and item.changed:
                tag = "changed"
            self.preview_tree.insert(
                "",
                "end",
                values=(item.original, item.proposed, status),
                tags=(tag,),
            )

    def _make_plan(self, *, clear_log: bool) -> tuple[Path, list[RenameItem]] | None:
        folder = self._get_folder()
        if folder is None:
            return None
        options = self._get_options()
        if options is None:
            return None
        try:
            items = create_plan(folder, options)
        except (OSError, ValueError, RuntimeError) as error:
            messagebox.showerror("Não foi possível analisar a pasta", str(error))
            return None
        self._show_plan(items)
        if clear_log:
            self._clear_log()
        changed = sum(item.changed for item in items)
        conflicts = sum(bool(item.error) for item in items)
        self._log(f"Pasta: {folder}")
        self._log(f"Arquivos analisados: {len(items)} | Mudanças: {changed} | Conflitos: {conflicts}")
        for item in items:
            if item.changed:
                label = "CONFLITO" if item.error else "PRÉVIA"
                detail = f" — {item.error}" if item.error else ""
                self._log(f"[{label}] {item.original} → {item.proposed}{detail}")
        if not items:
            self._log("Nenhum arquivo foi encontrado nesta pasta.")
        return folder, items

    def preview(self) -> None:
        self._make_plan(clear_log=True)

    def execute(self) -> None:
        planned = self._make_plan(clear_log=True)
        if planned is None:
            return
        folder, items = planned
        conflicts = [item for item in items if item.error]
        moves = [(item.original, item.proposed) for item in items if item.changed]
        if conflicts:
            messagebox.showerror(
                "Corrija os conflitos",
                "Há nomes inválidos ou destinos ocupados. Nenhum arquivo foi renomeado.\n\n"
                "Veja os detalhes na pré-visualização e no registro.",
            )
            return
        if not moves:
            messagebox.showinfo("Nada a renomear", "As regras atuais não alteram nenhum nome.")
            return

        if not messagebox.askyesno(
            "Confirmar renomeação",
            f"{len(moves)} arquivo(s) serão renomeados nesta pasta:\n\n{folder}\n\n"
            "O programa salvará o histórico para permitir desfazer este lote. Continuar?",
            icon="warning",
        ):
            self._log("Operação cancelada pelo usuário.")
            return

        try:
            count = apply_renames(folder, moves)
        except (OSError, RuntimeError, ValueError) as error:
            self._log(f"[ERRO] {error}")
            messagebox.showerror("Renomeação não concluída", str(error))
            return

        self._log(f"Concluído: {count} arquivo(s) renomeado(s). O último lote pode ser desfeito.")
        messagebox.showinfo("Renomeação concluída", f"{count} arquivo(s) renomeado(s) com sucesso.")
        try:
            fresh_plan = create_plan(folder, self._get_options() or RenameOptions())
            self._show_plan(fresh_plan)
        except (OSError, RuntimeError):
            pass

    def undo(self) -> None:
        folder = self._get_folder()
        if folder is None:
            return
        if not messagebox.askyesno(
            "Desfazer último lote",
            f"Restaurar os nomes originais do último lote registrado nesta pasta?\n\n{folder}",
            icon="warning",
        ):
            return
        try:
            count, warning = undo_last_renaming(folder)
        except (OSError, RuntimeError, ValueError, FileNotFoundError) as error:
            messagebox.showerror("Não foi possível desfazer", str(error))
            self._log(f"[ERRO AO DESFAZER] {error}")
            return

        self._log(f"Desfeito: {count} arquivo(s) restaurado(s).")
        if warning:
            self._log("[AVISO] " + warning)
            messagebox.showwarning("Arquivos restaurados com aviso", warning)
        else:
            messagebox.showinfo("Operação desfeita", f"{count} arquivo(s) restaurado(s).")
        try:
            fresh_plan = create_plan(folder, self._get_options() or RenameOptions())
            self._show_plan(fresh_plan)
        except (OSError, RuntimeError):
            pass


def main() -> None:
    root = tk.Tk()
    RenamerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
