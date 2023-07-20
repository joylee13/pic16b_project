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

    df1_movies = get_movie_list(df1)
    df2_movies = get_movie_list(df2)

    df1_top_movies = get_top_movies(df1_movies)
    df2_top_movies = get_top_movies(df2_movies)

    df1_movie = get_tv_list(df1, "MOVIE")
    df2_movie = get_tv_list(df2, "MOVIE")

    netflix_recs1_df = get_tv_recs(df1_movie, "MOVIE")
    netflix_recs1 = list(netflix_recs1_df['title'])
    netflix_recs2_df = get_tv_recs(df2_movie, "MOVIE")
    netflix_recs2 = list(netflix_recs2_df['title'])

    not_netflix_recs1_df = get_not_netflix_recs(df1_top_movies)
    not_netflix_recs1 = list(not_netflix_recs1_df['title'])
    not_netflix_recs2_df = get_not_netflix_recs(df2_top_movies)
    not_netflix_recs2 = list(not_netflix_recs2_df['title'])

    # common_movies = get_common_movies(df1_top_movies, df2_top_movies)

    df1_tv = get_tv_list(df1, "SHOW")
    df2_tv = get_tv_list(df2, "SHOW")

    tv_recs1_df = get_tv_recs(df1_tv, "SHOW")
    tv_recs1 = list(tv_recs1_df['title'])
    tv_recs2_df = get_tv_recs(df2_tv, "SHOW")
    tv_recs2 = list(tv_recs2_df['title'])

    # common_tv = get_common_tv(tv_recs1, tv_recs2)
    
    fig = total_minutes(df1)
    graphJSON_minutes1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig = total_minutes(df2)
    graphJSON_minutes2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig = top_tv(df1)
    graphJSON_tv1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig = top_tv(df2)
    graphJSON_tv2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig, top_actors1 = top_actors(df1)
    graphJSON_actors1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig, top_actors2 = top_actors(df2)
    graphJSON_actors2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    fig, top_genres1 = top_genres(df1)
    graphJSON_genres1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig, top_genres2 = top_genres(df2)
    graphJSON_genres2 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    # shouldn't overlap df. Instead take overlap of topX
    top_genre = blend_overlap(top_genres1, top_genres2)
    top_actor = blend_overlap(top_actors1, top_actors2)
    common_tv = blend_overlap(tv_recs1_df, tv_recs2_df)
    common_netflix = blend_overlap(netflix_recs1_df, netflix_recs2_df)
    common_movies = blend_overlap(not_netflix_recs1_df, not_netflix_recs2_df)

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
                           top_genres = top_genre,
                           top_actors = top_actor,
                           netflix_recs1 = netflix_recs1,
                           netflix_recs2 = netflix_recs2,
                           not_netflix_recs1 = not_netflix_recs1,
                           not_netflix_recs2 = not_netflix_recs2,
                           common_netflix = common_netflix,
                           tv_recs1 = tv_recs1,
                           tv_recs2 = tv_recs2,
                           common_tv = common_tv,
                           common_movies = common_movies
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
    cols_to_drop = ['production_countries', 'imdb_id', 'age_certification', 
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
    
    df = df.sort_values(by='runtime', ascending= False)[:10]

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
    
    df = pd.DataFrame(s.reset_index())
    top = df.sort_values(by=0, ascending=False)[:10]

    fig = px.pie(df, values=0, names='index', hole=.5, height=400, width=600)
    fig.update_traces(hovertemplate='Number of Minutes Watched: %{value}')
    return fig, top

def top_actors(df):
    '''
    Plots 10 most frequently appearing actors
    Returns a Plotly bar graph'''
    cast = pd.read_csv("static/data/credits.csv")
    cast = cast[cast['role']=='ACTOR']
    df = df.merge(cast, how='left', left_on='id', right_on='id')

    df = df.groupby('name').count()['Title'].reset_index()
    df = df.sort_values(by='Title', ascending= False)

    fig = px.bar(data_frame= df[:10],
                x= "Title",
                y= "name",
                # text= "num_shared_actors",
                labels= {"Title": "Number of Appearances"},
                text_auto= True,
                height=400,
                width=600)
    return fig, df

def blend_overlap(df1, df2):
    on = df1.columns[0]
    val = str(df1.columns[1])
    val_x = val+'_x'
    val_y = val+'_y'

    df = pd.merge(df1, df2, how='inner', on=on)
    df['score'] = (df[val_x] + df[val_y])/2
    df = df.sort_values(by='score', ascending=False)
    df = df[df[val_x]!=0]
    return list(df[on])

##########

# create a function that takes in movie title as input and returns a list of the most similar movies
def get_recommendations(title, n, cosine_sim, df_movies):
    
    # get the index of the movie that matches the title
    movie_index = df_movies[df_movies.title==title].new_id.values[0]
    
    # get the pairwsie similarity scores of all movies with that movie and sort the movies based on the similarity scores
    sim_scores_all = sorted(list(enumerate(cosine_sim[movie_index])), key=lambda x: x[1], reverse=True)
    
    # checks if recommendations are limited
    if n > 0:
        sim_scores_all = sim_scores_all[1:n+1]
        
    # get the movie indices of the top similar movies
    movie_indices = [i[0] for i in sim_scores_all]
    scores = [i[1] for i in sim_scores_all]
    
    # return the top n most similar movies from the movies df
    top_titles_df = pd.DataFrame(df_movies.iloc[movie_indices]['title'])
    top_titles_df['sim_scores'] = scores
    top_titles_df['ranking'] = range(1, len(top_titles_df) + 1)
    
    return top_titles_df, sim_scores_all

def get_movie_list(df):
    return list(df[df['type'] == "MOVIE"]['Title'])

def get_top_movies(movie_list):
    similarity = np.load('static/data/movies_similarity.npy')
    df_movies = pd.read_csv('static/data/movies.csv')

    user_scores = pd.DataFrame(df_movies['title'])
    user_scores['sim_scores'] = 0.0

    # top number of scores to be considered for each movie
    number_of_recommendations = 10000
    for movie_name in movie_list:
        try:
            top_titles_df, _ = get_recommendations(movie_name, number_of_recommendations,
                                                similarity, df_movies)
        except:
            continue
        # aggregate the scores
        user_scores = pd.concat([user_scores, top_titles_df[['title', 'sim_scores']]]).groupby(['title'], as_index=False).sum({'sim_scores'})

    user_scores = user_scores[~user_scores['title'].isin(movie_list)]
    return user_scores.sort_values(by='sim_scores', ascending=False)[:20]

def get_netflix_recs(user_scores):
    netflix = pd.read_csv('static/data/titles.csv')
    netflix = netflix[['title', 'type', 'imdb_score', 'imdb_votes', 'tmdb_popularity', 'tmdb_score']]
    netflix = netflix[netflix['type'] == 'MOVIE']

    recs = netflix.merge(user_scores, how='inner', on='title')
    recs = recs.sort_values(by='sim_scores', ascending=False)[:24]
    
    rated_recs = recs[['title', 'imdb_score', 'imdb_votes']]
    vote_counts = rated_recs[rated_recs['imdb_votes'].notnull()]['imdb_votes'].astype('int')
    vote_averages = rated_recs[rated_recs['imdb_score'].notnull()]['imdb_score'].astype('int')
    C = vote_averages.mean()
    m = vote_counts.quantile(0.60)
    qualified = rated_recs[(rated_recs['imdb_votes'] >= m) & (rated_recs['imdb_votes'].notnull())
                    & (rated_recs['imdb_score'].notnull())]
    qualified['imdb_votes'] = qualified['imdb_votes'].astype('int')
    qualified['imdb_score'] = qualified['imdb_score'].astype('int')
    qualified['wr'] = qualified.apply(weighted_rating, args=(m, C), axis=1)
    qualified = qualified.sort_values('wr', ascending=False).head(10)

    if len(qualified) > 5:
        return list(qualified['title'])
    else:
        return list(recs['title'])

def weighted_rating(x, m, C):
    v = x['imdb_votes']
    R = x['imdb_score']
    return (v/(v+m) * R) + (m/(m+v) * C)

def get_not_netflix_recs(user_scores):
    netflix = pd.read_csv('static/data/titles.csv')
    netflix = netflix[['title', 'type', 'imdb_score', 'imdb_votes', 'tmdb_popularity', 'tmdb_score']]
    netflix = netflix[netflix['type'] == 'MOVIE']

    not_netflix_recs = user_scores[~user_scores['title'].isin(netflix['title'])]
    not_netflix_recs = not_netflix_recs.sort_values(by='sim_scores', ascending=False)[:50]
    return not_netflix_recs

def get_common_movies(df1, df2):
    return list(set(df1['title']).intersection(set(df2['title'])))

def improved_recommendations(title, cosine_sim, tv):
    tv = tv.reset_index()
    indices = pd.Series(tv.index, index=tv['title'])

    idx = indices[title]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:26]
    tv_indices = [i[0] for i in sim_scores]
    
    tv_df = tv.iloc[tv_indices][['title', 'imdb_score', 'imdb_votes']]
    vote_counts = tv_df[tv_df['imdb_votes'].notnull()]['imdb_votes'].astype('int')
    vote_averages = tv_df[tv_df['imdb_score'].notnull()]['imdb_score'].astype('int')
    C = vote_averages.mean()
    m = vote_counts.quantile(0.60)
    qualified = tv_df[(tv_df['imdb_votes'] >= m) & (tv_df['imdb_votes'].notnull())
                       & (tv_df['imdb_score'].notnull())]
    qualified['imdb_votes'] = qualified['imdb_votes'].astype('int')
    qualified['imdb_score'] = qualified['imdb_score'].astype('int')
    qualified['wr'] = qualified.apply(weighted_rating, args=(m, C), axis=1)
    qualified = qualified.sort_values('wr', ascending=False).head(50)
    return qualified

def get_tv_list(df, type):
    return list(df[df['type'] == type]['Title'])

def get_tv_recs(tv_list, type):

    if type == "MOVIE":
        similarity = np.load('static/data/netflix_movies_similarity.npy')
        tv = pd.read_csv('static/data/netflix_movies.csv')
    else:
        similarity = np.load('static/data/tv_similarity.npy')
        tv = pd.read_csv('static/data/tv.csv')

    user_scores = pd.DataFrame(tv['title'])
    user_scores['wr'] = 0.0

    for tv_name in tv_list:
        try:
            top_titles_df = improved_recommendations(tv_name, similarity, tv)
        except:
            continue
        # aggregate the scores
        user_scores = pd.concat([user_scores, top_titles_df[['title', 'wr']]]).groupby(['title'], as_index=False).sum({'wr'})

    user_scores = user_scores[~user_scores['title'].isin(tv_list)]
    user_scores = user_scores.sort_values(by='wr', ascending=False)[:50]
    return user_scores

def get_common_tv(recs1, recs2):
    return list(set(recs1).intersection(set(recs2)))