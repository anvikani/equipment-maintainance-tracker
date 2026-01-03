from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    location = db.Column(db.String(120))
    status = db.Column(db.String(50), default='Working')
    last_maintenance = db.Column(db.Date, default=datetime.utcnow)

class MaintenanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'))
    date = db.Column(db.Date, default=datetime.utcnow)
    notes = db.Column(db.String(200))
    cost = db.Column(db.Float, default=0.0)

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    assets = Asset.query.all()
    return render_template('index.html', assets=assets)

@app.route('/add_asset', methods=['GET', 'POST'])
def add_asset():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        status = request.form['status'] 
        asset = Asset(name=name, location=location, status=status)
        db.session.add(asset)
        db.session.commit()
        return redirect('/')
    return render_template('add_asset.html')

@app.route('/add_log/<int:asset_id>', methods=['GET', 'POST'])
def add_log(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if request.method == 'POST':
        notes = request.form['notes']
        cost = float(request.form['cost'] or 0)
        date_str = request.form['date']
        if date_str:
            log_date = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            log_date = datetime.utcnow()
        log = MaintenanceLog(asset_id=asset_id, notes=notes, cost=cost, date=log_date)
        asset.last_maintenance = log_date
        db.session.add(log)
        db.session.commit()
        return redirect('/')
    return render_template('add_log.html', asset=asset)

@app.route('/view_logs/<int:asset_id>')
def view_logs(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    logs = MaintenanceLog.query.filter_by(asset_id=asset_id).all()
    return render_template('index.html', assets=[asset], logs=logs, show_logs=True)

@app.route('/report/<int:asset_id>')
def generate_report(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    logs = MaintenanceLog.query.filter_by(asset_id=asset_id).all()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height-50, f"Maintenance Report for {asset.name}")

    c.setFont("Helvetica", 12)
    c.drawString(50, height-80, f"Location: {asset.location}")
    c.drawString(50, height-100, f"Status: {asset.status}")
    c.drawString(50, height-120, f"Last Maintenance: {asset.last_maintenance.strftime('%Y-%m-%d')}")

    y = height - 160
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Date")
    c.drawString(150, y, "Notes")
    c.drawString(400, y, "Cost")
    y -= 20

    c.setFont("Helvetica", 12)
    total_cost = 0
    for log in logs:
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, log.date.strftime('%Y-%m-%d'))
        c.drawString(150, y, log.notes[:40])
        c.drawString(400, y, f"{log.cost}")
        total_cost += log.cost
        y -= 20


    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Total Maintenance Cost: {total_cost}")

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{asset.name}_report.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

