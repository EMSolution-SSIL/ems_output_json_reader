"""Standalone Tk/Matplotlib selector for every series in an output.json file."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import OutputData, PostSeries


def launch_plot(output: OutputData) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        from matplotlib.figure import Figure
    except ImportError as exc:
        raise ImportError("グラフ画面には matplotlib と tkinter が必要です。pip install 'emso-post[plot]' を実行してください") from exc

    root = tk.Tk()
    root.title(f"EMSolution ポスト結果: {output.path.name}")
    root.geometry("1200x760")

    outer = ttk.Frame(root, padding=10)
    outer.pack(fill="both", expand=True)
    selector = ttk.Frame(outer)
    selector.pack(side="left", fill="y", padx=(0, 12))
    chart = ttk.Frame(outer)
    chart.pack(side="right", fill="both", expand=True)

    posts = list(dict.fromkeys(s.post for s in output.series))
    if not posts:
        root.destroy()
        raise RuntimeError("グラフにできる時系列がありません")

    post_var = tk.StringVar(value=posts[0])
    group_var = tk.StringVar()
    axis_var = tk.StringVar(value="time")
    id_filter = tk.StringVar()
    field_filter = tk.StringVar()
    id_keys: list[tuple[tuple[str, int | str], ...]] = []
    field_names: list[str] = []

    ttk.Label(selector, text="ポストデータ種別").pack(anchor="w")
    post_box = ttk.Combobox(selector, textvariable=post_var, values=posts, state="readonly", width=32)
    post_box.pack(fill="x", pady=(0, 8))
    ttk.Label(selector, text="データ群").pack(anchor="w")
    group_box = ttk.Combobox(selector, textvariable=group_var, state="readonly", width=32)
    group_box.pack(fill="x", pady=(0, 8))

    ttk.Label(selector, text="ID 検索").pack(anchor="w")
    ttk.Entry(selector, textvariable=id_filter).pack(fill="x")
    ttk.Label(selector, text="ID（複数選択可）").pack(anchor="w", pady=(4, 0))
    id_frame = ttk.Frame(selector)
    id_frame.pack(fill="both", expand=True)
    id_list = tk.Listbox(id_frame, selectmode="extended", exportselection=False, height=8, width=38)
    id_scroll = ttk.Scrollbar(id_frame, orient="vertical", command=id_list.yview)
    id_list.configure(yscrollcommand=id_scroll.set)
    id_list.pack(side="left", fill="both", expand=True)
    id_scroll.pack(side="right", fill="y")

    ttk.Label(selector, text="項目検索").pack(anchor="w", pady=(8, 0))
    ttk.Entry(selector, textvariable=field_filter).pack(fill="x")
    ttk.Label(selector, text="項目（複数選択可）").pack(anchor="w", pady=(4, 0))
    field_frame = ttk.Frame(selector)
    field_frame.pack(fill="both", expand=True)
    field_list = tk.Listbox(field_frame, selectmode="extended", exportselection=False, height=6, width=38)
    field_scroll = ttk.Scrollbar(field_frame, orient="vertical", command=field_list.yview)
    field_list.configure(yscrollcommand=field_scroll.set)
    field_list.pack(side="left", fill="both", expand=True)
    field_scroll.pack(side="right", fill="y")

    ttk.Label(selector, text="横軸").pack(anchor="w", pady=(8, 0))
    axis_box = ttk.Combobox(selector, textvariable=axis_var, values=list(output.axes), state="readonly", width=32)
    axis_box.pack(fill="x", pady=(0, 8))
    info = ttk.Label(selector, text="ID と項目を選択してください", wraplength=280)
    info.pack(anchor="w", pady=(6, 0))
    ttk.Label(selector, text="選択プレビュー（先頭 3 点）").pack(anchor="w", pady=(8, 0))
    preview = ttk.Treeview(selector, columns=("series", "unit", "values"), show="headings", height=5)
    preview.heading("series", text="系列")
    preview.heading("unit", text="単位")
    preview.heading("values", text="先頭値")
    preview.column("series", width=155)
    preview.column("unit", width=50)
    preview.column("values", width=135)
    preview.pack(fill="x")

    figure = Figure(figsize=(7, 5), dpi=100)
    canvas = FigureCanvasTkAgg(figure, master=chart)
    toolbar = NavigationToolbar2Tk(canvas, chart, pack_toolbar=False)
    toolbar.pack(side="bottom", fill="x")
    canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    def group_series() -> list[PostSeries]:
        return output.series_for(post_var.get(), group_var.get())

    def refresh_groups(_event: object = None) -> None:
        groups = list(dict.fromkeys(s.group for s in output.series_for(post_var.get())))
        group_box.configure(values=groups)
        group_var.set(groups[0] if groups else "")
        refresh_ids()

    def refresh_ids(*_args: object) -> None:
        id_list.delete(0, "end")
        id_keys.clear()
        seen_ids: set[tuple[tuple[str, int | str], ...]] = set()
        query = id_filter.get().casefold()
        for series in group_series():
            identity = series.identity
            label = series.id_label
            if identity not in seen_ids and query in label.casefold():
                seen_ids.add(identity)
                id_keys.append(identity)
                id_list.insert("end", label)
        if id_keys:
            id_list.selection_set(0)
        refresh_fields()

    def refresh_fields(*_args: object) -> None:
        field_list.delete(0, "end")
        field_names.clear()
        chosen_ids = {id_keys[i] for i in id_list.curselection()}
        query = field_filter.get().casefold()
        for series in group_series():
            if series.identity in chosen_ids and series.field not in field_names and query in series.field.casefold():
                field_names.append(series.field)
                field_list.insert("end", series.field)
        if field_names:
            field_list.selection_set(0)
        refresh_preview()

    def selected_series() -> list[PostSeries]:
        identities = {id_keys[i] for i in id_list.curselection()}
        fields = {field_names[i] for i in field_list.curselection()}
        return [s for s in group_series() if s.identity in identities and s.field in fields]

    def refresh_preview(_event: object = None) -> None:
        preview.delete(*preview.get_children())
        chosen = selected_series()
        for series in chosen[:100]:
            sample = ", ".join(str(value) for value in series.values[:3])
            preview.insert("", "end", values=(f"{series.id_label} {series.field}", series.unit, sample))
        info.configure(text=f"{len(chosen)} 系列を選択中" if chosen else "ID と項目を選択してください")

    def draw() -> None:
        chosen = selected_series()
        if not chosen:
            messagebox.showinfo("選択してください", "ID と項目を選択してください", parent=root)
            return
        axis = output.axes[axis_var.get()]
        by_unit: dict[str, list[PostSeries]] = defaultdict(list)
        for series in chosen:
            by_unit[series.unit].append(series)
        figure.clear()
        for index, (unit, items) in enumerate(by_unit.items(), 1):
            subplot = figure.add_subplot(len(by_unit), 1, index)
            for series in items:
                subplot.plot(axis.values, series.values,
                             marker="o" if output.num_steps == 1 else None,
                             label=f"{series.id_label} {series.field}")
            subplot.set_ylabel(unit or "値")
            subplot.set_xlabel(axis.label)
            subplot.grid(True)
            subplot.legend(loc="best", fontsize="small")
        figure.tight_layout()
        canvas.draw_idle()
        info.configure(text=f"{len(chosen)} 系列を表示中。単位ごとに別の軸を使用")

    ttk.Button(selector, text="グラフ表示", command=draw).pack(fill="x", pady=(8, 0))
    post_box.bind("<<ComboboxSelected>>", refresh_groups)
    group_box.bind("<<ComboboxSelected>>", lambda _event: refresh_ids())
    id_list.bind("<<ListboxSelect>>", refresh_fields)
    field_list.bind("<<ListboxSelect>>", refresh_preview)
    id_filter.trace_add("write", refresh_ids)
    field_filter.trace_add("write", refresh_fields)
    refresh_groups()
    root.mainloop()
