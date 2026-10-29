"""Interface gráfica do Renomeador Portátil (Windows)."""
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


class RenamerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Renomeador Portátil")
        self.root.geometry("1040x790")
        self.root.minsize(880, 650)
        self.root.configure(bg="#f4f6f8")

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 17, "bold"), foreground="#17365d")
        style.configure("Hint.TLabel", foreground="#526171")
        style.configure("Action.TButton", padding=(12, 7))
        style.configure("Treeview", rowheight=25, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

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

        self._build_ui()
        self.root.bind("<Control-Return>", lambda _event: self.preview())
        self._log("Selecione uma pasta, configure as regras e clique em Pré-visualizar.")

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Renomeador Portátil", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Renomeie vários arquivos de uma vez, confira os resultados e desfaça o último lote.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(2, 12))

        folder_frame = ttk.LabelFrame(outer, text="1. Pasta dos arquivos", padding=10)
        folder_frame.pack(fill="x", pady=(0, 9))
        folder_frame.columnconfigure(1, weight=1)
        ttk.Label(folder_frame, text="Pasta:").grid(row=0, column=0, padx=(0, 8), sticky="w")
        ttk.Entry(folder_frame, textvariable=self.folder_var).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(folder_frame, text="Procurar…", command=self.browse_folder).grid(row=0, column=2)
        ttk.Label(
            folder_frame,
            text="Apenas arquivos diretamente nesta pasta serão considerados; subpastas não serão alteradas.",
            style="Hint.TLabel",
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(7, 0))

        rules = ttk.LabelFrame(outer, text="2. Regras de renomeação", padding=10)
        rules.pack(fill="x", pady=(0, 9))
        rules.columnconfigure(0, weight=1, uniform="rules")
        rules.columnconfigure(1, weight=1, uniform="rules")

        cut = ttk.LabelFrame(rules, text="Cortar caracteres do nome (sem a extensão)", padding=8)
        cut.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 7))
        ttk.Label(cut, text="Do início:").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(cut, from_=0, to=255, textvariable=self.remove_start_var, width=7).grid(
            row=0, column=1, padx=(6, 18), sticky="w"
        )
        ttk.Label(cut, text="Do final:").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(cut, from_=0, to=255, textvariable=self.remove_end_var, width=7).grid(
            row=0, column=3, padx=(6, 0), sticky="w"
        )

        remove = ttk.LabelFrame(rules, text="Remover termos", padding=8)
        remove.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 7))
        ttk.Label(remove, text="Termos separados por vírgula:").pack(anchor="w")
        ttk.Entry(remove, textvariable=self.remove_terms_var).pack(fill="x", pady=(4, 5))
        ttk.Checkbutton(
            remove,
            text="Ignorar maiúsculas/minúsculas ao remover e substituir",
            variable=self.ignore_case_var,
        ).pack(anchor="w")

        replace = ttk.LabelFrame(rules, text="Substituir texto", padding=8)
        replace.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(0, 7))
        replace.columnconfigure(1, weight=1)
        replace.columnconfigure(3, weight=1)
        ttk.Label(replace, text="De:").grid(row=0, column=0, sticky="w")
        ttk.Entry(replace, textvariable=self.replace_from_var).grid(
            row=0, column=1, sticky="ew", padx=(5, 10)
        )
        ttk.Label(replace, text="Para:").grid(row=0, column=2, sticky="w")
        ttk.Entry(replace, textvariable=self.replace_to_var).grid(
            row=0, column=3, sticky="ew", padx=(5, 0)
        )

        additions = ttk.LabelFrame(rules, text="Adicionar e formatar", padding=8)
        additions.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=(0, 7))
        additions.columnconfigure(1, weight=1)
        additions.columnconfigure(3, weight=1)
        ttk.Label(additions, text="Prefixo:").grid(row=0, column=0, sticky="w")
        ttk.Entry(additions, textvariable=self.prefix_var).grid(
            row=0, column=1, sticky="ew", padx=(5, 10)
        )
        ttk.Label(additions, text="Sufixo:").grid(row=0, column=2, sticky="w")
        ttk.Entry(additions, textvariable=self.suffix_var).grid(
            row=0, column=3, sticky="ew", padx=(5, 0)
        )
        ttk.Label(additions, text="Maiúsculas/minúsculas:").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(9, 0)
        )
        ttk.Combobox(
            additions,
            textvariable=self.case_var,
            state="readonly",
            values=("Manter", "MAIÚSCULAS", "minúsculas", "Título inteligente (PT-BR)", "Title Case (English)"),
            width=25,
        ).grid(row=1, column=2, columnspan=2, sticky="ew", pady=(7, 0))
        ttk.Checkbutton(
            additions,
            text="Corrigir ortografia automaticamente (opcional)",
            variable=self.spellcheck_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(9, 0))
        ttk.Label(additions, text="Idioma:").grid(row=2, column=2, sticky="e", padx=(8, 5), pady=(9, 0))
        ttk.Combobox(
            additions,
            textvariable=self.spell_language_var,
            state="readonly",
            values=("Português (Brasil)", "English"),
            width=18,
        ).grid(row=2, column=3, sticky="ew", pady=(7, 0))
        ttk.Label(
            additions,
            text="A correção é local; confira a prévia, pois nomes próprios podem ser alterados.",
            style="Hint.TLabel",
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(7, 0))

        action_row = ttk.Frame(outer)
        action_row.pack(fill="x", pady=(0, 8))
        ttk.Button(
            action_row,
            text="Pré-visualizar",
            style="Action.TButton",
            command=self.preview,
        ).pack(side="left", padx=(0, 7))
        ttk.Button(
            action_row,
            text="Renomear arquivos",
            style="Action.TButton",
            command=self.execute,
        ).pack(side="left", padx=(0, 7))
        ttk.Button(
            action_row,
            text="Desfazer último lote",
            style="Action.TButton",
            command=self.undo,
        ).pack(side="left")
        ttk.Label(action_row, text="Atalho: Ctrl + Enter para pré-visualizar", style="Hint.TLabel").pack(
            side="right"
        )

        preview_frame = ttk.LabelFrame(outer, text="3. Pré-visualização", padding=7)
        preview_frame.pack(fill="both", expand=True, pady=(0, 8))
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        columns = ("original", "proposed", "status")
        self.preview_tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=8)
        self.preview_tree.heading("original", text="Nome atual")
        self.preview_tree.heading("proposed", text="Novo nome")
        self.preview_tree.heading("status", text="Situação")
        self.preview_tree.column("original", width=310, minwidth=140)
        self.preview_tree.column("proposed", width=310, minwidth=140)
        self.preview_tree.column("status", width=250, minwidth=150)
        self.preview_tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.preview_tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.preview_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.preview_tree.tag_configure("conflict", foreground="#b42318")
        self.preview_tree.tag_configure("unchanged", foreground="#65717e")

        log_frame = ttk.LabelFrame(outer, text="Registro de operações", padding=7)
        log_frame.pack(fill="x")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=5, wrap="word", font=("Consolas", 9), state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

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
        for item in items:
            tag = "conflict" if item.error else ("unchanged" if not item.changed else "")
            status = f"Conflito: {item.error}" if item.error else item.status
            self.preview_tree.insert(
                "",
                "end",
                values=(item.original, item.proposed, status),
                tags=(tag,) if tag else (),
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
        self._log(f"Arquivos analisados: {len(items)} | Mudanças propostas: {changed} | Conflitos: {conflicts}")
        for item in items:
            if item.changed:
                label = "CONFLITO" if item.error else "PRÉVIA"
                detail = f" — {item.error}" if item.error else ""
                self._log(f"[{label}] {item.original} -> {item.proposed}{detail}")
        if not items:
            self._log("Não há arquivos para processar nesta pasta.")
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
