# -*- coding: utf-8 -*-
"""
Записник логики проектов (MAMONOV)

Простая программа для Windows: слева — список проектов,
справа — записи по выбранному проекту. Есть закреплённый раздел
«Общая логика» для всех программ сразу.

Всё хранится локально в файле JSON (в папке %APPDATA%\\MAMONOV).
Ничего в интернет не отправляется.
"""

import os
import json
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# Импорт модуля Google Drive
try:
    from google_drive_sync import sync_to_drive, sync_from_drive, auto_backup, HAS_GOOGLE
    GOOGLE_AVAILABLE = HAS_GOOGLE
except ImportError:
    GOOGLE_AVAILABLE = False

APP_NAME = "DevNotes — Записки разработчика"
COMMON_KEY = "__common__"  # служебный ключ для раздела «Общая логика»

# Тёмная тема (палитра в стиле VS Code)
THEME = {
    "bg":        "#1e1e1e",   # основной фон
    "bg2":       "#252526",   # панели
    "bg3":       "#2d2d30",   # поля ввода
    "fg":        "#e0e0e0",   # текст
    "fg_dim":    "#9a9a9a",   # приглушённый текст
    "accent":    "#0e639c",   # акцент (кнопки)
    "accent_hi": "#1177bb",   # акцент при наведении
    "select":    "#094771",   # выделение в списке
    "border":    "#3c3c3c",
    "caret":     "#e0e0e0",
}


def data_dir():
    """Папка для данных: %APPDATA%\\MAMONOV (Windows) или ~/.mamonov."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "MAMONOV")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        d = os.path.expanduser("~")
    return d


DATA_FILE = os.path.join(data_dir(), "project_notes.json")


# ---------------------------------------------------------------------------
# Работа с данными (загрузка / сохранение)
# ---------------------------------------------------------------------------

def empty_entry():
    """Пустая запись проекта."""
    return {
        "description": "",   # Описание
        "logic": "",         # Как работает логика
        "links": "",         # Ссылки / реквизиты
        "tasks": [],         # Список задач: [{"text": str, "done": bool}]
    }


def default_data():
    return {
        "common": empty_entry(),      # раздел «Общая логика»
        "order": [],                  # порядок проектов (список имён)
        "projects": {},               # имя -> запись
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # мягкая проверка структуры
        data.setdefault("common", empty_entry())
        data.setdefault("order", [])
        data.setdefault("projects", {})
        for name in list(data["projects"].keys()):
            e = empty_entry()
            e.update(data["projects"][name] or {})
            data["projects"][name] = e
        c = empty_entry()
        c.update(data["common"] or {})
        data["common"] = c
        return data
    except Exception:
        return default_data()


def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


# ---------------------------------------------------------------------------
# Главное окно
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.data = load_data()
        self.current = COMMON_KEY   # что сейчас показано справа
        self._loading = False       # чтобы автосохранение не срабатывало при загрузке
        self._syncing = False       # флаг синхронизации

        self.title(APP_NAME)
        self.geometry("980x620")
        self.minsize(760, 480)
        self.configure(bg=THEME["bg"])

        self._apply_theme()
        self._build_ui()
        self._refresh_project_list()
        self._select_in_list(COMMON_KEY)
        self._load_entry_into_form(COMMON_KEY)

        # Пробуем загрузить данные с Google Drive при старте
        if GOOGLE_AVAILABLE:
            self._try_load_from_drive()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- тёмная тема ----------
    def _apply_theme(self):
        t = THEME
        style = ttk.Style(self)
        try:
            style.theme_use("clam")   # единственная тема, где цвета хорошо настраиваются
        except Exception:
            pass

        style.configure(".", background=t["bg"], foreground=t["fg"],
                        fieldbackground=t["bg3"], bordercolor=t["border"],
                        lightcolor=t["bg2"], darkcolor=t["bg2"])
        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"])
        style.configure("TPanedwindow", background=t["bg"])

        style.configure("TButton", background=t["accent"], foreground="#ffffff",
                        bordercolor=t["accent"], focuscolor=t["accent"],
                        padding=4, relief="flat")
        style.map("TButton",
                  background=[("active", t["accent_hi"]), ("pressed", t["accent_hi"])],
                  foreground=[("disabled", t["fg_dim"])])

        style.configure("TEntry", fieldbackground=t["bg3"], foreground=t["fg"],
                        insertcolor=t["caret"], bordercolor=t["border"])
        style.map("TEntry", fieldbackground=[("focus", t["bg3"])])

        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
        style.map("TCheckbutton",
                  background=[("active", t["bg"])],
                  indicatorcolor=[("selected", t["accent_hi"]), ("!selected", t["bg3"])])

        # вкладки
        style.configure("TNotebook", background=t["bg"], bordercolor=t["border"])
        style.configure("TNotebook.Tab", background=t["bg2"], foreground=t["fg_dim"],
                        padding=(12, 5), bordercolor=t["border"])
        style.map("TNotebook.Tab",
                  background=[("selected", t["bg3"])],
                  foreground=[("selected", t["fg"])])

        # прокрутка
        style.configure("TScrollbar", background=t["bg2"], troughcolor=t["bg"],
                        bordercolor=t["bg"], arrowcolor=t["fg_dim"])
        style.map("TScrollbar", background=[("active", t["accent"])])

        style.configure("Status.TLabel", background=t["bg2"], foreground=t["fg_dim"])

    # ---------- построение интерфейса ----------
    def _build_ui(self):
        root = ttk.Frame(self, padding=6)
        root.pack(fill="both", expand=True)

        paned = ttk.PanedWindow(root, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # ----- левая часть: поиск + список проектов -----
        left = ttk.Frame(paned, padding=(0, 0, 6, 0))
        paned.add(left, weight=0)

        ttk.Label(left, text="Поиск по всем записям:").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_project_list())
        search_entry = ttk.Entry(left, textvariable=self.search_var)
        search_entry.pack(fill="x", pady=(0, 6))

        self.listbox = tk.Listbox(left, width=28, exportselection=False,
                                  activestyle="dotbox",
                                  bg=THEME["bg2"], fg=THEME["fg"],
                                  selectbackground=THEME["select"],
                                  selectforeground="#ffffff",
                                  highlightthickness=1,
                                  highlightbackground=THEME["border"],
                                  highlightcolor=THEME["accent"],
                                  borderwidth=0, relief="flat")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="+ Новый", command=self._add_project).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text="→ Переимен.", command=self._rename_project).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text="− Удалить", command=self._delete_project).pack(side="left", expand=True, fill="x")

        # Кнопки синхронизации с Google Drive
        if GOOGLE_AVAILABLE:
            sync_btns = ttk.Frame(left)
            sync_btns.pack(fill="x", pady=(6, 0))
            self.sync_btn = ttk.Button(sync_btns, text="☁ Синхронизировать", command=self._sync_to_drive)
            self.sync_btn.pack(fill="x")
            self.sync_btn.config(style="Sync.TButton")
            style = ttk.Style(self)
            style.configure("Sync.TButton", background="#2ea44f", foreground="#ffffff",
                           bordercolor="#2ea44f", focuscolor="#2ea44f", padding=4, relief="flat")
            style.map("Sync.TButton",
                     background=[("active", "#3fb950"), ("pressed", "#3fb950")])
            self.status.config(text="Google Drive подключён")

        # ----- правая часть: форма записи -----
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        self.title_label = ttk.Label(right, text="", font=("Segoe UI", 13, "bold"))
        self.title_label.pack(anchor="w", pady=(0, 4))
        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # вкладка «Описание»
        tab_desc = ttk.Frame(nb, padding=6)
        nb.add(tab_desc, text="Описание")
        self.txt_description = self._make_text(tab_desc)

        # вкладка «Логика»
        tab_logic = ttk.Frame(nb, padding=6)
        nb.add(tab_logic, text="Логика работы")
        self.txt_logic = self._make_text(tab_logic)

        # вкладка «Ссылки / реквизиты»
        tab_links = ttk.Frame(nb, padding=6)
        nb.add(tab_links, text="Ссылки и заметки")
        self.txt_links = self._make_text(tab_links)

        # вкладка «Задачи»
        tab_tasks = ttk.Frame(nb, padding=6)
        nb.add(tab_tasks, text="Задачи")
        self._build_tasks_tab(tab_tasks)

        # статус-строка
        self.status = ttk.Label(root, text="Готово", anchor="w",
                                style="Status.TLabel", padding=(6, 3))
        self.status.pack(fill="x", pady=(6, 0))

    def _make_text(self, parent):
        """Текстовое поле с прокруткой и автосохранением."""
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)
        yscroll = ttk.Scrollbar(wrap, orient="vertical")
        txt = tk.Text(wrap, wrap="word", undo=True, font=("Consolas", 10),
                      yscrollcommand=yscroll.set,
                      bg=THEME["bg3"], fg=THEME["fg"],
                      insertbackground=THEME["caret"],
                      selectbackground=THEME["select"],
                      selectforeground="#ffffff",
                      highlightthickness=1,
                      highlightbackground=THEME["border"],
                      highlightcolor=THEME["accent"],
                      borderwidth=0, relief="flat", padx=6, pady=4)
        yscroll.config(command=txt.yview)
        yscroll.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.bind("<<Modified>>", self._on_text_modified)
        return txt

    def _build_tasks_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", pady=(0, 6))
        self.task_entry = ttk.Entry(top)
        self.task_entry.pack(side="left", fill="x", expand=True)
        self.task_entry.bind("<Return>", lambda e: self._add_task())
        ttk.Button(top, text="+ Добавить задачу", command=self._add_task).pack(side="left", padx=(6, 0))

        # область со списком задач (с прокруткой)
        canvas_wrap = ttk.Frame(parent)
        canvas_wrap.pack(fill="both", expand=True)
        self.task_canvas = tk.Canvas(canvas_wrap, highlightthickness=0,
                                     bg=THEME["bg"])
        tscroll = ttk.Scrollbar(canvas_wrap, orient="vertical", command=self.task_canvas.yview)
        self.task_canvas.configure(yscrollcommand=tscroll.set)
        tscroll.pack(side="right", fill="y")
        self.task_canvas.pack(side="left", fill="both", expand=True)
        self.tasks_frame = ttk.Frame(self.task_canvas)
        self._tasks_window = self.task_canvas.create_window((0, 0), window=self.tasks_frame, anchor="nw")
        self.tasks_frame.bind("<Configure>",
                              lambda e: self.task_canvas.configure(scrollregion=self.task_canvas.bbox("all")))
        self.task_canvas.bind("<Configure>",
                              lambda e: self.task_canvas.itemconfig(self._tasks_window, width=e.width))

    # ---------- текущая запись ----------
    def _entry(self, key=None):
        key = key or self.current
        if key == COMMON_KEY:
            return self.data["common"]
        return self.data["projects"].get(key)

    # ---------- список проектов ----------
    def _filtered_projects(self):
        q = self.search_var.get().strip().lower()
        names = list(self.data["order"])
        if not q:
            return names
        out = []
        for name in names:
            e = self.data["projects"].get(name, {})
            hay = " ".join([
                name,
                e.get("description", ""),
                e.get("logic", ""),
                e.get("links", ""),
                " ".join(t.get("text", "") for t in e.get("tasks", [])),
            ]).lower()
            if q in hay:
                out.append(name)
        return out

    def _refresh_project_list(self):
        self.listbox.delete(0, "end")
        # первый пункт — всегда «Общая логика»
        self.listbox.insert("end", "⚙  Общая логика (для всех)")
        self._list_keys = [COMMON_KEY]
        for name in self._filtered_projects():
            self.listbox.insert("end", "   " + name)
            self._list_keys.append(name)
        # подсветить текущий
        self._select_in_list(self.current)

    def _select_in_list(self, key):
        if key in getattr(self, "_list_keys", []):
            idx = self._list_keys.index(key)
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(idx)
            self.listbox.see(idx)

    def _on_list_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        key = self._list_keys[sel[0]]
        if key == self.current:
            return
        self._save_form_into_entry()   # сохранить то, что было введено
        self.current = key
        self._load_entry_into_form(key)

    # ---------- кнопки проектов ----------
    def _add_project(self):
        name = simpledialog.askstring(APP_NAME, "Название нового проекта:", parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.data["projects"]:
            messagebox.showwarning(APP_NAME, "Проект с таким названием уже есть.", parent=self)
            return
        self.data["projects"][name] = empty_entry()
        self.data["order"].append(name)
        self._save_form_into_entry()
        self.current = name
        self.search_var.set("")
        self._refresh_project_list()
        self._load_entry_into_form(name)
        self._autosave()

    def _rename_project(self):
        if self.current == COMMON_KEY:
            messagebox.showinfo(APP_NAME, "Раздел «Общая логика» переименовать нельзя.", parent=self)
            return
        old = self.current
        name = simpledialog.askstring(APP_NAME, "Новое название:", initialvalue=old, parent=self)
        if not name:
            return
        name = name.strip()
        if not name or name == old:
            return
        if name in self.data["projects"]:
            messagebox.showwarning(APP_NAME, "Такое название уже есть.", parent=self)
            return
        self._save_form_into_entry()
        self.data["projects"][name] = self.data["projects"].pop(old)
        self.data["order"] = [name if n == old else n for n in self.data["order"]]
        self.current = name
        self._refresh_project_list()
        self._autosave()

    def _delete_project(self):
        if self.current == COMMON_KEY:
            messagebox.showinfo(APP_NAME, "Раздел «Общая логика» удалить нельзя.", parent=self)
            return
        name = self.current
        if not messagebox.askyesno(APP_NAME, "Удалить проект «%s»? Действие нельзя отменить." % name, parent=self):
            return
        self.data["projects"].pop(name, None)
        self.data["order"] = [n for n in self.data["order"] if n != name]
        self.current = COMMON_KEY
        self._refresh_project_list()
        self._load_entry_into_form(COMMON_KEY)
        self._autosave()

    # ---------- форма <-> данные ----------
    def _set_text(self, widget, value):
        widget.delete("1.0", "end")
        widget.insert("1.0", value or "")
        widget.edit_modified(False)

    def _get_text(self, widget):
        return widget.get("1.0", "end-1c")

    def _load_entry_into_form(self, key):
        self._loading = True
        e = self._entry(key)
        if e is None:
            e = empty_entry()
        if key == COMMON_KEY:
            self.title_label.config(text="⚙  Общая логика (для всех программ)")
        else:
            self.title_label.config(text=key)
        self._set_text(self.txt_description, e.get("description", ""))
        self._set_text(self.txt_logic, e.get("logic", ""))
        self._set_text(self.txt_links, e.get("links", ""))
        self._render_tasks()
        self._loading = False

    def _save_form_into_entry(self):
        """Забрать текст из полей в текущую запись (текстовые вкладки)."""
        e = self._entry()
        if e is None:
            return
        e["description"] = self._get_text(self.txt_description)
        e["logic"] = self._get_text(self.txt_logic)
        e["links"] = self._get_text(self.txt_links)
        # задачи сохраняются сразу при изменении, здесь трогать не нужно

    def _on_text_modified(self, event):
        w = event.widget
        if not w.edit_modified():
            return
        w.edit_modified(False)
        if self._loading:
            return
        self._save_form_into_entry()
        self._autosave()

    # ---------- задачи ----------
    def _render_tasks(self):
        for child in self.tasks_frame.winfo_children():
            child.destroy()
        e = self._entry()
        if e is None:
            return
        tasks = e.get("tasks", [])
        if not tasks:
            ttk.Label(self.tasks_frame, text="Пока нет задач. Добавь первую сверху.",
                      foreground="#888").pack(anchor="w", pady=4)
            return
        for i, task in enumerate(tasks):
            row = ttk.Frame(self.tasks_frame)
            row.pack(fill="x", pady=1)
            var = tk.BooleanVar(value=bool(task.get("done")))
            cb = ttk.Checkbutton(row, variable=var,
                                 command=lambda idx=i, v=var: self._toggle_task(idx, v))
            cb.pack(side="left")
            text = task.get("text", "")
            lbl = ttk.Label(row, text=text, wraplength=560, justify="left")
            if task.get("done"):
                lbl.config(foreground="#999")
            lbl.pack(side="left", fill="x", expand=True, padx=(4, 0))
            ttk.Button(row, text="✕", width=3,
                       command=lambda idx=i: self._delete_task(idx)).pack(side="right")

    def _add_task(self):
        text = self.task_entry.get().strip()
        if not text:
            return
        e = self._entry()
        if e is None:
            return
        e.setdefault("tasks", []).append({"text": text, "done": False})
        self.task_entry.delete(0, "end")
        self._render_tasks()
        self._autosave()

    def _toggle_task(self, idx, var):
        e = self._entry()
        if e is None:
            return
        try:
            e["tasks"][idx]["done"] = bool(var.get())
        except IndexError:
            return
        self._render_tasks()
        self._autosave()

    def _delete_task(self, idx):
        e = self._entry()
        if e is None:
            return
        try:
            e["tasks"].pop(idx)
        except IndexError:
            return
        self._render_tasks()
        self._autosave()

    # ---------- Google Drive синхронизация ----------
    def _try_load_from_drive(self):
        """Попытка загрузить данные с Google Drive при старте."""
        try:
            success, msg = sync_from_drive(DATA_FILE)
            if success:
                self.data = load_data()
                self.status.config(text="Загружено с Google Drive")
        except Exception:
            pass  # если ошибка — работаем с локальными данными

    def _sync_to_drive(self):
        """Ручная синхронизация с Google Drive."""
        if self._syncing:
            return
        self._syncing = True
        self.sync_btn.config(text="☁ Синхронизация...")
        self.status.config(text="Отправка на Google Drive...")

        def do_sync():
            try:
                success, msg = sync_to_drive(DATA_FILE)
                self.status.config(text=msg)
                if success:
                    messagebox.showinfo(APP_NAME, msg, parent=self)
            except Exception as ex:
                self.status.config(text=f"Ошибка: {str(ex)}")
            finally:
                self._syncing = False
                self.sync_btn.config(text="☁ Синхронизировать")

        # Запускаем в отдельном потоке, чтобы не блокировать UI
        import threading
        threading.Thread(target=do_sync, daemon=True).start()

    def _autosave(self):
        try:
            save_data(self.data)
            now = datetime.datetime.now().strftime("%H:%M:%S")
            self.status.config(text="Сохранено в " + now)

            # Автоматическая синхронизация с Google Drive
            if GOOGLE_AVAILABLE and not self._syncing:
                def auto_sync():
                    try:
                        sync_to_drive(DATA_FILE)
                    except Exception:
                        pass  # не показываем ошибки авто-синхронизации

                import threading
                threading.Thread(target=auto_sync, daemon=True).start()
        except Exception as ex:
            self.status.config(text="Ошибка сохранения: " + str(ex))

    def _on_close(self):
        self._save_form_into_entry()
        self._autosave()
        # Финальная синхронизация при закрытии
        if GOOGLE_AVAILABLE:
            try:
                sync_to_drive(DATA_FILE)
            except Exception:
                pass
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
