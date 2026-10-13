import json
import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

try:
    from pynput import keyboard
except ImportError:
    keyboard = None

APP_TITLE = 'The Escapists 1 | Crafting Companion'
DATA_FILE = Path(__file__).with_name('escapists_favorites.json')
BG = '#10141d'
PANEL = '#1a2230'
PANEL_2 = '#222d3e'
TEXT = '#f0f4fa'
MUTED = '#a4b2c5'
ACCENT = '#70c5ff'

# The Escapists 1 PC recipes; some are prison-specific.
RECIPES = [
    ('Tool Handle', 'Tools', ['Timber', 'File']),
    ('Flimsy Pickaxe', 'Tools', ['Tool Handle', 'Crowbar', 'Duct Tape']),
    ('Lightweight Pickaxe', 'Tools', ['Flimsy Pickaxe', 'Timber', 'Duct Tape']),
    ('Sturdy Pickaxe', 'Tools', ['Lightweight Pickaxe', 'Timber', 'Duct Tape']),
    ('Flimsy Shovel', 'Tools', ['Tool Handle', 'Sheet of Metal', 'Duct Tape']),
    ('Lightweight Shovel', 'Tools', ['Flimsy Shovel', 'Sheet of Metal', 'Duct Tape']),
    ('Sturdy Shovel', 'Tools', ['Lightweight Shovel', 'Sheet of Metal', 'Duct Tape']),
    ('Flimsy Cutters', 'Tools', ['File', 'File', 'Duct Tape']),
    ('Lightweight Cutters', 'Tools', ['Flimsy Cutters', 'File', 'Duct Tape']),
    ('Sturdy Cutters', 'Tools', ['Lightweight Cutters', 'File', 'Duct Tape']),
    ('Sock Mace', 'Weapons', ['Sock', 'Soap']),
    ('Super Sock Mace', 'Weapons', ['Sock', 'Battery']),
    ('Comb Blade', 'Weapons', ['Comb', 'Razor Blade']),
    ('Nunchucks', 'Weapons', ['Timber', 'Timber', 'Wire']),
    ('Whip', 'Weapons', ['Timber', 'Wire', 'Razor Blade']),
    ('Cup of Molten Chocolate', 'Weapons', ['Cup', 'Chocolate', 'Lighter']),
    ('Cushioned Inmate Outfit', 'Armor', ['Inmate Outfit', 'Pillow', 'Duct Tape']),
    ('Padded Inmate Outfit', 'Armor', ['Inmate Outfit', 'Book', 'Duct Tape']),
    ('Plated Inmate Outfit', 'Armor', ['Inmate Outfit', 'Sheet of Metal', 'Duct Tape']),
    ('Infirmary Overalls', 'Disguises', ['Any Outfit', 'Bleach']),
    ('Guard Outfit', 'Disguises', ['Infirmary Overalls', 'Ink']),
    ('Bed Dummy', 'Stealth', ['Pillow', 'Pillow', 'Bed Sheet']),
    ('Poster', 'Stealth', ['Magazine', 'Duct Tape']),
    ('Paper Mache', 'Stealth', ['Toilet Paper', 'Super Glue']),
    ('Fake Wall Block', 'Stealth', ['Paper Mache', 'Paper Mache', 'Ink']),
    ('Fake Vent Cover', 'Stealth', ['Paper Mache', 'Paper Mache']),
    ('Contraband Pouch', 'Stealth', ['Foil', 'Duct Tape']),
    ('Durable Contraband Pouch', 'Stealth', ['Foil', 'Foil', 'Duct Tape']),
    ('Fake Fence', 'Stealth', ['Wire', 'Wire', 'Wire']),
    ('Wad of Putty', 'Keys', ['Toothpaste', 'Talcum Powder']),
    ('Molten Plastic (Comb)', 'Keys', ['Comb', 'Lighter']),
    ('Molten Plastic (Toothbrush)', 'Keys', ['Toothbrush', 'Lighter']),
    ('Key Mold', 'Keys', ['Wad of Putty', 'Original Key']),
    ('Plastic Key', 'Keys', ['Key Mold', 'Molten Plastic']),
    ('Timber Brace', 'Escape', ['Timber', 'Timber']),
    ('Sheet Rope', 'Escape', ['Bed Sheet', 'Bed Sheet']),
    ('Grapple Head', 'Escape', ['Crowbar', 'Crowbar', 'Duct Tape']),
    ('Grappling Hook', 'Escape', ['Grapple Head', 'Rope']),
    ('Wooden Bat', 'Weapons', ['Timber', 'Timber', 'Duct Tape']),
    ('Knuckle Duster', 'Weapons', ['Razor Blade', 'Duct Tape']),
    ('Candle', 'Misc', ['Battery', 'Wire']),
    ('Unvarnished Chair', 'Misc', ['Timber', 'Timber', 'Timber']),
    ('Sail', 'Escape', ['Timber', 'Bed Sheet']),
    ('Raft Base', 'Escape', ['Balsa Wood', 'Balsa Wood', 'Rope']),
    ('Makeshift Raft', 'Escape', ['Raft Base', 'Sail', 'Rope']),
]
ESSENTIALS = ['Bed Dummy', 'Flimsy Cutters', 'Lightweight Cutters', 'Sturdy Cutters',
              'Flimsy Shovel', 'Sturdy Shovel', 'Flimsy Pickaxe', 'Sturdy Pickaxe',
              'Tool Handle', 'Contraband Pouch', 'Durable Contraband Pouch',
              'Wad of Putty', 'Molten Plastic (Comb)', 'Key Mold', 'Plastic Key',
              'Guard Outfit', 'Infirmary Overalls', 'Poster', 'Timber Brace',
              'Paper Mache', 'Fake Wall Block', 'Fake Vent Cover',
              'Cup of Molten Chocolate', 'Plated Inmate Outfit']
ESSENTIAL_SET = set(ESSENTIALS)
CATEGORIES = ['Run Essentials', 'All Recipes', 'Favorites', 'Tools', 'Stealth', 'Keys',
              'Escape', 'Disguises', 'Armor', 'Weapons', 'Misc']
RECIPE_BY_NAME = {name: (category, ingredients) for name, category, ingredients in RECIPES}

class CraftingCompanion:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry('1030x670')
        self.root.minsize(760, 500)
        self.root.configure(bg=BG)
        self.root.attributes('-topmost', True)
        self.visible = True
        self.category = 'Run Essentials'
        self.selected = None
        self.search = tk.StringVar()
        self.favorites = self.load_favorites()
        self.hotkey_events = queue.SimpleQueue()
        self.listener = None
        self.build_ui()
        self.refresh()
        self.root.bind('<Escape>', lambda event: self.hide())
        self.root.bind('<Control-f>', lambda event: self.focus_search())
        self.root.protocol('WM_DELETE_WINDOW', self.shutdown)
        if keyboard is not None:
            self.listener = keyboard.Listener(on_press=self.on_global_key)
            self.listener.start()
        self.root.after(60, self.poll_hotkeys)

    def load_favorites(self):
        try:
            data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
            return ({name for name in data if name in RECIPE_BY_NAME} | ESSENTIAL_SET) if isinstance(data, list) else set(ESSENTIAL_SET)
        except (OSError, ValueError, TypeError):
            return set(ESSENTIAL_SET)

    def save_favorites(self):
        try:
            DATA_FILE.write_text(json.dumps(sorted(self.favorites), indent=2), encoding='utf-8')
        except OSError as error:
            self.set_status(f'Could not save favorites: {error}')

    def label(self, parent, text, size=11, color=TEXT, bold=False, bg=None, **kwargs):
        return tk.Label(parent, text=text, font=('Segoe UI', size, 'bold' if bold else 'normal'),
                        fg=color, bg=bg or BG, **kwargs)

    def button(self, parent, text, command, bg=PANEL_2, fg=TEXT):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground='#33506c', activeforeground='white',
                         relief='flat', cursor='hand2', padx=13, pady=9,
                         font=('Segoe UI', 10, 'bold'))

    def build_ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=22, pady=(18, 12))
        self.label(header, 'CRAFTING COMPANION', 20, bold=True).pack(anchor='w')
        self.label(header, 'THE ESCAPISTS 1  •  Run Essentials preselected  •  Search all recipes and materials',
                   10, MUTED).pack(anchor='w', pady=(3, 0))

        content = tk.Frame(self.root, bg=BG)
        content.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        content.grid_columnconfigure(0, minsize=145)
        content.grid_columnconfigure(1, weight=2, minsize=240)
        content.grid_columnconfigure(2, weight=3, minsize=290)
        content.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(content, bg=PANEL)
        sidebar.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        self.label(sidebar, 'CATEGORIES', 10, MUTED, True, PANEL).pack(anchor='w', padx=13, pady=(18, 10))
        self.category_buttons = {}
        for category in CATEGORIES:
            btn = self.button(sidebar, category, lambda c=category: self.set_category(c), bg=PANEL)
            btn.pack(fill='x', padx=8, pady=2)
            self.category_buttons[category] = btn

        center = tk.Frame(content, bg=PANEL)
        center.grid(row=0, column=1, sticky='nsew', padx=(0, 10))
        self.recipe_heading = self.label(center, 'RECIPES', 11, bold=True, bg=PANEL)
        self.recipe_heading.pack(anchor='w', padx=14, pady=(16, 8))
        search_frame = tk.Frame(center, bg=PANEL)
        search_frame.pack(fill='x', padx=12, pady=(0, 10))
        self.search_entry = tk.Entry(search_frame, textvariable=self.search,
                                     bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
                                     relief='flat', font=('Segoe UI', 11))
        self.search_entry.pack(fill='x', ipady=9)
        self.search.trace_add('write', lambda *_: self.refresh())
        list_frame = tk.Frame(center, bg=PANEL)
        list_frame.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        scroll = tk.Scrollbar(list_frame)
        scroll.pack(side='right', fill='y')
        self.recipe_list = tk.Listbox(list_frame, bg=PANEL_2, fg=TEXT,
                                      selectbackground='#32618a', selectforeground='white',
                                      font=('Segoe UI', 10), relief='flat', borderwidth=0,
                                      highlightthickness=0, activestyle='none',
                                      yscrollcommand=scroll.set)
        self.recipe_list.pack(side='left', fill='both', expand=True)
        scroll.config(command=self.recipe_list.yview)
        self.recipe_list.bind('<<ListboxSelect>>', self.select_recipe)
        self.visible_names = []

        details = tk.Frame(content, bg=PANEL)
        details.grid(row=0, column=2, sticky='nsew')
        self.label(details, 'RECIPE DETAILS', 11, bold=True, bg=PANEL).pack(anchor='w', padx=18, pady=(18, 12))
        self.name_label = self.label(details, 'Choose a recipe', 17, bold=True, bg=PANEL,
                                     wraplength=330, justify='left')
        self.name_label.pack(anchor='w', padx=18, pady=(0, 6))
        self.category_label = self.label(details, '', 10, ACCENT, bg=PANEL)
        self.category_label.pack(anchor='w', padx=18)
        self.label(details, 'INGREDIENTS', 10, MUTED, True, PANEL).pack(anchor='w', padx=18, pady=(22, 8))
        self.ingredients_frame = tk.Frame(details, bg=PANEL)
        self.ingredients_frame.pack(fill='x', padx=18)
        self.label(details, 'FULL MATERIALS (INCLUDING SUB-RECIPES)', 9, MUTED, True, PANEL).pack(
            anchor='w', padx=18, pady=(22, 8))
        self.materials_label = self.label(details, '', 10, TEXT, bg=PANEL, justify='left',
                                          anchor='nw', wraplength=330)
        self.materials_label.pack(fill='x', padx=18)
        actions = tk.Frame(details, bg=PANEL)
        actions.pack(side='bottom', fill='x', padx=18, pady=18)
        self.favorite_button = self.button(actions, '☆ Favorite', self.toggle_favorite, bg='#284c6c')
        self.favorite_button.pack(side='left', padx=(0, 8))
        self.button(actions, 'Copy materials', self.copy_materials).pack(side='left')

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill='x', padx=22, pady=(0, 14))
        self.status_label = self.label(footer, 'F9: show/hide  •  Ctrl+F: search  •  Esc: hide', 9, MUTED)
        self.status_label.pack(side='left')
        self.label(footer, f'{len(RECIPES)} recipes available', 9, MUTED).pack(side='right')

    def set_status(self, message):
        self.status_label.config(text=message)

    def set_category(self, category):
        self.category = category
        for name, button in self.category_buttons.items():
            button.config(bg='#285477' if name == category else PANEL,
                          fg='white' if name == category else MUTED)
        self.refresh()

    def refresh(self):
        if not hasattr(self, 'recipe_list'):
            return
        previous = self.selected
        query = self.search.get().strip().casefold()
        self.visible_names = [name for name, category, ingredients in RECIPES
                              if (self.category in ('All Recipes', 'Favorites')
                                  or (self.category == 'Run Essentials' and name in ESSENTIAL_SET)
                                  or category == self.category)
                              and (self.category != 'Favorites' or name in self.favorites)
                              and (query in name.casefold() or query in category.casefold()
                                   or any(query in ingredient.casefold() for ingredient in ingredients))]
        self.visible_names.sort(key=lambda name: (ESSENTIALS.index(name) if self.category == 'Run Essentials' and name in ESSENTIAL_SET else 999, name.casefold()))
        self.recipe_heading.config(text=f'{self.category.upper()}  ({len(self.visible_names)})')
        self.recipe_list.delete(0, tk.END)
        for name in self.visible_names:
            self.recipe_list.insert(tk.END, ('★  ' if name in self.favorites else '   ') + name)
        if previous in self.visible_names:
            index = self.visible_names.index(previous)
            self.recipe_list.selection_set(index)
            self.recipe_list.see(index)
            self.show_details(previous)
        elif self.visible_names:
            self.recipe_list.selection_set(0)
            self.show_details(self.visible_names[0])
        else:
            self.show_details(None)

    def select_recipe(self, event=None):
        indices = self.recipe_list.curselection()
        if indices and indices[0] < len(self.visible_names):
            self.show_details(self.visible_names[indices[0]])

    def expand_materials(self, name, seen=None):
        seen = set() if seen is None else seen
        if name in seen:
            return [name]
        if name not in RECIPE_BY_NAME:
            return [name]
        seen = seen | {name}
        result = []
        for ingredient in RECIPE_BY_NAME[name][1]:
            if ingredient in RECIPE_BY_NAME:
                result.extend(self.expand_materials(ingredient, seen))
            else:
                result.append(ingredient)
        return result

    def show_details(self, name):
        self.selected = name
        for widget in self.ingredients_frame.winfo_children():
            widget.destroy()
        if name is None:
            self.name_label.config(text='No matching recipes')
            self.category_label.config(text='Try a different search or category')
            self.materials_label.config(text='')
            self.favorite_button.config(text='☆ Favorite', state='disabled')
            return
        category, ingredients = RECIPE_BY_NAME[name]
        self.name_label.config(text=name)
        self.category_label.config(text=category)
        self.favorite_button.config(text='★ Favorited' if name in self.favorites else '☆ Favorite', state='normal')
        for ingredient in ingredients:
            row = tk.Frame(self.ingredients_frame, bg=PANEL_2)
            row.pack(fill='x', pady=3)
            suffix = '  ↳ craftable' if ingredient in RECIPE_BY_NAME else ''
            self.label(row, '•  ' + ingredient + suffix, 10, TEXT, bg=PANEL_2,
                       anchor='w', wraplength=300, justify='left').pack(fill='x', padx=10, pady=7)
        from collections import Counter
        counts = Counter(self.expand_materials(name))
        self.materials_label.config(text='\n'.join(f'{count} × {item}' for item, count in sorted(counts.items())))

    def toggle_favorite(self):
        if self.selected is None:
            return
        name = self.selected
        if name in self.favorites:
            self.favorites.remove(name)
        else:
            self.favorites.add(name)
        self.save_favorites()
        self.refresh()

    def copy_materials(self):
        if self.selected is None:
            return
        text = f'{self.selected}\n{self.materials_label.cget("text")}'
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status('Copied the full material list to your clipboard.')

    def focus_search(self):
        self.show()
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    def hide(self):
        self.root.withdraw()
        self.visible = False

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.visible = True
        self.search_entry.focus_set()

    def toggle_window(self):
        self.hide() if self.visible else self.show()

    def on_global_key(self, key):
        if key == keyboard.Key.f9:
            self.hotkey_events.put('toggle')

    def poll_hotkeys(self):
        while not self.hotkey_events.empty():
            if self.hotkey_events.get_nowait() == 'toggle':
                self.toggle_window()
        self.root.after(60, self.poll_hotkeys)

    def shutdown(self):
        if self.listener is not None:
            self.listener.stop()
        self.root.destroy()

    def run(self):
        self.set_category('Run Essentials')
        if keyboard is None:
            self.set_status('Install pynput for F9: py -3.14 -m pip install pynput')
        self.root.mainloop()

if __name__ == '__main__':
    CraftingCompanion().run()
