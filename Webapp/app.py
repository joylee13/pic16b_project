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
    uploaded_file1 = request.files['file1']
    uploaded_file2 = request.files['file2']
    # REST NEEDS MODIFICATION BASED ON STORAGE ARCHITECTURE
    if uploaded_file1.filename != '':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file1.filename)
        # set the file path
        uploaded_file1.save(file_path)
        # save the file
    if uploaded_file2.filename != '':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file2.filename)
        # set the file path
        uploaded_file2.save(file_path)
        # save the file
    return redirect(url_for('insights', name = name))

@app.route("/insights/<name>")
def insights(name):
    return render_template('insights.html', name = name)