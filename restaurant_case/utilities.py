import string
from geopy import distance
import pandas as pd
import reverse_geocoder as rg

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
    for punctuation in string.punctuation:
        df['name'] = df['name'].replace(punctuation, '')

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

    print(f'{null_in_name} null in name columns are found and removed')
    print(f'{loc_na} unknown in columns latitude/logitude are found and removed')
    print(f'{duplicated} duplicated rows are found and removed')
    print(f'{unknown_loc} unknown coordinates are found and removed')
    after_shape = df.shape
    print(f'clean dataset shape {after_shape}')
    return df

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


#Within cluster groups, calculate distance between each other, drop duplicates if distance less than 200m
def split_by_geo_locations(cluster: pd.DataFrame):
    if len(cluster) < 2:
        # Only 1 restaurant has this group_id. No further comparison required.
        return cluster

    coordinates_seen = []
    for i, row in cluster.iterrows():
        row_coord = (row["latitude"], row["longitude"])
        dropped = False
        for seen_coord in coordinates_seen:
            if distance.distance(row_coord, seen_coord).km <= 0.2:  # distance <= 200 meter
                # The coordinate of the current row is previously seen.
                # This is therefore a duplicated restaurant and can be deleted.
                cluster.drop(i, inplace=True)
                dropped = True
                break

        if not dropped:
            # The coordinate of the current row was never seen before.
            # Record this newly discovered location.
            coordinates_seen.append(row_coord)

    return cluster

#find city, state, country according to coordinates
def get_city_state_country(df):
    coord = tuple(zip(df['latitude'], df['longitude']))
    addresses = rg.search(coord)
    df['city'] = [address.get('admin2', '') for address in addresses]
    df['state'] = [address.get('admin1', '') for address in addresses]
    df['country'] = [address.get('cc', '') for address in addresses]
    #df['city'] = city[0]
    #df['state'] = state[0]
    #df['country'] = country[0]
    return df
