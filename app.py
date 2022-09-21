import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

# Set page tab display
st.set_page_config(
   page_title="Restaurant Locations",
   page_icon= '🍔',
   layout="wide",
   initial_sidebar_state="expanded",
)

# Title
st.markdown("<h1 style='text-align: center; color: white;'>U.S Restaurant Location Dashboard</h1>", unsafe_allow_html=True)
#dataframe
df = pd.read_csv('dashboard_dataset.csv', index_col=0)

# Mapbox token
token = 'pk.eyJ1IjoiYmVsdWxldW5nIiwiYSI6ImNsN2lzOTcwNzA4dXUzcG1xN21qcWFtam0ifQ.TtyocIPJr4PGr5vi-rvgWA'
px.set_mapbox_access_token(token)

# Create the scatter mapbox
fig = px.scatter_mapbox(df,
                        lat="latitude",
                        lon="longitude",
                        hover_name="name",
                        color="active",
                        size_max=15,
                        zoom=2.8,
                        width=1200,
                        height=700,
                        center=dict(lat=37.0902, lon=-95.7129), #middle point of United States
                        mapbox_style='open-street-map'
                        )

# Plot!
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.plotly_chart(fig, use_container_width=False)

with col2:
    st.write(' ')

with col3:
    st.write(' ')

with col4:
    st.write(' ')

with col5:
    st.write(' ')

with col6:
    st.write(' ')

# Create customized DF
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_pagination(paginationAutoPageSize=True) #Add pagination
gb.configure_side_bar() #Add a sidebar
gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren="Group checkbox select children") #Enable multi-row selection
gb.configure_column('restaurant_id', headerCheckboxSelectionFilteredOnly = True, headerCheckboxSelection = True)
gridOptions = gb.build()

# Title of DF
st.write('Restaurant List')
grid_response = AgGrid(
    df,
    gridOptions=gridOptions,
    data_return_mode='AS_INPUT',
    update_mode='MODEL_CHANGED',
    fit_columns_on_grid_load=False,
    theme='balham', #Add theme color to the table
    enable_enterprise_modules=True,
    height=350,
    width='100%',
    reload_data=True
)

data = grid_response['data']
selected = grid_response['selected_rows']
df_new = pd.DataFrame(selected)   #Pass the selected rows to a new dataframe df

if selected:
    st.write('Selected rows')
    st.dataframe(df_new)
    csv = df_new.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='selected.csv',
        mime='text/csv',
    )

    #Create figure
    fig_new = px.scatter_mapbox(df_new,
                            lat="latitude",
                            lon="longitude",
                            hover_name="name",
                            color="active",
                            size_max=15,
                            zoom=2.8,
                            width=1200,
                            height=700,
                            center=dict(lat=37.0902, lon=-95.7129), #middle point of United States
                            mapbox_style='open-street-map'
                            )
    fig_new.update_traces(marker={'size': 12})
    st.plotly_chart(fig_new, use_container_width=False)
