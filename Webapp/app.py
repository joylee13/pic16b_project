from flask import Flask, g, render_template, request, url_for, redirect
import os
from os.path import join, dirname, realpath
import sqlite3
import pandas as pd
import json
import plotly
import plotly.express as px
import numpy as np

app = Flask(__name__)

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
    name1=request.args.get('name1')
    name2=request.args.get('name2')
    df_1 = get_history(name1)
    df_2 = get_history(name2)
    df1 = netflix_merge(df_1)
    df2 = netflix_merge(df_2)

    metadata = 'static/data/metadata_updated.json'
    glmer_scores = 'static/data/glmer.csv'
    user_history1 = df_1
    user_history2 = df_2
    movie_lens_dataset = 'static/data/titles_movielens.csv'
    master_matrix = 'static/data/masterlist_ml_matrix.csv'
    recommend_output = generate_two_user_recommendation(metadata, glmer_scores, user_history1, user_history2, movie_lens_dataset, master_matrix)
    
    list_recommended_titles = recommend_output[2]
    
    fig = total_minutes(df1)
    graphJSON_minutes1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig = total_minutes(df2)
    graphJSON_minutes2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig = top_tv(df1)
    graphJSON_tv1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig = top_tv(df2)
    graphJSON_tv2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig = top_actors(df1)
    graphJSON_actors1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig = top_actors(df2)
    graphJSON_actors2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig, top1 = top_genres(df1)
    graphJSON_genres1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig, top2 = top_genres(df2)
    graphJSON_genres2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    df = overlap_merge(df1, df2)

    fig = top_tv(df)
    graphJSON_tv = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig = top_actors(df)
    graphJSON_actors = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig, top_genre = top_genres(df)
    graphJSON_genre = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('insights.html',
                           name1=name1,
                           name2=name2,
                           graphJSON_tv1 = graphJSON_tv1,
                           graphJSON_tv2 = graphJSON_tv2,
                           graphJSON_minutes1 = graphJSON_minutes1,
                           graphJSON_minutes2 = graphJSON_minutes2,
                           graphJSON_actors1 = graphJSON_actors1,
                           graphJSON_actors2 = graphJSON_actors2,
                           graphJSON_genres1 = graphJSON_genres1,
                           graphJSON_genres2 = graphJSON_genres2,
                           graphJSON_tv = graphJSON_tv,
                           graphJSON_actors = graphJSON_actors,
                           graphJSON_genre = graphJSON_genre,
                           top_genre = top_genre, 
                           list_recommended_titles=list_recommended_titles
                           )

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
                    'title', 'seasons', 'tmdb_popularity']
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

def top_tv(df):
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
             text_auto= True,
             width = 600,
             height = 400)
    fig.update_traces(hovertemplate='Total Watch Time: %{x} mins')
    return fig

def total_minutes(df):
    '''
    Function that plots pie chart of total minutes watched for tv vs movies
    Returns a plotly pie chart
    '''
    fig = px.pie(df, values='runtime', names='Type', hole=.5, width=600, height=400)
    fig.update_traces(hovertemplate='Total Watch Time: %{value} mins')
    return fig

def top_genres(df):
    '''
    Plots breakdown of genres (measured in minutes) 
    Returns a Plotly bar graph as well as the top genre
    '''
    df['genres'] = df['genres'].apply(lambda x: x.replace('\'', ''))
    df['genres'] = df['genres'].apply(lambda x: x.replace('[', ''))
    df['genres'] = df['genres'].apply(lambda x: x.replace(']', ''))
    df['genres'] = df['genres'].apply(lambda x: x.replace(' ', ''))

    temp = df['genres'].str.split(',', expand = True)
    genre_col_list = ['genre_' + str(i) for i in range(len(temp.columns))]
    temp.columns = genre_col_list
    df = pd.concat([df, temp], axis = 1)

    s = pd.Series()
    for i in genre_col_list:
        s = s.add(df.groupby(i).sum()['runtime'], fill_value=0)
    
    top_genre = s.idxmax()
    df = pd.DataFrame(s.reset_index())

    fig = px.pie(df, values=0, names='index', hole=.5, height=400, width=600)
    fig.update_traces(hovertemplate='Number of Minutes Watched: %{value}')
    return fig, top_genre

def top_actors(df):
    '''
    Plots 10 most frequently appearing actors
    Returns a Plotly bar graph'''
    cast = pd.read_csv("static/data/credits.csv")
    cast = cast[cast['role']=='ACTOR']
    df = df.merge(cast, how='left', left_on='id', right_on='id')

    df = df.groupby('name').count()['Title'].reset_index()
    df = df.sort_values(by='Title', ascending= False)
    df = df.head(10)

    fig = px.bar(data_frame= df,
                x= "Title",
                y= "name",
                # text= "num_shared_actors",
                labels= {"Title": "Number of Appearances"},
                text_auto= True,
                height=400,
                width=600)
    return fig



def generate_item_id(df_user, movie_lens_csv):
    '''
    For a given user's user_history.csv file, generates a list of movie_ids
    as per the Movie Lens's dataset

    inputs:
        - df_user: user watch history df after netflix merge func
        - movie_lens_csv: the path to the csv file containing the Movie Lens dataset

    outputs:
        - item_ids: the list of all item_ids as desired
    '''
    df_movies = df_user[df_user.Type != 'TV']
    df_movies = pd.DataFrame(df_movies,columns = ['History', 'release_year'])
    df_mltitles = pd.read_csv(movie_lens_csv)
    df_merge = df_mltitles[df_mltitles.movie_title.isin(df_movies.History)]
    df_merge.drop(columns = ['Unnamed: 0'], inplace = True)
    df_merge.rename(columns = {'year': 'release_year'}, inplace = True)
    df_movies.rename(columns = {'History': 'movie_title'}, inplace = True)

    def to_int(x):
        try:
            return int(x)
        except ValueError:
            return np.nan
    df_merge['release_year'] = df_merge['release_year'].apply(to_int)
    df_output = pd.merge(df_movies,df_merge, how = 'inner', on = ['movie_title', 'release_year']).sort_values(by = 'movie_title')

    item_ids = df_output['item_id'].values
    item_ids = np.array(item_ids)
    return item_ids


def collect_master_df(glmer_scores):
    '''
    collects the master list of all glmer_scores as per the study referenced in this project and 
    returns as a df along with a list of the unique titles
    
    inputs:
        - glmer_scores: file path of where the glmer scores file is located
    '''
    df = pd.read_csv(glmer_scores)
    titles = df['item_id'].unique()
    return df, titles

def read_metadata(metadata):
    lines = []
    for line in open(metadata, 'r'):
        lines.append(json.loads(line))
    return lines

def generate_user_watch_history(lines, titles, user_data = 'random', n = 20):
    '''
    Generates a dictionary containing the movie id titles along with their names

    inputs:
        - lines: a list of all lines in the metadata json file
        - titles: a list of all unique titles in the scores data
        - user_data: the item_ids of all user watched movies. Generates n random titles if not provided
        - n: the number of titles to generate

    outputs:
        - sample_user: generates the desired dict
    '''
    if type(user_data) == str:
        t = np.random.choice(titles,n)
    else:
        t = user_data
    sample_user = {}
    for line in lines:
        if line['item_id'] in t:
            sample_user[line['item_id']] = line['title']
    return sample_user


def generate_user_history_tag(sample_user, df):
    '''
    Generates a matrix of an aggregation of tag scores for each title watched by a user
    along with a list of all user watched titles for which scores do not exist

    inputs:
        - sample_user: list of all movie titles watched by a user
        - df: the dataframe of tag_scores

    outputs:
        - errors: list of all user watched titles for which scores do not exist
        - mat: the desired matrix
    '''
    sample_user_matrix = []
    errors = []
    for movie in sample_user.keys():
        #skip if for some reason the movie does not contain all labels
        if len(df[df.item_id == movie]) != 1084:
            errors.append(movie)
        #if the movie contains all label values, obtain the tag vector from the main df
        else:
            matrix = list(df[df.item_id == movie].score.values)
            sample_user_matrix.append(matrix)

    #turning the list of lists into a matrix as a 2D array
    mat = np.array(sample_user_matrix)

    return errors,mat


def generate_user_pref_vector(mat, f = '2-norm'):
    '''
    Generates a user preference for each label as a vector, aggregating on the matrix
    created by generate_user_history_tag() with function f applied

    inputs:
        - mat: the user matrix generated by generate_user_history_tag()
        - f: the function to be applied to 

    outputs:
        - aggroot/agg: the preference vector after applying the desired function
    '''
    if f == '2-norm':
        matsq = mat**2
        agg = np.average(matsq, axis = 0)
        aggroot = agg**0.5

        return aggroot
    
    else:
        agg = []

        for col in mat.T:
            val = f(col)
            agg.append(val)
        
        return agg
    
def generate_master_matrix(df, titles):
    '''
    Generates the master matrix - a transformation of the dataframe generated 
    by collect_master_df(). Not used if instead the master matrix is stored separately

    inputs:
        - df: the dataframe of label scores
        - titles: the list of movie ids

    outputs:
        - master_mat: the desired matrix
    '''
    master_mat = []
    for movie in titles:
        if len(df[df.item_id == movie]) != 1084:
            print(f'error {movie}')

        else:
            matrix = list(df[df.item_id == movie].score.values)
            master_mat.append(matrix)
    master_mat = np.array(master_mat)

    return master_mat


def generate_user_movie_interest(master_mat, user_tag_interest, g = '2-norm'):
    '''
    Generates an interest rating for each movie for a given user

    inputs:
        - master_mat: the master mat either generated by generate_master_matrix() or stored as a txt file
        - user_tag_interest: the user preference vector generated by generate_user_pref_vector()
        - g: the desired aggregation function. defaults to the 2-norm function (euclid distance)

    outputs:
        - dist: a list contiaining the preferences for each movie in order of the movie_items
    '''
    if g == '2-norm':
        rows, _ = master_mat.shape
        dist = []
        for r in range(rows):
            d = np.linalg.norm(user_tag_interest-master_mat[r])
            dist.append(d)
        return dist
    
    else:
        dist = []
        for i in master_mat:
            val = g(user_tag_interest,i)
            dist.append(val)
        return dist


def generate_recommendation(dists, lines, titles, n_recs = 10, users = 1):
    '''
    Generates movie recommendation after all necessary components collected, for one or two user

    inputs:
        - dists: an array containing the movie preference vectors for each user
        - lines: the metadata entries stored as lines
        - titles: a list of all movie ids
        - n_recs: desired number of movies to be recommended
        - users: whether recommendations are desired for 1 or two users

    output:
        - a dataframe containing the top n recommended movies, a score for how strongly 
          the movie is recommended, and other cols
    '''
    if users == 1:
        dfresult = pd.DataFrame(titles, columns = ['movie_id'])
        dfresult['score1'] = dists[0]
        dfresult = dfresult.sort_values(by = ['score1'], ascending = False)
        dfrecommend = dfresult[0:n_recs]
        
        movie_titles = {}
        for line in lines:
            if line['item_id'] in dfrecommend.movie_id.values:

                movie_titles[line['item_id']] = line['title']
        
        dfrecommend['movie_title'] = dfrecommend['movie_id'].map(movie_titles)
        dfrecommend.reset_index(inplace = True)
        return dfrecommend
    
    if users == 2:
        dfresult = pd.DataFrame(titles, columns = ['movie_id'])
        dfresult['score1'] = dists[0]
        dfresult['score2'] = dists[1]

        dfresult['average'] = (dfresult['score1'] + dfresult['score2'])/2
        dfresult['dev'] = ((dfresult['score1']-dfresult['average'])**2) + ((dfresult['score2'] - dfresult['average'])**2)
        dfresult = dfresult.sort_values(by = ['average'], ascending = False)

        dfrecommend = dfresult[0:2*n_recs]
        dfrecommend = dfrecommend.sort_values(by= ['dev'], ascending = True)
        dfrecommend = dfrecommend[0:n_recs]

        movie_titles = {}
        for line in lines:
            if line['item_id'] in dfrecommend.movie_id.values:

                movie_titles[line['item_id']] = line['title']
        
        dfrecommend['movie_title'] = dfrecommend['movie_id'].map(movie_titles)
        dfrecommend.reset_index(inplace = True)
        return dfrecommend
    

def f(a):
    '''
    An implementation of a desired aggregation function. Used to aggregate preference labels

    inputs:
        - a: an array/list containing all values to be aggregated
    
    outputs:
        - result: a final value after aggregation
    '''
    result = 0
    for val in a:
        result+= val**0.5
    
    result = result/np.size(a)
    result = result**2
    return result

def generate_two_user_recommendation(metadata, glmer_scores, user_history1, user_history2, movie_lens_dataset, master_matrix):
    '''
    Generates recommendations for two users based on their watch history

    inputs:
        - metadata: the metadata file from the movielens dataset
        - glmer_scores: the label scores from the ml dataset
        - user_history1: user 1 history df
        - user_history2: user 2 history df
        - movie_lens_dataset: the path for the movie_lens_dataset
        - master_matrix: the array of the master_matrix

    output:
        - errors: a list of movies watched by users that do not have label scores (entry 0 is for user1, entry 1 is for user2)
        - dfrecommend: a dataframe of recommended movie, with a metric score for how much user 1 prefers, user 2 prefers, and
            how strongly recommended, along with other column information
        - recommend: an array containing the movies recommended
    '''
    master_mat = np.loadtxt(master_matrix, delimiter = ',')
    df, titles = collect_master_df(glmer_scores)
    lines = read_metadata(metadata)
    
    sample_user1 = generate_item_id(user_history1, movie_lens_dataset)
    user1 = generate_user_watch_history(lines, titles, sample_user1)
    errors_user1, mat1 = generate_user_history_tag(user1,df)
    agg1 = generate_user_pref_vector(mat1, f = f)
    dist1 = generate_user_movie_interest(master_mat, agg1)

    sample_user2 = generate_item_id(user_history2, movie_lens_dataset)
    user2 = generate_user_watch_history(lines, titles, sample_user2)
    errors_user2, mat2 = generate_user_history_tag(user2,df)
    agg2 = generate_user_pref_vector(mat2, f = f)
    dist2 = generate_user_movie_interest(master_mat, agg2)

    dfrecommend= generate_recommendation([dist1, dist2], lines, titles, n_recs = 20, users = 2)

    errors = [errors_user1, errors_user2]
    recommend = dfrecommend['movie_title'].values
    return errors, dfrecommend, recommend


#######################
