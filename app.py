from flask import Flask, render_template, request, redirect, url_for, session
import numpy as np

from markowitz import markowitz_optimize
from realtime_market import get_market_data

app = Flask(__name__)
app.secret_key = "sicuan"


# ======================
# FINANCIAL FUNCTIONS
# ======================

def future_value_lump_sum(pv, r, n):
    return pv * ((1 + r) ** n)


def future_value_annuity(pmt, r, n):
    if r == 0:
        return pmt * n
    return pmt * (((1 + r) ** n - 1) / r)


# ======================
# NAV PAGES
# ======================

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ======================
# START FORM (DATA USER)
# ======================

@app.route("/start", methods=["GET", "POST"])
def start():
    if request.method == "POST":
        session["user"] = {
            "nama": request.form.get("nama"),
            "nohp": request.form.get("nohp"),
            "email": request.form.get("email")
        }
        return redirect(url_for("profil_form"))

    return render_template("form.html")


# ======================
# PROFIL RISIKO
# ======================

@app.route("/profil", methods=["GET", "POST"])
def profil_form():
    if request.method == "POST":

        total = 0
        for i in range(1, 9):
            total += int(request.form.get(f"q{i}", 0))

        if total <= 14:
            profil = "konservatif"
        elif total <= 21:
            profil = "moderat"
        else:
            profil = "agresif"

        session["profil"] = profil
        return redirect(url_for("advisor"))

    return render_template("profil_form.html")


# ======================
# ADVISOR (INPUT DANA + ENGINE)
# ======================

@app.route("/advisor", methods=["GET", "POST"])
def advisor():
    if request.method == "POST":

        # ---------- INPUT USER ----------
        tujuan = request.form.get("tujuan")
        dana_awal = int(request.form.get("dana_awal"))
        target = int(request.form.get("harga"))

        waktu_angka = int(request.form.get("waktu_angka"))
        waktu_satuan = request.form.get("waktu_satuan")
        bulan = waktu_angka * 12 if waktu_satuan == "tahun" else waktu_angka

        profil = session.get("profil", "moderat")

        # ---------- RETURN + INFLASI ----------
        inflasi_bulanan = 0.003  # 0.3%

        if profil == "konservatif":
            r = 0.008
        elif profil == "moderat":
            r = 0.015
        else:
            r = 0.03

        # ---------- KEBUTUHAN NABUNG ----------
        kebutuhan_per_bulan = max(0, (target - dana_awal) // max(1, bulan))

        # ---------- FUTURE VALUE ----------
        fv_lump = future_value_lump_sum(dana_awal, r, bulan)
        fv_annuity = future_value_annuity(kebutuhan_per_bulan, r, bulan)
        fv_total = fv_lump + fv_annuity

        realistis = fv_total >= target

        # ---------- MARKOWITZ ----------
        returns = np.array([0.15, 0.10, 0.05])
        cov = np.array([
            [0.10, 0.02, 0.01],
            [0.02, 0.08, 0.01],
            [0.01, 0.01, 0.03]
        ])

        weights = markowitz_optimize(returns, cov)

        alokasi = [
            ("Saham Growth", round(weights[0] * 100, 1), int(dana_awal * weights[0])),
            ("Bluechip", round(weights[1] * 100, 1), int(dana_awal * weights[1])),
            ("Obligasi", round(weights[2] * 100, 1), int(dana_awal * weights[2]))
        ]

        # ---------- MARKET DATA (SUPER AMAN) ----------
        raw_market = get_market_data()

        kode_saham_map = {
            "I": "IHSG",
            "B": "BBCA",
            "T": "TLKM"
        }

        tren_map = {
            "H": "Naik (Uptrend)",
            "B": "Sideways",
            "L": "Turun (Downtrend)"
        }

        keyakinan_map = {
            "T": "Tinggi",
            "S": "Sedang",
            "R": "Rendah"
        }

        market = []

        for item in raw_market:
            kode = item[0] if len(item) > 0 else "-"
            tren = item[1] if len(item) > 1 else "-"
            keyakinan = item[2] if len(item) > 2 else "-"

            market.append((
                kode_saham_map.get(kode, kode),
                tren_map.get(tren, tren),
                keyakinan_map.get(keyakinan, keyakinan)
            ))

        # ---------- RESULT OBJECT ----------
        result = {
            "tujuan": tujuan,
            "dana": dana_awal,
            "target": target,
            "bulan": bulan,
            "profil": profil.capitalize(),

            "return_bulanan": round(r * 100, 2),
            "inflasi": round(inflasi_bulanan * 100, 2),

            "kebutuhan_per_bulan": kebutuhan_per_bulan,
            "realistis": realistis,

            "alokasi": alokasi,
            "market": market
        }

        return render_template("result.html", r=result)

    return render_template("advisor.html")


# ======================
# ADMIN
# ======================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")

        if user == "admin" and pw == "admin123":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin.html", error="Login gagal")

    return render_template("admin.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    return render_template("admin_dashboard.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(debug=True, port=10000)
