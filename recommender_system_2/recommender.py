import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
sns.set_style('white', { 'axes.spines.right': False, 'axes.spines.top': False})
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from nltk.corpus import stopwords

path = '../MLdata/'
# movie metadata
df_meta=pd.read_csv(path + 'movies_metadata.csv', low_memory=False, encoding='UTF-8') 
df_meta = df_meta.drop([19730, 29503, 35587])

df_meta = df_meta.set_index(df_meta['id'].str.strip().replace(',','').astype(int))
pd.set_option('display.max_colwidth', 20)

# load movie credits
df_credits = pd.read_csv(path + 'credits.csv', encoding='UTF-8')
df_credits = df_credits.set_index('id')

# load movie keywords
df_keywords=pd.read_csv(path + 'keywords.csv', low_memory=False, encoding='UTF-8') 
df_keywords = df_keywords.set_index('id')

# merge
df_k_c = df_keywords.merge(df_credits, left_index=True, right_on='id')
df = df_k_c.merge(df_meta[['release_date','genres','overview','title']], left_index=True, right_on='id')

#########

df_movies = pd.DataFrame()
df_movies['keywords'] = df['keywords'].apply(lambda x: [i['name'] for i in eval(x)])
df_movies['keywords'] = df_movies['keywords'].apply(lambda x: ' '.join([i.replace(" ", "") for i in x]))
df_movies['overview'] = df['overview'].fillna('')
df_movies['release_date'] = pd.to_datetime(df['release_date'], errors='coerce').apply(lambda x: str(x).split('-')[0] if x!= np.nan else np.nan)
df_movies['cast'] = df['cast'].apply(lambda x:[i['name'] for i in eval(x)])
df_movies['cast'] = df_movies['cast'].apply(lambda x: ' '.join([i.replace(" ", "") for i in x]))
df_movies['genres'] = df['genres'].apply(lambda x: [i['name'] for i in eval(x)])
df_movies['genres'] = df_movies['genres'].apply(lambda x: ' '.join([i.replace(" ", "") for i in x]))
df_movies['title'] = df['title']

# merge all fields into 'tag' column
df_movies['tags'] = df_movies['keywords'] + df_movies['cast']+' '+df_movies['genres']+' '+df_movies['release_date']

df_movies.drop(df_movies[df_movies['tags']==''].index, inplace=True)
df_movies.drop_duplicates(inplace=True)
df_movies['new_id'] = range(0, len(df_movies))
df_movies = df_movies[['new_id', 'title', 'tags']]

df_movies['tag_len'] = df_movies['tags'].apply(lambda x: len(x))

##########

stop = list(stopwords.words('english'))

# create the tfid vectorizer, alternatively you can also use countVectorizer
tfidf =  TfidfVectorizer(max_features=5000, analyzer = 'word', stop_words=stop)
vectorized_data = tfidf.fit_transform(df_movies['tags'])
count_matrix = pd.DataFrame(vectorized_data.toarray(), index=df_movies['tags'].index.tolist())

##########

svd = TruncatedSVD(n_components=3000)
reduced_data = svd.fit_transform(count_matrix)

##########

similarity = cosine_similarity(reduced_data)
np.save('similarity', similarity)