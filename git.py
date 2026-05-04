# FULL UPDATED SMART STORE CODE - WITH SEARCH & PRICE SORTING
# Features: Auto Low Stock Alert | Working Restock Button | Search Product | Price Sort (Low/High)

from tkinter import *
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import re
import tempfile
import os
import sqlite3

# Try to import win32print for Windows printing support
try:
    import win32print
    PRINT_SUPPORT = True
except ImportError:
    PRINT_SUPPORT = False

# ========== DATABASE SETUP ==========
DB_NAME = "store1.db"

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            discount REAL DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            discount REAL DEFAULT 0,
            total REAL NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_date TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            amount REAL NOT NULL,
            reason TEXT NOT NULL
        )
    ''')
    
    try:
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'transaction_id' not in columns:
            cursor.execute('''
                CREATE TABLE transactions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    discount REAL DEFAULT 0,
                    total REAL NOT NULL
                )
            ''')
            try:
                cursor.execute('''
                    INSERT INTO transactions_new (id, date, time, product_name, category, quantity, price, discount, total)
                    SELECT id, date, time, product_name, category, quantity, price, discount, total 
                    FROM transactions
                ''')
            except:
                pass
            cursor.execute("DROP TABLE IF EXISTS transactions")
            cursor.execute("ALTER TABLE transactions_new RENAME TO transactions")
    except:
        pass
    
    conn.commit()
    conn.close()

init_database()

# ========== CURRENCY ==========
CURRENCY_SYMBOL = "Rs"

def format_currency(amount):
    return f"{CURRENCY_SYMBOL} {amount:,.2f}"

# ========== CATEGORY DETECTION ==========
def detect_category(product_name):
    product_name_lower = product_name.lower()
    
    category_keywords = {
        "Electronics": ["mobile", "phone", "laptop", "computer", "tv", "headphone", "charger", "camera", "iphone", "samsung", "redmi", "realme", "tecno"],
        "Groceries": ["rice", "wheat", "atta", "sugar", "salt", "oil", "daal", "masala", "tea"],
        "Vegetables": ["tomato", "onion", "potato", "carrot", "cabbage", "ladyfinger"],
        "Fruits": ["apple", "banana", "orange", "mango", "grape", "watermelon"],
        "Dairy": ["milk", "curd", "cheese", "paneer", "butter", "ghee"],
        "Beverages": ["coke", "pepsi", "juice", "water", "cold drink"],
        "Meat": ["chicken", "mutton", "fish", "egg", "beef"],
        "Clothing": ["shirt", "pant", "jeans", "jacket", "coat", "sweater", "t-shirt", "saree", "kurta"],
        "Footwear": ["shoe", "sandal", "slipper", "boot"],
        "General": []
    }
    
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in product_name_lower:
                return category
    return "General"

# ========== PRINT RECEIPT ==========
def print_receipt(bill_text):
    try:
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write(bill_text)
        temp_file.close()
        
        if PRINT_SUPPORT:
            try:
                printer_name = win32print.GetDefaultPrinter()
                hprinter = win32print.OpenPrinter(printer_name)
                win32print.StartDocPrinter(hprinter, 1, ("Receipt", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                with open(temp_file.name, 'r', encoding='utf-8') as f:
                    win32print.WritePrinter(hprinter, f.read().encode('utf-8'))
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
                win32print.ClosePrinter(hprinter)
            except:
                os.system(f'notepad.exe "{temp_file.name}"')
        else:
            os.system(f'notepad.exe "{temp_file.name}"')
    except:
        pass

# ========== CLASSES ==========
class Product:
    def __init__(self, name, category, price, stock, discount=0):
        self.name = name
        self.category = category
        self.price = price
        self.stock = stock
        self.discount = discount

class ReturnItem:
    def __init__(self, product_name, quantity, amount, reason, return_date):
        self.product_name = product_name
        self.quantity = quantity
        self.amount = amount
        self.reason = reason
        self.return_date = return_date

# ========== STORE CLASS ==========
class SmartStore:
    def __init__(self):
        self.products = {}
        self.categories = set()
        self.total_sales = 0
        self.total_returns = 0
        self.transactions = []
        self.returns = []
        self.last_low_stock_date = ""
        self.low_stock_shown = []
        self.next_transaction_id = 1
        self.search_query = ""  # For product search
        self.current_sort = "Default"  # For price sorting
        self.load_from_database()

    def save_product_to_db(self, product):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO products (name, category, price, stock, discount) VALUES (?, ?, ?, ?, ?)',
                       (product.name, product.category, product.price, product.stock, product.discount))
        conn.commit()
        conn.close()

    def delete_product_from_db(self, product_name):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE name = ?', (product_name,))
        conn.commit()
        conn.close()

    def save_transaction_to_db(self, transaction):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO transactions (transaction_id, date, time, product_name, category, quantity, price, discount, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (transaction['id'], transaction['date'], transaction['time'],
                        transaction['name'], transaction['category'], transaction['qty'],
                        transaction['price'], transaction['discount'], transaction['total']))
        conn.commit()
        conn.close()

    def save_return_to_db(self, return_item):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO returns (return_date, product_name, quantity, amount, reason) VALUES (?, ?, ?, ?, ?)',
                       (return_item.return_date, return_item.product_name,
                        return_item.quantity, return_item.amount, return_item.reason))
        conn.commit()
        conn.close()

    def load_from_database(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT name, category, price, stock, discount FROM products')
            for row in cursor.fetchall():
                name, category, price, stock, discount = row
                self.products[name] = Product(name, category, price, stock, discount)
                self.categories.add(category)
        except:
            pass
        
        try:
            cursor.execute('SELECT transaction_id, date, time, product_name, category, quantity, price, discount, total FROM transactions')
            for row in cursor.fetchall():
                trans_id, date, time, name, category, qty, price, discount, total = row
                self.transactions.append({
                    "id": trans_id, "date": date, "time": time, "name": name,
                    "category": category, "qty": qty, "price": price,
                    "discount": discount, "total": total
                })
                self.total_sales += total
                if trans_id.startswith("#"):
                    try:
                        num = int(trans_id[1:])
                        if num >= self.next_transaction_id:
                            self.next_transaction_id = num + 1
                    except:
                        pass
        except:
            pass
        
        try:
            cursor.execute('SELECT return_date, product_name, quantity, amount, reason FROM returns')
            for row in cursor.fetchall():
                return_date, product_name, quantity, amount, reason = row
                self.returns.append(ReturnItem(product_name, quantity, amount, reason, return_date))
                self.total_returns += amount
        except:
            pass
        
        conn.close()

    def get_next_transaction_id(self):
        tid = f"#{self.next_transaction_id:04d}"
        self.next_transaction_id += 1
        return tid

    def clear_boxes(self):
        txt_name.delete(0, END)
        txt_category.delete(0, END)
        txt_price.delete(0, END)
        txt_stock.delete(0, END)
        txt_discount.delete(0, END)
        category_filter_var.set("All Categories")
        lbl_discounted_price.config(text=f"💰 Final Price: {format_currency(0)}")

    def auto_detect_category(self, event=None):
        name = txt_name.get().strip()
        if name:
            detected = detect_category(name)
            txt_category.delete(0, END)
            txt_category.insert(0, detected)

    def calculate_discounted_price(self, event=None):
        try:
            price = float(txt_price.get().strip()) if txt_price.get().strip() else 0
            discount = float(txt_discount.get().strip()) if txt_discount.get().strip() else 0
            if price > 0:
                final = price - (price * discount / 100)
                if discount > 0:
                    lbl_discounted_price.config(text=f"💰 After {discount:.0f}% OFF: {format_currency(final)}", fg="#22c55e")
                else:
                    lbl_discounted_price.config(text=f"💰 Final Price: {format_currency(price)}", fg="#38bdf8")
            else:
                lbl_discounted_price.config(text=f"💰 Final Price: {format_currency(0)}", fg="#94a3b8")
        except:
            lbl_discounted_price.config(text="💰 Invalid", fg="#ef4444")

    def add_product(self):
        try:
            name = txt_name.get().strip()
            category = txt_category.get().strip().title()
            if not category and name:
                category = detect_category(name).title()
                txt_category.delete(0, END)
                txt_category.insert(0, category)
            
            price = float(txt_price.get().strip()) if txt_price.get().strip() else 0
            stock = int(txt_stock.get().strip()) if txt_stock.get().strip() else 0
            discount = float(txt_discount.get().strip()) if txt_discount.get().strip() else 0
            
            if not name or price <= 0 or stock < 0:
                messagebox.showerror("Error", "Please fill all fields correctly")
                return
            
            if name in self.products:
                messagebox.showerror("Error", f"Product '{name}' already exists!")
                return
            
            self.products[name] = Product(name, category, price, stock, discount)
            self.save_product_to_db(self.products[name])
            self.categories.add(category)
            self.update_category_filter()
            self.view_products_sorted()
            self.clear_boxes()
            messagebox.showinfo("Success", f"✓ Product Added!\n{name}\n{category}\n{format_currency(price)}\nStock: {stock}")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    # ========== NEW: SEARCH & SORTING METHODS ==========
    
    def on_search_change(self, event=None):
        """Called when user types in search box"""
        search_entry = search_box
        if search_entry:
            self.search_query = search_entry.get().strip().lower()
            self.view_products_sorted()
            # Update status
            self.update_status_with_count()

    def clear_search(self):
        """Clear search box and refresh"""
        search_box.delete(0, END)
        self.search_query = ""
        sort_var.set("Default")
        self.current_sort = "Default"
        self.view_products_sorted()
        self.update_status_with_count()

    def on_sort_change(self, event=None):
        """Called when sort option changes"""
        self.current_sort = sort_var.get()
        self.view_products_sorted()
        self.update_status_with_count()

    def get_filtered_and_sorted_products(self):
        """Get products filtered by category, search, then sorted by price"""
        selected_cat = category_filter_var.get()
        
        # Filter products
        filtered = []
        for p in self.products.values():
            # Category filter
            if selected_cat != "All Categories" and p.category != selected_cat:
                continue
            
            # Search filter (partial match on product name)
            if self.search_query:
                if self.search_query not in p.name.lower():
                    continue
            
            filtered.append(p)
        
        # Sort by final price (after discount)
        if self.current_sort == "Price: Low to High":
            filtered.sort(key=lambda x: x.price - (x.price * x.discount / 100))
        elif self.current_sort == "Price: High to Low":
            filtered.sort(key=lambda x: x.price - (x.price * x.discount / 100), reverse=True)
        # Default: keep as is (original order from dict)
        
        return filtered

    def view_products_sorted(self):
        """Display products with search and sorting applied"""
        # Clear table
        for item in table.get_children():
            table.delete(item)
        
        # Get filtered and sorted products
        products_to_show = self.get_filtered_and_sorted_products()
        
        # Show products in table
        for p in products_to_show:
            final_price = p.price - (p.price * p.discount / 100)
            item_id = table.insert("", END, values=(
                p.name, p.category, format_currency(p.price),
                format_currency(final_price), p.stock if p.stock > 0 else "OUT",
                f"{p.discount:.0f}%" if p.discount > 0 else "—"
            ))
            
            if p.stock == 0:
                table.tag_configure('out', background='#fee2e2')
                table.item(item_id, tags=('out',))
            elif p.stock <= 5:
                table.tag_configure('low', background='#fed7aa')
                table.item(item_id, tags=('low',))
        
        # Update status bar with count
        self.update_status_with_count()

    def update_status_with_count(self):
        """Update status bar with current filter/sort info"""
        total_products = len(self.products)
        filtered_count = len(self.get_filtered_and_sorted_products())
        
        status_parts = []
        if self.search_query:
            status_parts.append(f"🔍 Search: '{self.search_query}'")
        if category_filter_var.get() != "All Categories":
            status_parts.append(f"📁 Category: {category_filter_var.get()}")
        if self.current_sort != "Default":
            status_parts.append(f"📊 Sort: {self.current_sort}")
        
        if status_parts:
            status_text = f"📦 Showing {filtered_count} of {total_products} products | {' | '.join(status_parts)}"
        else:
            status_text = f"📦 Total {total_products} products in store"
        
        # Update status label
        for widget in status_bar.winfo_children():
            if isinstance(widget, Label) and hasattr(widget, 'cget') and "📦" in widget.cget("text"):
                widget.config(text=status_text)
                return
        
        # If not found, create it
        Label(status_bar, text=status_text, font=("Segoe UI", 9), 
              bg=DARK_BG, fg="#94a3b8").pack(side=LEFT, padx=20, pady=5)

    # ========== EXISTING METHODS (UPDATED) ==========
    
    def view_products(self):
        """Original view method - now calls sorted version"""
        self.view_products_sorted()

    def update_category_filter(self):
        current = category_filter_var.get()
        cats = ["All Categories"] + sorted(list(self.categories))
        category_filter_menu['values'] = cats
        category_filter_var.set(current if current in cats else "All Categories")
        self.view_products_sorted()

    def search_product(self):
        name = txt_name.get().strip()
        if name in self.products:
            p = self.products[name]
            txt_category.delete(0, END)
            txt_category.insert(0, p.category)
            txt_price.delete(0, END)
            txt_price.insert(0, str(p.price))
            txt_stock.delete(0, END)
            txt_stock.insert(0, str(p.stock))
            txt_discount.delete(0, END)
            txt_discount.insert(0, str(p.discount) if p.discount > 0 else "")
            self.calculate_discounted_price()
            final = p.price - (p.price * p.discount / 100)
            messagebox.showinfo("Found", f"Product: {p.name}\nPrice: {format_currency(p.price)}\nFinal: {format_currency(final)}\nStock: {p.stock}")
        else:
            messagebox.showerror("Error", f"'{name}' not found!")

    def update_product(self):
        name = txt_name.get().strip()
        if name not in self.products:
            messagebox.showerror("Error", "Product not found! Search first.")
            return
        
        try:
            category = txt_category.get().strip().title()
            price = float(txt_price.get().strip())
            stock = int(txt_stock.get().strip())
            discount = float(txt_discount.get().strip()) if txt_discount.get().strip() else 0
            
            if not category:
                category = detect_category(name).title()
            
            old_cat = self.products[name].category
            self.products[name].category = category
            self.products[name].price = price
            self.products[name].stock = stock
            self.products[name].discount = discount
            self.save_product_to_db(self.products[name])
            
            if old_cat != category:
                self.categories.add(category)
                if not any(p.category == old_cat for p in self.products.values()):
                    self.categories.discard(old_cat)
                self.update_category_filter()
            
            self.view_products_sorted()
            self.clear_boxes()
            messagebox.showinfo("Success", "✓ Product Updated!")
        except ValueError:
            messagebox.showerror("Error", "Invalid numbers!")

    def delete_product(self):
        name = txt_name.get().strip()
        if name in self.products:
            if messagebox.askyesno("Confirm", f"Delete '{name}'?"):
                self.delete_product_from_db(name)
                category = self.products[name].category
                del self.products[name]
                if not any(p.category == category for p in self.products.values()):
                    self.categories.discard(category)
                    self.update_category_filter()
                self.view_products_sorted()
                self.clear_boxes()
                messagebox.showinfo("Deleted", f"✓ '{name}' deleted!")
        else:
            messagebox.showerror("Error", "Product not found!")

    def check_and_show_low_stock_alert(self):
        """Check for low stock products and show alert if any"""
        low_products = [p for p in self.products.values() if 0 < p.stock <= 5]
        if low_products:
            self.show_low_stock_alert(low_products)

    def show_low_stock_alert(self, low_products):
        """Show low stock alert with restock buttons"""
        alert = Toplevel(root)
        alert.title("⚠️ LOW STOCK ALERT")
        alert.geometry("600x500")
        alert.config(bg="#0f172a")
        alert.transient(root)
        alert.grab_set()
        
        Label(alert, text="⚠️ LOW STOCK ALERT", font=("Segoe UI", 18, "bold"),
              bg="#0f172a", fg="#ef4444").pack(pady=15)
        
        Label(alert, text="The following products are running low. Please restock soon!",
              font=("Segoe UI", 10), bg="#0f172a", fg="#94a3b8").pack()
        
        frame = Frame(alert, bg="white")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        canvas = Canvas(frame, bg="white", highlightthickness=0)
        scrollbar = Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable = Frame(canvas, bg="white")
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        hframe = Frame(scrollable, bg="#1e293b")
        hframe.pack(fill="x", pady=(0,5))
        Label(hframe, text="Product", width=20, anchor="w", font=("Segoe UI", 10, "bold"),
              bg="#1e293b", fg="white").pack(side=LEFT, padx=10, pady=5)
        Label(hframe, text="Category", width=15, anchor="w", font=("Segoe UI", 10, "bold"),
              bg="#1e293b", fg="white").pack(side=LEFT, padx=10, pady=5)
        Label(hframe, text="Stock", width=8, anchor="center", font=("Segoe UI", 10, "bold"),
              bg="#1e293b", fg="white").pack(side=LEFT, padx=10, pady=5)
        Label(hframe, text="Status", width=10, anchor="center", font=("Segoe UI", 10, "bold"),
              bg="#1e293b", fg="white").pack(side=LEFT, padx=10, pady=5)
        Label(hframe, text="Action", width=12, anchor="center", font=("Segoe UI", 10, "bold"),
              bg="#1e293b", fg="white").pack(side=LEFT, padx=10, pady=5)
        
        def do_restock(product, alert_window):
            new_stock = simpledialog.askinteger(
                "Restock Product",
                f"Product: {product.name}\nCurrent Stock: {product.stock}\n\nEnter additional quantity:",
                parent=alert_window, minvalue=1, maxvalue=10000
            )
            if new_stock and new_stock > 0:
                old_stock = product.stock
                product.stock += new_stock
                self.save_product_to_db(product)
                self.view_products_sorted()
                alert_window.destroy()
                remaining_low = [p for p in self.products.values() if 0 < p.stock <= 5]
                if remaining_low:
                    self.show_low_stock_alert(remaining_low)
                messagebox.showinfo("Restock Successful", 
                    f"✅ {product.name} restocked!\nAdded: +{new_stock}\nNew Stock: {product.stock}")
        
        for p in low_products:
            item_frame = Frame(scrollable, bg="white")
            item_frame.pack(fill="x", pady=2, padx=5)
            
            if p.stock == 1:
                status = "CRITICAL"
                status_color = "#dc2626"
            elif p.stock == 2:
                status = "VERY LOW"
                status_color = "#f97316"
            else:
                status = "LOW"
                status_color = "#eab308"
            
            Label(item_frame, text=p.name, width=20, anchor="w", font=("Segoe UI", 10),
                  bg="white", fg="#1e293b").pack(side=LEFT, padx=10, pady=8)
            Label(item_frame, text=p.category, width=15, anchor="w", font=("Segoe UI", 10),
                  bg="white", fg="#475569").pack(side=LEFT, padx=10, pady=8)
            Label(item_frame, text=str(p.stock), width=8, anchor="center", font=("Segoe UI", 10, "bold"),
                  bg="white", fg=status_color).pack(side=LEFT, padx=10, pady=8)
            Label(item_frame, text=status, width=10, anchor="center", font=("Segoe UI", 10, "bold"),
                  bg="white", fg=status_color).pack(side=LEFT, padx=10, pady=8)
            
            Button(item_frame, text="🔄 Restock", 
                   command=lambda prod=p, a=alert: do_restock(prod, a),
                   bg="#22c55e", fg="white", font=("Segoe UI", 9, "bold"),
                   cursor="hand2", width=9).pack(side=LEFT, padx=10, pady=5)
        
        btn_frame = Frame(alert, bg="#0f172a")
        btn_frame.pack(fill="x", pady=15)
        
        Button(btn_frame, text="📋 VIEW ALL LOW STOCK", 
               command=lambda: [alert.destroy(), self.show_low_stock_window()],
               bg="#38bdf8", fg="white", font=("Segoe UI", 10, "bold"), width=18).pack(side=LEFT, padx=20)
        
        Button(btn_frame, text="🔕 IGNORE", command=alert.destroy,
               bg="#64748b", fg="white", font=("Segoe UI", 10, "bold"), width=10).pack(side=RIGHT, padx=20)

    def sell_product(self):
        name = txt_name.get().strip()
        if name not in self.products:
            messagebox.showerror("Error", "Product not found! Search first.")
            return
        
        p = self.products[name]
        if p.stock == 0:
            messagebox.showerror("Error", f"{name} is out of stock!")
            return
        
        final = p.price - (p.price * p.discount / 100)
        qty = simpledialog.askinteger("Sell", f"Quantity for {name}\nStock: {p.stock}\nPrice: {format_currency(final)}")
        
        if not qty or qty <= 0:
            return
        if qty > p.stock:
            messagebox.showerror("Error", f"Only {p.stock} available!")
            return
        
        subtotal = qty * p.price
        save = subtotal * p.discount / 100
        total = subtotal - save
        
        p.stock -= qty
        self.total_sales += total
        self.save_product_to_db(p)
        
        trans_id = self.get_next_transaction_id()
        
        receipt = f"""
{'='*46}
        SMART STORE - RECEIPT
{'='*46}
Bill No: {trans_id}
Date: {datetime.now().strftime('%d-%m-%Y %I:%M:%S %p')}
{'='*46}
Product: {p.name}
Category: {p.category}
Qty: {qty} x {format_currency(p.price)}
Discount: {p.discount}%
{'='*46}
Subtotal: {format_currency(subtotal)}
You Save: {format_currency(save)}
TOTAL: {format_currency(total)}
{'='*46}
Thank you! Visit Again!
"""
        
        trans = {
            "id": trans_id,
            "date": datetime.now().strftime("%d-%m-%Y"),
            "time": datetime.now().strftime("%I:%M:%S %p"),
            "name": p.name, "category": p.category, "qty": qty,
            "price": p.price, "discount": p.discount, "total": total
        }
        self.transactions.append(trans)
        self.save_transaction_to_db(trans)
        self.view_products_sorted()
        self.clear_boxes()
        
        if messagebox.askyesno("Print", f"{receipt}\n\nPrint receipt?"):
            print_receipt(receipt)
        else:
            messagebox.showinfo("Receipt", receipt)
        
        self.check_and_show_low_stock_alert()

    def restock_product(self, product_name, current_stock):
        dialog = Toplevel(root)
        dialog.title("Restock Product")
        dialog.geometry("400x350")
        dialog.config(bg="#0f172a")
        dialog.resizable(False, False)
        dialog.transient(root)
        dialog.grab_set()
        
        Label(dialog, text="📦 RESTOCK PRODUCT", font=("Segoe UI", 18, "bold"),
              bg="#0f172a", fg="#38bdf8").pack(pady=20)
        
        main_frame = Frame(dialog, bg="#1e293b", relief=RAISED, bd=2)
        main_frame.pack(fill="both", expand=True, padx=25, pady=15)
        
        info_frame = Frame(main_frame, bg="#1e293b")
        info_frame.pack(fill="x", pady=15, padx=20)
        
        Label(info_frame, text="Product:", font=("Segoe UI", 12, "bold"),
              bg="#1e293b", fg="#94a3b8").grid(row=0, column=0, sticky="w", pady=8)
        Label(info_frame, text=product_name, font=("Segoe UI", 12, "bold"),
              bg="#1e293b", fg="#38bdf8").grid(row=0, column=1, sticky="w", padx=15, pady=8)
        
        Label(info_frame, text="Current Stock:", font=("Segoe UI", 12, "bold"),
              bg="#1e293b", fg="#94a3b8").grid(row=1, column=0, sticky="w", pady=8)
        Label(info_frame, text=str(current_stock), font=("Segoe UI", 14, "bold"),
              bg="#1e293b", fg="#fbbf24").grid(row=1, column=1, sticky="w", padx=15, pady=8)
        
        Frame(main_frame, bg="#334155", height=2).pack(fill="x", padx=20, pady=10)
        
        qty_frame = Frame(main_frame, bg="#1e293b")
        qty_frame.pack(fill="x", pady=15, padx=20)
        
        Label(qty_frame, text="Enter additional quantity:", font=("Segoe UI", 11, "bold"),
              bg="#1e293b", fg="white").pack(anchor="w", pady=(0,10))
        
        qty_var = StringVar()
        qty_entry = Entry(qty_frame, textvariable=qty_var, font=("Segoe UI", 14),
                          justify="center", width=15, bg="white", fg="#1e293b",
                          relief=SOLID, bd=2)
        qty_entry.pack(pady=5, ipady=8)
        qty_entry.focus()
        
        def do_restock():
            try:
                add_qty = int(qty_var.get().strip())
                if add_qty <= 0:
                    messagebox.showerror("Error", "Quantity must be greater than 0")
                    return
                if add_qty > 10000:
                    messagebox.showerror("Error", "Maximum restock is 10,000")
                    return
                
                old_stock = self.products[product_name].stock
                self.products[product_name].stock += add_qty
                self.save_product_to_db(self.products[product_name])
                self.view_products_sorted()
                
                messagebox.showinfo("Success", 
                    f"✅ Restock Successful!\n\nProduct: {product_name}\nAdded: +{add_qty}\nStock: {old_stock} → {self.products[product_name].stock}")
                
                dialog.destroy()
                
                if self.products[product_name].stock > 5:
                    if product_name in self.low_stock_shown:
                        self.low_stock_shown.remove(product_name)
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        btn_frame = Frame(main_frame, bg="#1e293b")
        btn_frame.pack(fill="x", pady=20, padx=20)
        
        Button(btn_frame, text="OK", command=do_restock,
               bg="#22c55e", fg="white", font=("Segoe UI", 11, "bold"),
               width=10, height=1, cursor="hand2").pack(side=LEFT, padx=10, expand=True)
        
        Button(btn_frame, text="Cancel", command=dialog.destroy,
               bg="#ef4444", fg="white", font=("Segoe UI", 11, "bold"),
               width=10, height=1, cursor="hand2").pack(side=RIGHT, padx=10, expand=True)

    def open_return_page(self):
        return_win = Toplevel(root)
        return_win.title("📝 Product Return")
        return_win.geometry("650x600")
        return_win.config(bg="#0f172a")
        return_win.resizable(False, False)
        
        Label(return_win, text="📝 PRODUCT RETURN",
              font=("Segoe UI", 20, "bold"), bg="#0f172a", fg="#38bdf8").pack(pady=20)
        
        main_frame = Frame(return_win, bg="#1e293b", relief=RAISED, bd=2)
        main_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        Label(main_frame, text="Product Name *", font=("Segoe UI", 11, "bold"),
              bg="#1e293b", fg="white").pack(anchor="w", padx=20, pady=(20,5))
        return_product_var = StringVar()
        Entry(main_frame, textvariable=return_product_var, font=("Segoe UI", 12)).pack(padx=20, fill="x", pady=5)
        
        Label(main_frame, text="Return Quantity *", font=("Segoe UI", 11, "bold"),
              bg="#1e293b", fg="white").pack(anchor="w", padx=20, pady=(15,5))
        return_qty_var = StringVar()
        Entry(main_frame, textvariable=return_qty_var, font=("Segoe UI", 12)).pack(padx=20, fill="x", pady=5)
        
        Label(main_frame, text="Return Reason *", font=("Segoe UI", 11, "bold"),
              bg="#1e293b", fg="white").pack(anchor="w", padx=20, pady=(15,5))
        return_reason_var = StringVar()
        reasons = ["Damaged Product", "Wrong Product", "Expired Product", "Defective Item", "Changed Mind", "Other"]
        ttk.Combobox(main_frame, textvariable=return_reason_var, values=reasons, 
                     state="readonly", font=("Segoe UI", 11)).pack(padx=20, fill="x", pady=5)
        
        Label(main_frame, text="Custom Reason:", font=("Segoe UI", 10),
              bg="#1e293b", fg="#94a3b8").pack(anchor="w", padx=20, pady=(10,0))
        custom_reason_entry = Entry(main_frame, font=("Segoe UI", 11))
        custom_reason_entry.pack(padx=20, fill="x", pady=5)
        
        def submit_return():
            product_name = return_product_var.get().strip()
            if not product_name or product_name not in self.products:
                messagebox.showerror("Error", "Product not found!")
                return
            
            try:
                qty = int(return_qty_var.get().strip())
                if qty <= 0:
                    messagebox.showerror("Error", "Invalid quantity!")
                    return
            except:
                messagebox.showerror("Error", "Enter valid quantity!")
                return
            
            product = self.products[product_name]
            reason = return_reason_var.get()
            custom = custom_reason_entry.get().strip()
            if custom:
                reason = custom
            elif not reason:
                messagebox.showerror("Error", "Please select a reason!")
                return
            
            final_price = product.price - (product.price * product.discount / 100)
            refund = final_price * qty
            old_stock = product.stock
            product.stock += qty
            self.save_product_to_db(product)
            
            self.total_returns += refund
            self.total_sales -= refund
            
            return_item = ReturnItem(product_name, qty, refund, reason, 
                                    datetime.now().strftime("%d-%m-%Y"))
            self.returns.append(return_item)
            self.save_return_to_db(return_item)
            self.view_products_sorted()
            
            receipt = f"""
{'='*50}
        RETURN RECEIPT
{'='*50}
Product: {product_name}
Quantity: {qty}
Refund: {format_currency(refund)}
Reason: {reason}
Stock: {old_stock} → {product.stock}
{'='*50}
✅ Return Successful!
"""
            messagebox.showinfo("Return Successful", receipt)
            return_win.destroy()
        
        btn_frame = Frame(main_frame, bg="#1e293b")
        btn_frame.pack(fill="x", padx=20, pady=25)
        center_btn_frame = Frame(btn_frame, bg="#1e293b")
        center_btn_frame.pack(expand=True)
        
        Button(center_btn_frame, text="✅ SUBMIT", command=submit_return,
               bg="#22c55e", fg="white", font=("Segoe UI", 11, "bold"), 
               width=14, height=1, padx=10, pady=6, cursor="hand2").pack(side=LEFT, padx=15)
        Button(center_btn_frame, text="❌ CANCEL", command=return_win.destroy,
               bg="#ef4444", fg="white", font=("Segoe UI", 11, "bold"), 
               width=14, height=1, padx=10, pady=6, cursor="hand2").pack(side=RIGHT, padx=15)

    def show_returns(self):
        if not self.returns:
            messagebox.showinfo("Returns", "No returns yet!")
            return
        win = Toplevel(root)
        win.title("Return History")
        win.geometry("900x500")
        win.config(bg="#0f172a")
        Label(win, text="📋 RETURN HISTORY", font=("Segoe UI", 20, "bold"),
              bg="#0f172a", fg="#38bdf8").pack(pady=15)
        
        frame = Frame(win, bg="white")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tree = ttk.Treeview(frame, columns=("Date", "Product", "Qty", "Amount", "Reason"), show="headings", height=15)
        for c in ("Date", "Product", "Qty", "Amount", "Reason"):
            tree.heading(c, text=c)
        tree.column("Date", width=120, anchor="center")
        tree.column("Product", width=200, anchor="w")
        tree.column("Qty", width=80, anchor="center")
        tree.column("Amount", width=120, anchor="center")
        tree.column("Reason", width=320, anchor="w")
        
        for r in self.returns:
            tree.insert("", END, values=(r.return_date, r.product_name, r.quantity, format_currency(r.amount), r.reason))
        
        scrollbar = Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        Button(win, text="❌ CLOSE", command=win.destroy, 
               bg="#38bdf8", fg="white", font=("Segoe UI", 11, "bold"),
               width=12, height=1, padx=10, pady=5, cursor="hand2").pack(pady=10)

    def show_sales(self):
        net = self.total_sales - self.total_returns
        messagebox.showinfo("Sales Summary", 
            f"Gross Sales: {format_currency(self.total_sales)}\n"
            f"Returns: {format_currency(self.total_returns)}\n"
            f"Net Sales: {format_currency(net)}")

    def show_low_stock_window(self):
        low_items = [p for p in self.products.values() if 0 < p.stock <= 5]
        if not low_items:
            messagebox.showinfo("Low Stock", "✅ No low stock products!")
            return
        
        win = Toplevel(root)
        win.title("⚠️ LOW STOCK ALERT - FULL LIST")
        win.geometry("900x550")
        win.config(bg="#0f172a")
        
        Label(win, text="⚠️ LOW STOCK PRODUCTS",
              font=("Segoe UI", 18, "bold"), bg="#0f172a", fg="#ef4444").pack(pady=15)
        
        main_frame = Frame(win, bg="white")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        canvas = Canvas(main_frame, bg="white", highlightthickness=0)
        scrollbar = Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas, bg="white")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        headers = ["#", "Product", "Category", "Stock", "Status", "Action"]
        for col, header in enumerate(headers):
            Label(scrollable_frame, text=header,
                  font=("Segoe UI", 11, "bold"), bg="#1e293b", fg="#38bdf8",
                  padx=10, pady=10, relief=RAISED, bd=1).grid(row=0, column=col, sticky="nsew")
        
        scrollable_frame.grid_columnconfigure(0, weight=0, minsize=50)
        scrollable_frame.grid_columnconfigure(1, weight=3, minsize=200)
        scrollable_frame.grid_columnconfigure(2, weight=2, minsize=150)
        scrollable_frame.grid_columnconfigure(3, weight=1, minsize=80)
        scrollable_frame.grid_columnconfigure(4, weight=1, minsize=100)
        scrollable_frame.grid_columnconfigure(5, weight=1, minsize=100)
        
        def do_restock(product, window):
            new_stock = simpledialog.askinteger(
                "Restock Product",
                f"Product: {product.name}\nCurrent Stock: {product.stock}\n\nEnter additional quantity:",
                parent=window, minvalue=1, maxvalue=10000
            )
            if new_stock and new_stock > 0:
                old_stock = product.stock
                product.stock += new_stock
                self.save_product_to_db(product)
                self.view_products_sorted()
                window.destroy()
                self.show_low_stock_window()
                messagebox.showinfo("✅ Restock Successful", 
                    f"Product: {product.name}\nAdded: +{new_stock}\nStock: {old_stock} → {product.stock}")
        
        for idx, p in enumerate(low_items, start=1):
            if p.stock == 1:
                status_text = "🔴 CRITICAL"
                status_color = "#ef4444"
                row_bg = "#fef2f2"
            elif p.stock == 2:
                status_text = "🟠 VERY LOW"
                status_color = "#f97316"
                row_bg = "#fff7ed"
            else:
                status_text = "🟡 LOW"
                status_color = "#eab308"
                row_bg = "#fefce8"
            
            if idx % 2 == 0:
                row_bg = "#ffffff"
            
            Label(scrollable_frame, text=str(idx), font=("Segoe UI", 10),
                  bg=row_bg, fg="#1e293b", padx=10, pady=8, relief=FLAT).grid(row=idx, column=0, sticky="nsew")
            Label(scrollable_frame, text=p.name, font=("Segoe UI", 10, "bold"),
                  bg=row_bg, fg="#1e293b", padx=10, pady=8, anchor="w", relief=FLAT).grid(row=idx, column=1, sticky="nsew")
            Label(scrollable_frame, text=p.category, font=("Segoe UI", 10),
                  bg=row_bg, fg="#475569", padx=10, pady=8, anchor="w", relief=FLAT).grid(row=idx, column=2, sticky="nsew")
            Label(scrollable_frame, text=str(p.stock), font=("Segoe UI", 10, "bold"),
                  bg=row_bg, fg=status_color, padx=10, pady=8, relief=FLAT).grid(row=idx, column=3, sticky="nsew")
            Label(scrollable_frame, text=status_text, font=("Segoe UI", 10, "bold"),
                  bg=row_bg, fg=status_color, padx=10, pady=8, relief=FLAT).grid(row=idx, column=4, sticky="nsew")
            
            Button(scrollable_frame, text="🔄 Restock", 
                   command=lambda prod=p, w=win: do_restock(prod, w),
                   bg="#22c55e", fg="white", font=("Segoe UI", 9, "bold"),
                   cursor="hand2", width=10).grid(row=idx, column=5, padx=10, pady=5)
        
        Button(win, text="❌ CLOSE", command=win.destroy,
               bg="#38bdf8", fg="white", font=("Segoe UI", 11, "bold"),
               width=15, height=1, padx=15, pady=6, cursor="hand2").pack(pady=10)

    def show_transactions(self):
        win = Toplevel(root)
        win.title("Transaction History")
        win.geometry("1300x550")
        win.config(bg="#0f172a")
        Label(win, text="📊 TRANSACTION HISTORY", font=("Segoe UI", 20, "bold"),
              bg="#0f172a", fg="#38bdf8").pack(pady=15)
        
        frame = Frame(win, bg="white")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tree = ttk.Treeview(frame, columns=("ID", "Date", "Time", "Product", "Category", "Qty", "Price", "Discount", "Total"), show="headings", height=15)
        for c in ("ID", "Date", "Time", "Product", "Category", "Qty", "Price", "Discount", "Total"):
            tree.heading(c, text=c)
        tree.column("ID", width=100, anchor="center")
        tree.column("Date", width=100, anchor="center")
        tree.column("Time", width=100, anchor="center")
        tree.column("Product", width=180, anchor="w")
        tree.column("Category", width=120, anchor="w")
        tree.column("Qty", width=70, anchor="center")
        tree.column("Price", width=100, anchor="center")
        tree.column("Discount", width=80, anchor="center")
        tree.column("Total", width=120, anchor="center")
        
        for t in self.transactions:
            tree.insert("", END, values=(t["id"], t["date"], t["time"], t["name"], t["category"],
                                        t["qty"], format_currency(t["price"]), f"{t['discount']}%",
                                        format_currency(t["total"])))
        
        scrollbar = Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        total = sum(t["total"] for t in self.transactions)
        bottom = Frame(win, bg="#0f172a")
        bottom.pack(fill="x", pady=10)
        Label(bottom, text=f"💰 TOTAL SALES = {format_currency(total)}", font=("Segoe UI", 12, "bold"),
              bg="#0f172a", fg="#22c55e").pack(side=LEFT, padx=20)
        Button(bottom, text="❌ CLOSE", command=win.destroy, bg="#38bdf8", fg="white",
               font=("Segoe UI", 11, "bold"), width=12, height=1, padx=10, pady=5, cursor="hand2").pack(side=RIGHT, padx=20)


# ========== MAIN WINDOW ==========
root = Tk()
root.title("✨ Smart Store Management System")
root.geometry("1200x700")
root.config(bg="#0f172a")
root.state("zoomed")
root.withdraw()

# ========== LOGIN ==========
def login_check():
    if entry_user.get() == "admin" and entry_pass.get() == "1234":
        login_window.destroy()
        root.deiconify()
    else:
        messagebox.showerror("Login Failed", "Wrong Username or Password")

login_window = Toplevel(root)
login_window.title("Login")
login_window.geometry("350x250")
login_window.config(bg="#0f172a")
login_window.state("zoomed")

Label(login_window, text="✨ SMART STORE LOGIN ✨",
      font=("Segoe UI", 15, "bold"), bg="#0f172a", fg="#38bdf8").pack(pady=15)
Label(login_window, text="Username", bg="#0f172a", fg="white").pack()
entry_user = Entry(login_window, font=("Segoe UI", 11))
entry_user.pack(pady=5)
Label(login_window, text="Password", bg="#0f172a", fg="white").pack()
entry_pass = Entry(login_window, show="*", font=("Segoe UI", 11))
entry_pass.pack(pady=5)
Button(login_window, text="🔓 LOGIN", command=login_check,
       bg="#38bdf8", font=("Segoe UI", 11, "bold"), 
       width=10, height=1, padx=10, pady=5, cursor="hand2").pack(pady=15)

# Create store instance
store = SmartStore()

# ========== UI ==========
THEME_COLOR = "#38bdf8"
DARK_BG = "#0f172a"
LIGHT_BG = "#f8fafc"

header_frame = Frame(root, bg=DARK_BG, height=70)
header_frame.pack(fill="x", pady=(10,0))
Label(header_frame, text="🏪 SMART STORE MANAGEMENT SYSTEM",
      font=("Segoe UI", 26, "bold"), bg=DARK_BG, fg=THEME_COLOR).pack()
Label(header_frame, text="Auto Category Detection | Smart Inventory | PKR Currency | Search | Price Sort",
      font=("Segoe UI", 10), bg=DARK_BG, fg="#94a3b8").pack()

# Left Panel
left = Frame(root, bg=LIGHT_BG, relief=RAISED, bd=2)
left.place(x=20, y=90, width=380, height=590)
Label(left, text="📝 PRODUCT MANAGEMENT", font=("Segoe UI", 16, "bold"), bg=LIGHT_BG, fg=DARK_BG).pack(pady=12)

Label(left, text="Product Name", font=("Segoe UI", 9, "bold"), bg=LIGHT_BG, fg="#475569").pack(anchor="w", padx=25, pady=(8,0))
txt_name = Entry(left, font=("Segoe UI", 10), bg="white")
txt_name.pack(padx=25, fill="x", pady=(3,0))
txt_name.bind("<KeyRelease>", store.auto_detect_category)

Label(left, text="Category (Auto-detected)", font=("Segoe UI", 9, "bold"), bg=LIGHT_BG, fg="#475569").pack(anchor="w", padx=25, pady=(8,0))
txt_category = Entry(left, font=("Segoe UI", 10), bg="white")
txt_category.pack(padx=25, fill="x", pady=(3,0))

Label(left, text=f"Original Price ({CURRENCY_SYMBOL})", font=("Segoe UI", 9, "bold"), bg=LIGHT_BG, fg="#475569").pack(anchor="w", padx=25, pady=(8,0))
txt_price = Entry(left, font=("Segoe UI", 10), bg="white")
txt_price.pack(padx=25, fill="x", pady=(3,0))
txt_price.bind("<KeyRelease>", store.calculate_discounted_price)

Label(left, text="Stock Quantity", font=("Segoe UI", 9, "bold"), bg=LIGHT_BG, fg="#475569").pack(anchor="w", padx=25, pady=(8,0))
txt_stock = Entry(left, font=("Segoe UI", 10), bg="white")
txt_stock.pack(padx=25, fill="x", pady=(3,0))

Label(left, text="Discount (%)", font=("Segoe UI", 9, "bold"), bg=LIGHT_BG, fg="#475569").pack(anchor="w", padx=25, pady=(8,0))
txt_discount = Entry(left, font=("Segoe UI", 10), bg="white")
txt_discount.pack(padx=25, fill="x", pady=(3,0))
txt_discount.bind("<KeyRelease>", store.calculate_discounted_price)

lbl_discounted_price = Label(left, text=f"💰 Final Price: {format_currency(0)}",
                              font=("Segoe UI", 11, "bold"), bg="#e2e8f0", fg="#38bdf8",
                              pady=8, relief=SOLID, bd=1)
lbl_discounted_price.pack(padx=25, fill="x", pady=(10,5))

btn_style = {"font": ("Segoe UI", 10, "bold"), "height": 1, "relief": RAISED, "bd": 0, "bg": THEME_COLOR, "fg": "white", "cursor": "hand2"}
btn_frame = Frame(left, bg=LIGHT_BG)
btn_frame.pack(pady=15, fill="x", padx=25)

Button(btn_frame, text="ADD PRODUCT", command=store.add_product, **btn_style).pack(fill="x", pady=4)
Button(btn_frame, text="SEARCH", command=store.search_product, **btn_style).pack(fill="x", pady=4)
Button(btn_frame, text="UPDATE", command=store.update_product, **btn_style).pack(fill="x", pady=4)
Button(btn_frame, text="DELETE", command=store.delete_product, **btn_style).pack(fill="x", pady=4)

# Right Panel
right = Frame(root, bg=LIGHT_BG, relief=RAISED, bd=2)
right.place(x=420, y=90, width=870, height=590)

top_btn_frame = Frame(right, bg=LIGHT_BG, height=50)
top_btn_frame.pack(fill="x", padx=15, pady=8)

Button(top_btn_frame, text=" SELL", command=store.sell_product, **btn_style, width=10).pack(side=LEFT, padx=4)
Button(top_btn_frame, text="RETURN", command=store.open_return_page, **btn_style, width=10).pack(side=LEFT, padx=4)
Button(top_btn_frame, text="SALES", command=store.show_sales, **btn_style, width=10).pack(side=LEFT, padx=4)
Button(top_btn_frame, text="TRANSACTIONS", command=store.show_transactions, **btn_style, width=14).pack(side=LEFT, padx=4)
Button(top_btn_frame, text="RETURNS", command=store.show_returns, **btn_style, width=10).pack(side=LEFT, padx=4)
Button(top_btn_frame, text="LOW STOCK", command=store.show_low_stock_window, **btn_style, width=12).pack(side=LEFT, padx=4)

# ========== NEW: SEARCH AND SORTING CONTROLS ==========
# Search Frame
search_frame = Frame(right, bg=LIGHT_BG)
search_frame.pack(fill="x", padx=15, pady=(0,8))

Label(search_frame, text="🔎 Search Product:", font=("Segoe UI", 9, "bold"), 
      bg=LIGHT_BG, fg="#475569").pack(side=LEFT)

search_box = Entry(search_frame, font=("Segoe UI", 10), bg="white", width=30)
search_box.pack(side=LEFT, padx=8)
search_box.bind("<KeyRelease>", store.on_search_change)

Button(search_frame, text="✖ Clear", command=store.clear_search,
       font=("Segoe UI", 9), bg="#64748b", fg="white", cursor="hand2", padx=10).pack(side=LEFT, padx=5)

# Sorting Frame
sort_frame = Frame(right, bg=LIGHT_BG)
sort_frame.pack(fill="x", padx=15, pady=(0,8))

Label(sort_frame, text="📊 Sort by Price:", font=("Segoe UI", 9, "bold"), 
      bg=LIGHT_BG, fg="#475569").pack(side=LEFT)

sort_var = StringVar()
sort_var.set("Default")
sort_menu = ttk.Combobox(sort_frame, textvariable=sort_var, 
                         values=["Default", "Price: Low to High", "Price: High to Low"],
                         state="readonly", width=18)
sort_menu.pack(side=LEFT, padx=8)
sort_menu.bind("<<ComboboxSelected>>", store.on_sort_change)

# Filter Frame
filter_frame = Frame(right, bg=LIGHT_BG)
filter_frame.pack(fill="x", padx=15, pady=(0,8))
Label(filter_frame, text="🔍 Filter by Category:", font=("Segoe UI", 9, "bold"), bg=LIGHT_BG, fg="#475569").pack(side=LEFT)
category_filter_var = StringVar()
category_filter_var.set("All Categories")
category_filter_menu = ttk.Combobox(filter_frame, textvariable=category_filter_var, state="readonly", width=25)
category_filter_menu.pack(side=LEFT, padx=8)
category_filter_menu.bind("<<ComboboxSelected>>", lambda e: store.view_products_sorted())

# Table Frame
table_frame = Frame(right, bg="white")
table_frame.pack(fill="both", expand=True, padx=15, pady=5)

style = ttk.Style()
style.theme_use("clam")
style.configure("Custom.Treeview", background="white", foreground="#1e293b", rowheight=30, font=("Segoe UI", 9))
style.configure("Custom.Treeview.Heading", background="#0f172a", foreground="#38bdf8", font=("Segoe UI", 10, "bold"))

table = ttk.Treeview(table_frame, columns=("Name", "Category", "Price", "Final Price", "Stock", "Discount"),
                     show="headings", style="Custom.Treeview", height=20)
table.heading("Name", text="Product")
table.heading("Category", text="Category")
table.heading("Price", text="Original Price")
table.heading("Final Price", text="After Discount")
table.heading("Stock", text="Stock")
table.heading("Discount", text="Disc%")

table.column("Name", width=220, anchor="w")
table.column("Category", width=140, anchor="w")
table.column("Price", width=110, anchor="e")
table.column("Final Price", width=120, anchor="e")
table.column("Stock", width=80, anchor="center")
table.column("Discount", width=70, anchor="center")

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
scrollbar.pack(side="right", fill="y")
table.configure(yscrollcommand=scrollbar.set)
table.pack(fill="both", expand=True)

# Status Bar
status_bar = Frame(root, bg=DARK_BG, height=30)
status_bar.pack(side=BOTTOM, fill="x")
Label(status_bar, text="💾 SQLite Database | 🇵🇰 PKR | ✅ Search | ✅ Price Sort (Low→High / High→Low)",
      font=("Segoe UI", 9), bg=DARK_BG, fg="#94a3b8").pack(side=LEFT, padx=20, pady=5)
Label(status_bar, text="© Smart Store v4.0", font=("Segoe UI", 9), bg=DARK_BG, fg="#94a3b8").pack(side=RIGHT, padx=20, pady=5)

# Initial load
store.update_category_filter()
store.view_products_sorted()
store.update_status_with_count()

root.mainloop()