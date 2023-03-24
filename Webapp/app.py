from flask import Flask, g, render_template, request, url_for, redirect
import os
from os.path import join, dirname, realpath
import sqlite3
import pandas as pd
import json
import plotly
import plotly.express as px

app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = 'static/files'
app.config['UPLOAD_FOLDER'] =  UPLOAD_FOLDER

DB_NAME = 'static/data/users.db'

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
    uploaded_file = request.files['file']
    
    if uploaded_file.filename != '':
        insert_history(request)

    if request.form['action'] == 'submit':
        return redirect(url_for('submit'))
    else:
        return redirect(url_for('blend'))

@app.route("/insights/")
def insights():
    # CALL ALL PROCESSING & PLOTTING FUNCTIONS HERE
    # 1. df1 = get_history(name1) & df2 = get_history(name2)
    # 2. df1 = netflix_merge(df1) & df2 = netflix_merge(df2)
    # 3. call all individual-info plot functions
    # 4. overlap_merge(df1, df2) [on the netflix_merge datasets]
    # 5. call all common-info plot functions
    # https://towardsdatascience.com/web-visualization-with-plotly-and-flask-3660abf9c946

    name1=request.args.get('name1')
    name2=request.args.get('name2')
    df1 = get_history(name1)
    df2 = get_history(name2)
    df1 = netflix_merge(df1)
    df2 = netflix_merge(df2)

    fig = most_watched_tv(df1)
    graphJSON_tv1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig = most_watched_tv(df2)
    graphJSON_tv2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig = total_minutes(df1)
    graphJSON_minutes1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig = total_minutes(df2)
    graphJSON_minutes2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    # df = overlap_merge(df1, df2)
    # total_minutes(df)

    return render_template('insights.html',
                           name1=name1,
                           name2=name2,
                           graphJSON_tv1 = graphJSON_tv1,
                           graphJSON_tv2 = graphJSON_tv2,
                           graphJSON_minutes1 = graphJSON_minutes1,
                           graphJSON_minutes2 = graphJSON_minutes2)

@app.route("/blend/")
def blend():
    return render_template('blend.html')

@app.route("/blend/", methods=["POST"])
def create_blend():
    name1 = request.form['name1']
    name2 = request.form['name2']
    return redirect(url_for('insights', name1=name1, name2=name2))

# Database Organization
def get_user(username): 
    """
    Creates a SQLite table named after each user 
    with their viewing history from the uploaded csv:
    
    string Date for date the title was watched.
    string Title for the title name.
    """
    try:
        return g.users_db
    # if not, create database
    except:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cmd = f"""CREATE TABLE IF NOT EXISTS {username} (
            Title nvarchar(255),
            Date nvarchar(10)
            );
            """
            cur.execute(cmd)
            conn.commit()
            g.users_db = conn
            return g.users_db

def insert_history(request):
    """
    Method to store user history. 
    Fetches information from the uploaded user csv and 
    uploads their history into their SQL table.
    """
    # connect to database
    username = request.form['name'] 
    conn = get_user(username=username)                    
    # import CSV
    uploaded_file = request.files['file']
    data = pd.read_csv(uploaded_file)   
    # insert DataFrame to table
    data.to_sql(username, conn, index = False, if_exists='replace')
    conn.commit()   # save history
    conn.close()    # close connection

def get_history(username):
    '''
    Function that gets users history and returns their cleaned dataframe
    '''
    conn = get_user(username=username)
    cmd = """SELECT * from {}""".format(username)
    df = pd.read_sql(cmd, conn)

    # CALL CLEAN_DATA
    df = clean_watch_history(df)
    return df

def clean_watch_history(df):
    '''
    Function that cleans a given users watch history data
    Input: dataframe
    Output: (cleaned) dataframe
    '''
    df = df.rename(columns = {"Title": "History"})
    df['Date'] = pd.to_datetime(df['Date'])
    df['Day']= df['Date'].dt.day
    df['Month']= df['Date'].dt.month
    df['Year']= df['Date'].dt.year
    df['Day_of_week'] = df['Date'].dt.dayofweek

    df['Title'] = df['History'].str.rsplit(': ', 2).str[0]
    df['Season'] = df['History'].str.rsplit(': ', 2).str[1]
    df['Episode'] = df['History'].str.rsplit(': ', 2).str[2]

    df['Type'] = df['Episode'].apply(lambda x : 'Movie' if (pd.isna(x)==True) else 'TV')

    tv = df[df['Type']!='Movie']
    tv['Season'] = tv['Season'].str.split().str[1]

    movies = df[df['Type']=='Movie']
    movies['Title'] = movies['History']
    movies['Season'] = None

    df = pd.concat([movies, tv], ignore_index = True)
    return df

def netflix_merge(df):
    '''
    Function that merges given watch history with netflix dataset,
    and returns merged dataset
    '''
    titles = pd.read_csv('static/data/titles.csv')
    merged = df.merge(titles, left_on = 'Title', right_on = 'title', how = 'inner')
    cols_to_drop = ['type', 'production_countries', 'imdb_id', 'age_certification', 
                    'id', 'title', 'seasons', 'tmdb_popularity']
    merged = merged.drop(cols_to_drop, axis = 1)
    return merged

def overlap_merge(df1, df2):
    '''
    Function that merges two users watch histories to find overlap
    '''
    # merge on 'History'
    dfNew = df1.merge(df2, how = 'inner', left_on = 'History', right_on = 'History', suffixes=('', '_y'))
    dfNew = dfNew.drop(dfNew.filter(regex='_y$').columns, axis=1)
    return dfNew

def most_watched_tv(df):
    '''
    Plots 10 most watched TV shows (measured in minutes) in given dataframe
    Returns a Plotly bar graph
    '''
    df = df[df['Type']=='TV']
    df = df.groupby('Title').sum()
    df = df.reset_index()
    
    df = df.sort_values(by='runtime', ascending= False)
    # extract 10 most similar shows
    df = df.head(10)
    
    fig = px.bar(data_frame= df,
             x= "runtime",
             y= "Title",
             # text= "num_shared_actors",
             labels= {"runtime": "Minutes Watched"},
             text_auto= True)
    fig.update_traces(hovertemplate='Total Watch Time: %{x} mins')
    return fig

def total_minutes(df):
    '''
    Function that plots pie chart of total minutes watched for tv vs movies
    Returns a plotly pie chart
    '''
    fig = px.pie(df, values='runtime', names='Type', hole=.5)
    fig.update_traces(hovertemplate='Total Watch Time: %{value} mins')
    return fig
