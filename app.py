from flask import Flask, redirect, render_template, request, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import gspread
import os


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///frolic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'yath' 


db = SQLAlchemy(app)

# Define basedir for Google Sheets credentials
basedir = os.path.abspath(os.path.dirname(__file__))

# Define your model
class Frolic(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(200), nullable=False)
    lname = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(320), nullable=True)
    phone = db.Column(db.String(15), nullable=False)
    wd = db.Column(db.DateTime, default=datetime.utcnow)
    msg = db.Column(db.String(1000), nullable=True)

    def __repr__(self):
        return f"<Frolic {self.fname} {self.lname} - {self.phone}>"

# --- Google Sheets Integration Functions ---
def setup_google_sheets_client():
    try:
        gc = gspread.service_account(filename=os.path.join(basedir, 'credentials.json'))
        return gc
    except Exception as e:
        raise Exception(f"Failed to authenticate with Google Sheets: {e}. "
                        "Make sure credentials.json is in your app's directory "
                        "and is correct.")

def write_to_google_sheet(gc_client, submission_object):
    try:
        spreadsheet = gc_client.open("Frolic Sales")
        worksheet = spreadsheet.sheet1

        row_data = [
            submission_object.sno if submission_object.sno else '', # Handle sno potentially being None before commit
            submission_object.fname,
            submission_object.lname,
            submission_object.email,
            submission_object.phone,
            submission_object.wd.strftime('%Y-%m-%d %H:%M:%S') if submission_object.wd else '', 
            submission_object.msg
        ]

        worksheet.append_row(row_data)
        print("Data successfully written to Google Sheet.")
    except Exception as e:
        raise Exception(f"Failed to write data to Google Sheet: {e}. "
                        "Check sheet name/permissions, and column order.")


@app.route('/')
def hello():
    return render_template('index.html')

@app.route("/submit_contact", methods=['POST']) 
def submit_contact():
    first_name = request.form['fname']
    last_name = request.form['lname']
    email = request.form['email']
    phoneno = request.form['phone']
    wedding_date_str = request.form['wedding']
    message = request.form['message']


    try:
        wedding_date = datetime.strptime(wedding_date_str, '%Y-%m-%d')
    except ValueError:
        flash("Invalid wedding date format. Please use YYYY-MM-DD.", 'danger')
        return redirect(url_for('hello'))

    new_submission = Frolic(
        fname=first_name,
        lname=last_name,
        email=email,
        phone=phoneno,
        wd=wedding_date,
        msg=message
    )

    try:
        db.session.add(new_submission)
        db.session.commit() 
        flash('Your message has been sent and saved to database!', 'success')

        try:
            gc = setup_google_sheets_client()
            write_to_google_sheet(gc, new_submission) # Pass the database object
            flash('Data also synced to Google Sheets!', 'info')
        except Exception as e:
            # Log this error but don't prevent redirecting the user
            flash(f'Failed to sync data to Google Sheets: {e}', 'warning')
            print(f"Google Sheets Error: {e}") # Crucial for debugging issues

    except Exception as e:
        db.session.rollback() # Rollback DB changes if there's a problem
        flash(f'An error occurred saving to database: {e}', 'danger')
        print(f"Database Error: {e}")

    return redirect(url_for('hello')) # Redirect back to the home page

# --- Main Application Run ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # This creates the database and tables
    app.run(debug=True)