from flask import Flask, g, render_template, request, url_for, redirect
import os
from os.path import join, dirname, realpath
import sqlite3
import pandas as pd

app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = 'static/files'
app.config['UPLOAD_FOLDER'] =  UPLOAD_FOLDER

@app.route("/")
def main():
    return render_template('main.html')

# Get the uploaded files
@app.route("/submit/")
def submit():
    return render_template('submit.html')

@app.route("/submit/", methods=["POST"])
def upload_file():
    # get the submitted info
    name = request.form['name']
    uploaded_file = request.files['file']
    # REST NEEDS MODIFICATION BASED ON STORAGE ARCHITECTURE
    if uploaded_file.filename != '':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
        # set the file path
        uploaded_file.save(file_path)
        # save the file
    if request.form['action'] == 'submit':
        return redirect(url_for('submit'))
    else:
        return redirect(url_for('blend'))

@app.route("/insights/")
def insights():
    return render_template('insights.html',
                           name1=request.args.get('name1'),
                           name2=request.args.get('name2'))

@app.route("/blend/")
def blend():
    return render_template('blend.html')

@app.route("/blend/", methods=["POST"])
def create_blend():
    name1 = request.form['name1']
    name2 = request.form['name2']
    return redirect(url_for('insights', name1=name1, name2=name2))


# Database Organization
def get_user(): 
    """
    Creates a SQLite table named after each user 
    with their viewing history from the uploaded csv:
    
    string Date for date the title was watched.
    string Title for the title name.
    """
    # get username
    username = request.form['name'] 
    try:# return database if exists
          return g.users_db   
    except:
        # connect to SQLite
          g.users_db = sqlite3.connect("users.db") 
          cursor = g.users_db.cursor()           
        # create table and name it after user
          query = """
            CREATE TABLE IF NOT EXISTS {} (
            Title nvarchar(50),
            Date nvarchar(10),
            );
            """.format(username)    
          cursor.execute(query)
          g.user_db.commit()    
          return g.users_db

def insert_history(request):
    """
    Method to store user history. 
    Fetches information from the uploaded user csv and 
    uploads their history into their SQL table.
    """
    # connect to database
    conn = get_user()                     
    username = request.form['name'] 
    # import CSV
    uploaded_file = request.files['file']
    data = pd.read_csv(uploaded_file)   
    df = pd.DataFrame(data)
    # insert DataFrame to table
    cursor = conn.cursor()
    for row in df.itertuples():
       cursor.execute("""
            INSERT INTO {} (Title, Date)
            VALUES ({},{});
            """.format(username, row.Title, row.Date)
            )
    conn.commit()   # save history
    conn.close()    # close connection