
import re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BANK_CODE = "RJHI"
EMPLOYER_ID = "00068776"
EMPLOYER_ACCOUNT = "SA3180000584608016210209"
CURRENCY = "SAR"
DEFAULT_UNIFIED = "1-18895884245"
DEFAULT_REJECT_CODE = "P000"
DEFAULT_EST_NO = "01-2045418"
BANK_SIGNATURE = 'Dho4TPhQUFj4d6b68y48knik3XiAvYmLN3h1iZKXr6bo+oweQnXnWyNMMkGM9XDAcdd4ZAzeUDQqNOyuuedWF50qLSMrLcXTeeB87EcUMoV03r3J4lgK9RpeuEukyKNJtmm6FB5Riwm+RmqquOhHAQq4+ceygP9mT7OQejrnASelhpMfEUKBuw7X5nnJAIyGu3lCLXxPlfKR4JJqMhyWtg3QexH/EpB3i3zyiqCwOlCI2Ftb2d8+02YSUiF35kqyh4qBIg52GVeoO8T8ELIwqDQRNo9LYD4lngUX+d4fNeTXCJeQcVQw74UR6/oPgH5vX5LTrR9l8AyxbjjXpaVEqA=='

def clean_amount(v):
    v = str(v or "").replace(",", "").replace("ريال", "").replace("ر.س", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", v)
    return float(m.group(0)) if m else 0.0

def money(v):
    return f"{int(round(float(v or 0))):013d},00"

def find_iban(line):
    s = line.upper().replace(" ", "").replace("-", "")
    m = re.search(r"(SA[A-Z0-9]{22})", s)
    return m.group(1) if m else ""

def parse_paste(text, default_salary):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    company = ""
    unified = ""
    workers = []
    cur = {}

    for line in lines:
        if line.startswith("مؤسسة") or line.startswith("شركة"):
            company = line
            continue

        if "رقم موحد" in line or re.fullmatch(r"\d{1,3}\s*-\s*\d{5,12}", line):
            m = re.search(r"(\d{1,3})\s*-\s*(\d{5,12})", line)
            if m:
                unified = f"{m.group(1)}-{m.group(2)}"
            continue

        if re.match(r"^(الاسم|اسم)\s*[:：]", line):
            if cur.get("name"):
                workers.append(cur)
                cur = {}
            cur["name"] = re.sub(r"^(الاسم|اسم)\s*[:：]\s*", "", line).strip()
            continue

        if "رقم الهوية" in line or "الهوية" in line or "الإقامة" in line or "الاقامة" in line:
            ids = re.findall(r"\d{7,15}", line)
            if ids:
                cur["id"] = ids[0]
            continue

        iban = find_iban(line)
        if iban:
            cur["iban"] = iban
            continue

        if re.fullmatch(r"[\d,]+(?:\.\d+)?(?:\s*ريال)?", line):
            cur["salary"] = clean_amount(line)
            continue

    if cur.get("name"):
        workers.append(cur)

    result = []
    for w in workers:
        result.append({
            "name": w.get("name", "").strip(),
            "id": w.get("id", "").strip(),
            "iban": w.get("iban", "").strip(),
            "salary": float(w.get("salary", default_salary) or default_salary or 0),
        })
    return company, unified, result

def validate(unified, workers):
    errors = []
    if not unified:
        errors.append("الرقم الموحد/مرجع المنشأة مفقود")
    if not workers:
        errors.append("لا يوجد عمال")
    for i, w in enumerate(workers, 1):
        if not w["name"]:
            errors.append(f"العامل {i}: الاسم مفقود")
        if not w["id"]:
            errors.append(f"العامل {i}: رقم الهوية/الإقامة مفقود")
        if not w["iban"]:
            errors.append(f"العامل {i}: الآيبان مفقود")
        elif not re.fullmatch(r"SA[A-Z0-9]{22}", w["iban"]):
            errors.append(f"العامل {i}: الآيبان غير صحيح")
        if w["salary"] <= 0:
            errors.append(f"العامل {i}: الراتب صفر أو غير صحيح")
    return errors

def build_file(unified, workers, central_base):
    today = datetime.now().strftime("%Y%m%d")
    total = sum(w["salary"] for w in workers)
    lines = []
    lines.append("\t".join([
        BANK_CODE,
        f"{EMPLOYER_ID:<11}",
        EMPLOYER_ACCOUNT,
        CURRENCY,
        today,
        money(total),
        today,
        f"{unified:<18}",
        f"{DEFAULT_REJECT_CODE:<7}",
        f"{DEFAULT_EST_NO:<18}",
    ]))
    base_ref = int(central_base or "1090442768")
    for i, w in enumerate(workers, 1):
        gross = money(w["salary"])
        ref = datetime.now().strftime("%y%m%d") + f"{i:010d}"
        central = f"Centralization Ref:{base_ref + i - 1}"
        line = "\t".join([
            gross,
            f"{w['iban']:<36}",
            f"{w['name']:<140}",
            f"RJHI".ljust(140),
            central.ljust(140),
            "      ",
            gross,
            "0000000000000,00",
            "0000000000000,00",
            "0000000000000,00",
            w["id"],
            ref,
            "Success ",
            today,
        ])
        lines.append(line)
    lines.append("-")
    lines.append(BANK_SIGNATURE)
    return "\n".join(lines)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("السيف")
        self.geometry("455x635")
        self.minsize(430, 600)
        self.configure(fg_color="#171717")

        ctk.CTkLabel(self, text="السيف", font=("Arial", 27, "bold"), text_color="#00c8ff").pack(pady=(10, 0))
        ctk.CTkLabel(self, text="أداة تجهيز ملف الأجور", font=("Arial", 11), text_color="#eeeeee").pack(pady=(0, 8))

        self.e_unified = ctk.CTkEntry(self, width=410, height=34, placeholder_text="الرقم الموحد / مرجع المنشأة", justify="center")
        self.e_unified.insert(0, DEFAULT_UNIFIED)
        self.e_unified.pack(pady=3)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=2)
        self.e_non = ctk.CTkEntry(row, width=198, height=34, placeholder_text="راتب غير السعودي", justify="center")
        self.e_non.insert(0, "2000")
        self.e_non.pack(side="left", padx=5)
        self.e_sa = ctk.CTkEntry(row, width=198, height=34, placeholder_text="راتب السعودي", justify="center")
        self.e_sa.insert(0, "5000")
        self.e_sa.pack(side="right", padx=5)

        self.e_ref = ctk.CTkEntry(self, width=410, height=32, placeholder_text="Centralization Ref بداية", justify="center")
        self.e_ref.insert(0, "1090442768")
        self.e_ref.pack(pady=3)

        top_btns = ctk.CTkFrame(self, fg_color="transparent")
        top_btns.pack(padx=20, pady=(5, 5), fill="x")
        top_btns.grid_columnconfigure((0,1,2,3), weight=1)
        ctk.CTkButton(top_btns, text="لصق", height=32, command=self.paste).grid(row=0, column=0, padx=3, sticky="ew")
        ctk.CTkButton(top_btns, text="تحديد الكل", height=32, fg_color="#555", command=self.select_all).grid(row=0, column=1, padx=3, sticky="ew")
        ctk.CTkButton(top_btns, text="فحص", height=32, fg_color="#777", command=self.check).grid(row=0, column=2, padx=3, sticky="ew")
        ctk.CTkButton(top_btns, text="توليد", height=32, fg_color="#18c8e8", command=self.generate).grid(row=0, column=3, padx=3, sticky="ew")

        frame = ctk.CTkFrame(self, fg_color="#202020", border_width=1, border_color="#666")
        frame.pack(padx=20, pady=(5, 7), fill="both", expand=True)
        self.text = tk.Text(frame, bg="#202020", fg="white", insertbackground="white", font=("Arial", 12), relief="flat", wrap="word", padx=10, pady=10)
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.text.bind("<Control-v>", self.paste_event)
        self.text.bind("<Control-a>", self.select_all_event)
        self.text.bind("<Button-3>", self.menu_popup)

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="تحديد الكل", command=self.select_all)
        self.menu.add_command(label="لصق", command=self.paste)
        self.menu.add_command(label="نسخ", command=lambda: self.text.event_generate("<<Copy>>"))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(padx=20, pady=(0, 8), fill="x")
        bottom.grid_columnconfigure((0,1), weight=1)
        ctk.CTkButton(bottom, text="حذف", height=38, fg_color="#b0182f", command=lambda: self.text.delete("1.0", "end")).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bottom, text="توليد ملف", height=38, fg_color="#18c8e8", font=("Arial", 13, "bold"), command=self.generate).grid(row=0, column=1, padx=4, sticky="ew")

        self.status = ctk.CTkLabel(self, text="جاهز", text_color="#ffd84d", font=("Arial", 11, "bold"))
        self.status.pack(pady=(0, 5))

    def select_all_event(self, event=None):
        self.select_all()
        return "break"

    def select_all(self):
        self.text.tag_add("sel", "1.0", "end")
        self.text.focus_set()

    def paste_event(self, event=None):
        self.paste()
        return "break"

    def paste(self):
        try:
            self.text.insert("insert", self.clipboard_get())
        except Exception:
            messagebox.showwarning("تنبيه", "لا يوجد نص منسوخ")

    def menu_popup(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def get_data(self):
        company, unified_from_text, workers = parse_paste(self.text.get("1.0", "end"), clean_amount(self.e_non.get()))
        unified = self.e_unified.get().strip() or unified_from_text
        if unified_from_text and not self.e_unified.get().strip():
            self.e_unified.insert(0, unified_from_text)
        return company, unified, workers

    def check(self):
        company, unified, workers = self.get_data()
        errors = validate(unified, workers)
        if errors:
            messagebox.showerror("نواقص", "\n".join(errors[:40]))
        else:
            messagebox.showinfo("الفحص", f"الفحص سليم\nعدد العمال: {len(workers)}\nجاهز للتوليد")

    def generate(self):
        company, unified, workers = self.get_data()
        errors = validate(unified, workers)
        if errors:
            messagebox.showerror("لا يمكن توليد ملف ناقص", "\n".join(errors[:40]))
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"WPS_File_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not path:
            return

        Path(path).write_text(build_file(unified, workers, self.e_ref.get().strip()), encoding="utf-8")
        self.status.configure(text="تم توليد الملف")
        messagebox.showinfo("تم", f"تم توليد الملف بنجاح:\n{path}")

def main():
    App().mainloop()
