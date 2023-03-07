from flask import Flask, g, render_template, request, url_for, redirect
import os
from os.path import join, dirname, realpath
import sqlite3

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