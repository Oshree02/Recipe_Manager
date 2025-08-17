import tkinter as tk
from tkinter import ttk, messagebox
from pymongo import MongoClient
from bson.objectid import ObjectId

# ===== MongoDB Connection =====
# Change this to your Atlas URI if needed
client = MongoClient("mongodb://localhost:27017/")
db = client["recipe_manager"]
collection = db["recipes"]

# ===== Helpers =====
def parse_list_from_text(text: str):
    """
    Parse a multi-line or comma-separated string into a clean list.
    - Splits by newlines first; if single line, splits by commas.
    - Trims empty lines/spaces.
    """
    if "\n" in text.strip():
        items = [line.strip() for line in text.splitlines()]
    else:
        items = [x.strip() for x in text.split(",")]
    return [x for x in items if x]

def join_list_for_text(items):
    """Join a list into multiline text for display/editing."""
    return "\n".join(items or [])

def ensure_not_empty(*pairs):
    """
    Validate required fields: pairs like ("Title", title_value)
    Returns (ok: bool, message: str)
    """
    for label, value in pairs:
        if not value or not str(value).strip():
            return False, f"{label} is required!"
    return True, ""

# ===== GUI =====
root = tk.Tk()
root.title("Recipe Manager 🍳 (MongoDB + Tkinter)")
root.geometry("980x640")
root.minsize(900, 600)

# ---- Layout weights ----
root.columnconfigure(0, weight=1)
root.rowconfigure(2, weight=1)

# ---- Styles (simple, clean) ----
style = ttk.Style()
try:
    style.theme_use("clam")
except:
    pass

# ===== Top: Search + Tag Filter =====
toolbar = ttk.Frame(root, padding=(10, 8))
toolbar.grid(row=0, column=0, sticky="ew")
for i in range(6):
    toolbar.columnconfigure(i, weight=1 if i in (1, 3, 5) else 0)

ttk.Label(toolbar, text="Search (Title/Tag):").grid(row=0, column=0, sticky="w", padx=(0,6))
search_entry = ttk.Entry(toolbar)
search_entry.grid(row=0, column=1, sticky="ew")

ttk.Label(toolbar, text="Filter Tag:").grid(row=0, column=2, sticky="e", padx=(12,6))
tag_filter = ttk.Combobox(toolbar, values=[], state="readonly")
tag_filter.grid(row=0, column=3, sticky="ew")

def refresh_tag_filter():
    """Rebuild tag dropdown from distinct tags in DB."""
    tags = sorted({t for doc in collection.find({}, {"tags": 1}) for t in (doc.get("tags") or [])})
    tag_filter["values"] = ["(All)"] + tags if tags else ["(All)"]
    tag_filter.set("(All)")

def do_search():
    fetch_recipes(search_entry.get().strip(), tag_filter.get().strip())

ttk.Button(toolbar, text="Search", command=do_search).grid(row=0, column=4, padx=(12,0))
ttk.Button(toolbar, text="Clear", command=lambda: [search_entry.delete(0, tk.END), tag_filter.set("(All)"), fetch_recipes()]).grid(row=0, column=5, padx=(8,0))

# ===== Middle: Form =====
form = ttk.LabelFrame(root, text="Recipe Details", padding=(12, 10))
form.grid(row=1, column=0, sticky="ew", padx=10, pady=8)
for i in range(6):
    form.columnconfigure(i, weight=1 if i in (1, 3, 5) else 0)

# Title
ttk.Label(form, text="Title *").grid(row=0, column=0, sticky="w")
title_entry = ttk.Entry(form)
title_entry.grid(row=0, column=1, columnspan=5, sticky="ew", padx=(6,0), pady=(0,6))

# Ingredients (multiline)
ttk.Label(form, text="Ingredients *").grid(row=1, column=0, sticky="nw", pady=(4,0))
ingredients_text = tk.Text(form, height=6, wrap="word")
ingredients_text.grid(row=1, column=1, columnspan=5, sticky="ew", padx=(6,0), pady=(4,6))

# Instructions (multiline)
ttk.Label(form, text="Instructions *").grid(row=2, column=0, sticky="nw")
instructions_text = tk.Text(form, height=6, wrap="word")
instructions_text.grid(row=2, column=1, columnspan=5, sticky="ew", padx=(6,0), pady=(4,6))

# Tags
ttk.Label(form, text="Tags (comma or lines)").grid(row=3, column=0, sticky="nw")
tags_text = tk.Text(form, height=3, wrap="word")
tags_text.grid(row=3, column=1, columnspan=5, sticky="ew", padx=(6,0), pady=(4,6))

# Buttons
btns = ttk.Frame(form)
btns.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(4,0))
for i in range(6):
    btns.columnconfigure(i, weight=1)

def clear_form():
    title_entry.delete(0, tk.END)
    ingredients_text.delete("1.0", tk.END)
    instructions_text.delete("1.0", tk.END)
    tags_text.delete("1.0", tk.END)
    title_entry.focus_set()

def add_recipe():
    title = title_entry.get().strip()
    ingredients = parse_list_from_text(ingredients_text.get("1.0", tk.END))
    instructions = instructions_text.get("1.0", tk.END).strip()
    tags = parse_list_from_text(tags_text.get("1.0", tk.END))

    ok, msg = ensure_not_empty(("Title", title), ("Ingredients", ingredients), ("Instructions", instructions))
    if not ok:
        messagebox.showerror("Input Error", msg)
        return

    doc = {"title": title, "ingredients": ingredients, "instructions": instructions, "tags": tags}
    collection.insert_one(doc)
    fetch_recipes()
    refresh_tag_filter()
    clear_form()
    messagebox.showinfo("Success", "Recipe added!")

def get_selected_id():
    sel = tree.selection()
    if not sel:
        return None
    values = tree.item(sel[0])["values"]
    return values[0] if values else None

def load_selected_into_form(_event=None):
    sel_id = get_selected_id()
    if not sel_id:
        return
    doc = collection.find_one({"_id": ObjectId(sel_id)})
    if not doc:
        return
    clear_form()
    title_entry.insert(0, doc.get("title", ""))
    ingredients_text.insert("1.0", join_list_for_text(doc.get("ingredients", [])))
    instructions_text.insert("1.0", doc.get("instructions", ""))
    tags_text.insert("1.0", join_list_for_text(doc.get("tags", [])))

def update_recipe():
    sel_id = get_selected_id()
    if not sel_id:
        messagebox.showerror("Selection Error", "Select a recipe to update.")
        return

    title = title_entry.get().strip()
    ingredients = parse_list_from_text(ingredients_text.get("1.0", tk.END))
    instructions = instructions_text.get("1.0", tk.END).strip()
    tags = parse_list_from_text(tags_text.get("1.0", tk.END))

    ok, msg = ensure_not_empty(("Title", title), ("Ingredients", ingredients), ("Instructions", instructions))
    if not ok:
        messagebox.showerror("Input Error", msg)
        return

    try:
        oid = ObjectId(sel_id)
    except:
        messagebox.showerror("Error", "Invalid record ID.")
        return

    collection.update_one(
        {"_id": oid},
        {"$set": {"title": title, "ingredients": ingredients, "instructions": instructions, "tags": tags}}
    )
    fetch_recipes()
    refresh_tag_filter()
    clear_form()
    messagebox.showinfo("Success", "Recipe updated!")

def delete_recipe():
    sel_id = get_selected_id()
    if not sel_id:
        messagebox.showerror("Selection Error", "Select a recipe to delete.")
        return
    if not messagebox.askyesno("Confirm", "Delete this recipe? This action cannot be undone."):
        return
    try:
        oid = ObjectId(sel_id)
    except:
        messagebox.showerror("Error", "Invalid record ID.")
        return
    collection.delete_one({"_id": oid})
    fetch_recipes()
    refresh_tag_filter()
    clear_form()
    messagebox.showinfo("Deleted", "Recipe deleted.")

ttk.Button(btns, text="Add", command=add_recipe).grid(row=0, column=0, padx=4, sticky="ew")
ttk.Button(btns, text="Update", command=update_recipe).grid(row=0, column=1, padx=4, sticky="ew")
ttk.Button(btns, text="Delete", command=delete_recipe).grid(row=0, column=2, padx=4, sticky="ew")
ttk.Button(btns, text="Clear", command=clear_form).grid(row=0, column=3, padx=4, sticky="ew")

# ===== Bottom: Table =====
table_frame = ttk.LabelFrame(root, text="Recipes", padding=(10, 8))
table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0,10))
table_frame.columnconfigure(0, weight=1)
table_frame.rowconfigure(0, weight=1)

columns = ("ID", "Title", "Tags", "Ingredients Count")
tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
for col in columns:
    anchor = "w" if col != "Ingredients Count" else "center"
    width = 120
    if col == "Title":
        width = 280
    if col == "Tags":
        width = 220
    tree.heading(col, text=col, anchor="w")
    tree.column(col, width=width, anchor=anchor)

tree.grid(row=0, column=0, sticky="nsew")
tree.bind("<ButtonRelease-1>", load_selected_into_form)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
tree.configure(yscrollcommand=scrollbar.set)

def fetch_recipes(search_term: str = "", tag_filter_value: str = "(All)"):
    # Clear current rows
    for row in tree.get_children():
        tree.delete(row)

    # Build query
    query = {}
    if search_term:
        query["$or"] = [
            {"title": {"$regex": search_term, "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": search_term, "$options": "i"}}},
        ]
    if tag_filter_value and tag_filter_value != "(All)":
        query.setdefault("$and", [])
        query["$and"].append({"tags": tag_filter_value})

    # Insert
    for doc in collection.find(query).sort("title", 1):
        _id = str(doc["_id"])
        title = doc.get("title", "")
        tags = ", ".join(doc.get("tags") or [])
        count_ing = len(doc.get("ingredients") or [])
        tree.insert("", tk.END, values=(_id, title, tags, count_ing))

def on_close():
    client.close()
    root.destroy()

# Initial data load
refresh_tag_filter()
fetch_recipes()

# Close hook
root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()
