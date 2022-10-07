import string
from typing import List, Hashable, Dict
from geopy import distance
import pandas as pd
import reverse_geocoder as rg
import chars2vec
import keras
from sklearn.cluster import AgglomerativeClustering
import tensorflow.keras


# Define the function to remove the punctuation
def remove_punctuations(text):
    for punctuation in string.punctuation:
        text = text.replace(punctuation, '')
    return text

# Dataframe cleaning process
def basic_cleaning(df):
    original_shape = df.shape
    print(f'original dataset shape {original_shape}')

    #number of rows of null names, duplicates
    null_in_name = len(df[df['name'].isna()])
    duplicated = sum(df.duplicated(subset=['name','platform','latitude','longitude']))


    #'name' column: drop duplicate
    df = df.drop_duplicates(['name','platform','latitude','longitude'], keep='first')
    df = df[df['name'].notna()]
    df = df.drop_duplicates()

    #lower case, trimmed white space
    df.loc[:, 'name'] = df.loc[:, 'name'].str.lower().str.strip()
    #remove special characters
    df['name'] = df['name'].apply(remove_punctuations)

    #convert latitude and longitude to float, get number of latitude rows out of range and then drop na
    df[["latitude","longitude"]] = df[["latitude","longitude"]]._convert(numeric=True)
    df["latitude"] = df.latitude.astype(float)
    df["longitude"] = df.longitude.astype(float)
    unknown_loc = len(df[(df.latitude >90) & (df.latitude <-90) ])
    loc_na = len(df[(df.latitude.isna()) | (df.longitude.isna())])
    df = df[(df.latitude.notna()) & (df.longitude.notna())]
    df = df[(df.latitude <= 90) & (df.latitude >= -90)]

    #Clean 'active' column
    df['active'] = df.active.replace(['TRUE','FALSE'],['True','False'])

    #Append city, state, country base on lat and long
    df = get_city_state_country(df)

    #State with FIPS
    state_fips = pd.read_csv('state_fips.csv')
    #Append FIPS to dataset
    df = df.merge(state_fips, left_on='state', right_on='Name', how='left')\
    .drop(['Name', 'FIPS'], axis=1)
    #Drop rows without FIPS(cannot be recognized as US)
    not_us = len(df[df['Postal Code'].isna()])
    df = df[df['Postal Code'].notna()]
    #Drop rows without status(cannot recognize active status)
    unknown_status = len(df[df['active'].isna()])
    df = df[df['active'].notna()]

    #Drop columns not in use
    df = df.drop(columns=['delivery_radius', 'geom'])
    #Add keyword column
    '''
    df['keyword'] = df['name'] + df['city'] + df['platform']
    df['keyword'] = df['keyword'].str.replace(' ', '').str.lower().apply(remove_punctuations)
    '''
    #Transform data type to reduce memory use
    df[['platform','sub_platform','city','country','active','state']]\
    = df[['platform','sub_platform','city','country','active','state']].astype('category')
    df[['latitude','longitude']] = df[['latitude','longitude']].astype('float32')

    print(f'{null_in_name} null in name columns are found and removed')
    print(f'{loc_na} unknown in columns latitude/logitude are found and removed')
    print(f'{duplicated} duplicated rows are found and removed')
    print(f'{unknown_loc} unknown coordinates are found and removed')
    print(f'{not_us} restaurants not in U.S are found and removed')
    print(f'{unknown_status} unknown active status are found and removed')
    after_shape = df.shape
    print(f'clean dataset shape {after_shape}')
    return df

#Clustering to drop duplicate based on name similarity
c2v_model = chars2vec.load_model('eng_50')
#Append cluster id to restaurants with similar names in same city
def similar_restaurant_clusters(group: pd.DataFrame) -> Dict[Hashable, int]:
    restaurant_names = group['name'].to_numpy()
    word_features = c2v_model.vectorize_words(restaurant_names)
    if len(word_features) == 0:
        return {}
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=0.3  # smaller threshold meaning more strict similarities, and more clusters
    ).fit(word_features)
    res = {}
    for (i, row), label in zip(group.iterrows(), clustering.labels_):
        res[i] = int(label)
    return res


#Assign group id after clustering
def restaurant_name_to_group_id(df, restaurant_names, clustering):
    restaurant_name_to_group_id = {}
    for i in range(len(restaurant_names)):
        restaurant_name = restaurant_names[i]
        group_id = int(clustering.labels_[i])
        restaurant_name_to_group_id[restaurant_name] = group_id
    df["group_id"] = df["name"].map(restaurant_name_to_group_id)
    df = df[df['group_id'].notnull()].sort_values(by=['group_id'])
    return df


# Within cluster groups, return the row indices of duplicates that are located
# near each other (distance <= 200m).
def split_by_geo_locations(cluster: pd.DataFrame) -> List[Hashable]:
    coordinates_seen = []
    to_drop = []
    for i, row in cluster.iterrows():
        row_coord = (row["latitude"], row["longitude"])
        dropped = False
        for seen_coord in coordinates_seen:
            if distance.distance(row_coord, seen_coord).km <= 0.2:  # distance <= 200m
                # The coordinate of the current row is previously seen.
                # This is therefore a duplicated restaurant and can be deleted.
                to_drop.append(i)
                dropped = True
                break

        if not dropped:
            # The coordinate of the current row was never seen before.
            # Record this newly discovered location.
            coordinates_seen.append(row_coord)

    return to_drop

#find city, state, country according to coordinates
def get_city_state_country(df):
    coord = tuple(zip(df['latitude'], df['longitude']))
    addresses = rg.search(coord)
    df['city'] = [address.get('admin2', '') for address in addresses]
    df['state'] = [address.get('admin1', '') for address in addresses]
    df['country'] = [address.get('cc', '') for address in addresses]
    return df
