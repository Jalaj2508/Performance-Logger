from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
from flask import send_file
import csv
import os
from fpdf import FPDF
from reportlab.pdfgen import canvas
from io import BytesIO
import pdfkit
from flask import make_response
import mysql 

app = Flask(__name__)
DB = 'database/compressor.db'

# Initialize DB (only first time)
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT,
        temperature REAL,
        pressure REAL,
        noise REAL,
        tester TEXT,
        result TEXT,
        date TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tests ORDER BY date DESC")
    data = c.fetchall()
    conn.close()
    return render_template("index.html", tests=data)

@app.route('/add', methods=['GET', 'POST'])
def add_test():
    if request.method == 'POST':
        model = request.form['model']
        temperature = float(request.form['temperature'])
        pressure = float(request.form['pressure'])
        noise = float(request.form['noise'])
        tester = request.form['tester']
        result = request.form['result']
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO tests (model, temperature, pressure, noise, tester, result, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (model, temperature, pressure, noise, tester, result, date))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template("add_test.html")

@app.route('/export/csv')
def export_csv():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tests")
    data = c.fetchall()
    conn.close()

    filename = "exports/tests_export.csv"
    os.makedirs("exports", exist_ok=True)
    with open(filename, "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Model', 'Temperature', 'Pressure', 'Noise', 'Tester', 'Result', 'Date'])
        writer.writerows(data)

    return send_file(filename, as_attachment=True)

@app.route('/export/pdf')
def export_pdf():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tests")
    data = c.fetchall()
    conn.close()

    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, "Compressor Test Report", ln=True, align='C')

    col_widths = [10, 30, 30, 30, 30, 30, 20, 50]
    headers = ['ID', 'Model', 'Temperature', 'Pressure', 'Noise', 'Tester', 'Result', 'Date']

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1)

    pdf.ln()
    for row in data:
        for i, item in enumerate(row):
            pdf.cell(col_widths[i], 10, str(item), border=1)
        pdf.ln()

    os.makedirs("exports", exist_ok=True)
    filename = "exports/tests_export.pdf"
    pdf.output(filename)

    return send_file(filename, as_attachment=True)

@app.route('/bill/<int:test_id>')
def view_bill(test_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tests WHERE id = ?", (test_id,))
    test = c.fetchone()
    conn.close()
    return render_template('bill.html', test=test)

@app.route('/bill/<int:test_id>/pdf')
def download_pdf(test_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tests WHERE id = ?", (test_id,))
    test = c.fetchone()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 12)
    p.drawString(200, 800, "Compressor Test Report")
    
    fields = ["ID", "Model", "Temperature", "Pressure", "Noise", "Tester", "Result", "Date"]
    y = 760
    for i in range(len(fields)):
        p.drawString(100, y, f"{fields[i]}: {test[i]}")
        y -= 20

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"test_{test_id}_bill.pdf", mimetype='application/pdf')

@app.route('/view_bill/<int:test_id>')
def view_bill(test_id):
    # Fetch test details from DB using test_id
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
    test = cur.fetchone()
    cur.close()

    if not test:
        return "Test not found", 404

    # Sample static details – replace with your patient/user data
    bill_data = {
        'company_name': 'CareLab Diagnostics',
        'company_msg': 'Precision in Every Report',
        'invoice_no': f'INV-{test_id}',
        'invoice_date': datetime.now().strftime("%d-%m-%Y"),
        'name': 'Patient Name',
        'address': 'Patient Address',
        'items': [
            {
                'sno': 1,
                'description': test[1],  # assuming test[1] is test name
                'qty': 1,
                'rate': test[2],         # assuming test[2] is cost
                'amount': test[2]
            }
        ],
        'total': test[2],
        'amount_words': 'One Thousand Rupees Only',
        'terms': 'Reports delivered digitally. No refunds.',
    }

    return render_template('invoice.html', data=bill_data)

@app.route('/download_pdf/<int:test_id>')
def download_pdf(test_id):
    rendered = view_bill(test_id).data.decode("utf-8")
    pdf = pdfkit.from_string(rendered, False)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Invoice_{test_id}.pdf'
    return response


if __name__ == '__main__':
    app.run(debug=True)
