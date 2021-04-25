import requests
import io
from os import path
import pandas as pd
import plotly.graph_objs as go

def fetch_data(path_to_data, file_name='../data/latest_crime_data.csv'):
    """
    Request the dataset from 
    https://www.ethnicity-facts-figures.service.gov.uk/crime-justice-and-the-law/policing/number-of-arrests/.

    Args:
        path_to_data (string) representing the url of the data (csv).
        file_name (string) representing the location to store the downloaded data.

    Returns:
        ../data/latest_crime_data.csv containing the raw data from the url.
        The size of the new file and whether or not it has been overwritten or newly created.
    """
    no_content_error_message = 'No content has been downloaded! Please check url.'

    try:
        # request the data from the given url
        r = requests.get(path_to_data)

        # converts byte-code to string
        content = r.content.decode('utf-8')

        if content == None:
            return no_content_error_message
        else:    
            df = pd.read_csv(io.StringIO(content))
            return df
    except Exception as e:
        print("Unable to fetch dataset from url.")
        print(e)

def clean_data():
    """
    Clean the data of redundant columns, missing values, data quality etc.

    Args:
        None

    Returns:
        df (pandas.DataFrame) containing cleaned version of data.
    """
    # url where data source is located
    csv_url = "https://www.ethnicity-facts-figures.service.gov.uk/crime-justice-and-the-law/policing/number-of-arrests/latest/downloads/number-of-arrests.csv"


    # call read_data()
    df = fetch_data(csv_url)

    # strip any whitespace in column names
    df.columns = [i.strip() for i in df.columns]

    # remove columns with low cardinality
    low_card_cols = df.columns[df.nunique() == 1].tolist()
    if low_card_cols != []:
        df.drop(low_card_cols, axis=1, inplace=True)
    else:
        del low_card_cols

    # remove notes column due to number of missing values. This may change in future.
    df.drop(['Notes'], axis=1, inplace=True)

    # drop ethnicity type as it is completely correlated with ethnicity
    df.drop(['Ethnicity_type'], axis=1, inplace=True)

    # sort data by time
    df.sort_values(by='Time', ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # clean the number of arrests by removing commas from numbers and removing non-numeric chars
    df['Number of arrests'] = df['Number of arrests'].str.replace("[^0-9]", "").str.strip()

    # create a flag column to show rows with missing values in number of arrests
    df['Missing_Number_of_Arrests'] = df['Number of arrests'].apply(lambda x: 1 if x == '' else 0)

    # convert arrests column to int
    df['Number of arrests'] = df['Number of arrests'].replace('', -1)
    df['Number of arrests'] = df['Number of arrests'].astype(int)

    # make new ethnic groups like those on data source website description
    df.Ethnicity = df.Ethnicity.apply(lambda x: 'Asian' if x in ['Asian', 'Indian', 'Pakistani', 'Bangladeshi', 'Any other asian']
                                      else 'Black' if x in ['Black Caribbean', 'Black African', 'Any other black background', 'Black']
                                      else 'White' if x in ['White Irish', 'White British', 'White', 'Any other white background']
                                      else 'Other' if x in ['Chinese', 'Other', 'Any other ethnic group']
                                      else 'Mixed' if 'mixed' in x.lower() else x)

    return df

def filter_df(how='all'):
    """
    Filters the data to include only stats about population as a whole.

    Args:
        how (string) ['all', 'not all'] representing how to filter the data:
            'all' selects all rows where column values = all
            'not all' selects all rows where column values != all 

    Returns:
        filtered_df (pandas.DataFrame) containing filtered data
    """
    # call clean_data()
    df = clean_data()

    if how == 'all':
        filtered_df = df.loc[(df.Geography=='All') & (df.Gender=='All') & (df.Ethnicity=='All') &
                             (df.Age_Group=='All') & (df.Missing_Number_of_Arrests == 0)].copy()
    elif how == 'not all':
        filtered_df = df.loc[(df.Ethnicity != 'All') & (df.Gender != 'All') &
                             (df.Age_Group != 'All') & (df.Geography != 'All') &
                             (df.Missing_Number_of_Arrests == 0)].copy()
    else:
        raise Exception("Parameter value not recognised. Value must be 'all' or 'not all'.")

    return filtered_df

def plot_data():
    """
    Plots the data to be displayed on the frontend of the web application.

    Args:
        None

    Returns:
        figures (list) containing the plotly visualisations (dict)
    """
    # call clean_data() and filter_data()
    df_all = filter_df()
    df_not_all = filter_df(how='not all')
    df = clean_data()

    # plot the rate of arrests by gender
    plot_one = []

    df_gender_pivot = df.loc[(df.Missing_Number_of_Arrests == 0) & (df.Ethnicity=='All') & (df.Geography=='All') &
                             (df.Age_Group=='All') & (df.Gender != 'All')].copy()
    df_gender_pivot = df_gender_pivot.pivot_table(index='Time', columns=['Gender'], values='Rate per 1,000 population by ethnicity, gender, and PFA', aggfunc='sum')

    plot_one.append(
        go.Scatter(
            x=df_gender_pivot.index.tolist(),
            y=df_gender_pivot.Female.tolist(),
            mode='lines+markers',
            marker=dict(
                symbol=200
            ),
            name='Female',
            line=dict(
                color="aquamarine"
            )
        )
    )

    plot_one.append(
        go.Scatter(
            x=df_gender_pivot.index.tolist(),
            y=df_gender_pivot.Male.tolist(),
            mode='lines+markers',
            marker=dict(
                symbol=200
            ),
            name='Male',
            line=dict(
                color="yellow"
            )
        )
    )

    layout_one = dict(
        title="Rate of Arrests Arrests by Gender per Year",
        font = dict(
            color="white"
        ),
        plot_bgcolor='transparent',
        paper_bgcolor="transparent",
        xaxis=dict(
            title='Year',
            color='white',
            showgrid=False,
            tickangle=60
        ),
        yaxis=dict(
            title="Rate of arrests (per 1000 people)",
            color='white'
        ),
    )

    # plot arrests by ethnicity - use grouping that are specified on data source website
    df_ethnic_pivot = df.loc[(df.Missing_Number_of_Arrests == 0) & (df.Ethnicity != 'All') &
                       (df.Age_Group == 'All') & (df.Geography == 'All') &
                       (df.Gender == 'All')].copy()
    df_ethnic_pivot = df_ethnic_pivot.loc[df_ethnic_pivot.Ethnicity != 'Unreported']
    df_ethnic_pivot['Rate per 1,000 population by ethnicity, gender, and PFA'] = df_ethnic_pivot['Rate per 1,000 population by ethnicity, gender, and PFA'].astype(int)
    df_ethnic_pivot = df_ethnic_pivot.pivot_table(index='Time', columns=['Ethnicity'],
                                                  values='Rate per 1,000 population by ethnicity, gender, and PFA', aggfunc='sum')

    plot_two = []
    colors = ['aquamarine', 'yellow', 'skyblue', 'tomato', 'magenta']

    for eth, col in zip(df_ethnic_pivot.columns, colors):
        plot_two.append(
            go.Scatter(name=eth,
                       x=df_ethnic_pivot.index.tolist(),
                       y=df_ethnic_pivot[eth].tolist(),
                       line=dict(
                           color=col
                       ),
                       mode='lines+markers',
                       marker=dict(
                           symbol=102
                       )
            )
        )

    layout_two = dict(
        title="Rate of Arrests by Ethnicity per Year",
        font = dict(
            color='white'
        ),
        xaxis=dict(
            title="Year",
            color='white',
            showgrid=False,
            tickangle=60
        ),
        yaxis=dict(
            title="Rate of arrests (per 1000 people)",
            color="white"
        ),
        paper_bgcolor='transparent',
        plot_bgcolor='transparent'
    )

    # plot the top 10 forces per year
    df_forces = df.loc[(df.Missing_Number_of_Arrests == 0) & (df.Ethnicity == 'All') & (df.Age_Group == 'All') &
                       (df.Gender == 'All') & (df.Geography != 'All')].copy()
    df_forces = df_forces.loc[~df['Rate per 1,000 population by ethnicity, gender, and PFA'].str.contains('N/A')]
    df_forces['Rate per 1,000 population by ethnicity, gender, and PFA'] = df_forces['Rate per 1,000 population by ethnicity, gender, and PFA'].astype(int)
    df_forces_arrest_rates = df_forces.groupby(['Geography'])['Rate per 1,000 population by ethnicity, gender, and PFA'].mean().sort_values(ascending=False)
    top10_forces = df_forces_arrest_rates.index.tolist()[:10]
    bottom10_forces = df_forces_arrest_rates.index.tolist()[-10:]

    df_top10_forces = df.loc[(df.Missing_Number_of_Arrests == 0) & (df.Ethnicity == 'All') & (df.Age_Group == 'All') &
                       (df.Gender == 'All') & (df.Geography.isin(top10_forces))].copy()
    df_top10_forces_pivot = df_top10_forces.pivot_table(index='Time', columns=['Geography'], values='Rate per 1,000 population by ethnicity, gender, and PFA', aggfunc='sum')
    df_top10_forces_pivot.at['2017/18', 'Lancashire'] = 14 # lancashire didnt record 17/18 data so fill value with year before 

    plot_three = []
    colors = ['aquamarine', 'yellow', 'skyblue', 'tomato', 'magenta', 'blue', 'chartreuse', 'cyan', 'navajowhite', 'hotpink']

    for force,col in zip(df_top10_forces_pivot.columns, colors):
        plot_three.append(
            go.Scatter(
                x=df_top10_forces_pivot.index.tolist(),
                y=df_top10_forces_pivot[force].tolist(),
                name=force,
                mode='lines+markers',
                line=dict(
                    color=col
                ),
                marker=dict(
                    symbol=200
                )
            )
        )

    layout_three = dict(
        title="Police Forces with Highest Rates of Arrest",
        font = dict(
            color='white'
        ),
        xaxis=dict(
            title="Year",
            color='white',
            showgrid=False
        ),
        yaxis=dict(
            title="Rate of arrests (per 1000 people)",
            color="white"
        ),
        paper_bgcolor='transparent',
        plot_bgcolor='transparent'
    )

    # plot rate of arrest for ethnicity for top 5 and bottom 5 forces
    top5_forces = df_forces_arrest_rates.index.tolist()[:6]
    bottom5_forces = df_forces_arrest_rates.index.tolist()[-6:]
    df_ethnic_pivot = df.loc[(df.Missing_Number_of_Arrests == 0) & (df.Ethnicity != 'All') &
                       (df.Age_Group == 'All') & (df.Geography.isin(top5_forces + bottom5_forces)) &
                       (df.Gender == 'All')].copy()
    df_ethnic_pivot = df_ethnic_pivot.loc[df_ethnic_pivot.Ethnicity != 'Unreported']
    df_ethnic_pivot['Rate per 1,000 population by ethnicity, gender, and PFA'] = df_ethnic_pivot['Rate per 1,000 population by ethnicity, gender, and PFA'].astype(int)
    df_force_ethnic_groups = df_ethnic_pivot.groupby('Geography')
    forces_dict = dict()
    forces_layout_dict = dict()

    for name, group, in df_force_ethnic_groups:
        colors = ['aquamarine', 'yellow', 'skyblue', 'tomato', 'magenta']
        plot_tmp = []
        tmp = group.pivot_table(index='Time', columns=['Ethnicity'], values='Rate per 1,000 population by ethnicity, gender, and PFA', aggfunc='sum')
        for eth, col in zip(tmp.columns, colors):
            plot_tmp.append(go.Scatter(
                name=eth,
                mode="lines+markers",
                x=tmp.index.tolist(),
                y=tmp[eth].tolist(),
                line=dict(
                    color=col
                ),
                marker=dict(
                    symbol=200
                )
            ))
        forces_dict[name] = plot_tmp
        forces_layout_dict[name] = dict(
                                    title=name,
                                    font = dict(
                                    color='white'
                                    ),
                                    xaxis=dict(
                                        title="Year",
                                        color='white',
                                        showgrid=False,
                                        tickangle=60
                                    ),
                                    yaxis=dict(
                                        title="Rate of arrests (per 1000 people)",
                                        color="white"
                                    ),
                                    paper_bgcolor='transparent',
                                    plot_bgcolor='transparent'
                                    )
        

    # append all plotly graphs to a list
    figures = []
    figures.append(dict(data=plot_one, layout=layout_one))
    figures.append(dict(data=plot_two, layout=layout_two))
    figures.append(dict(data=plot_three, layout=layout_three))
    
    for i, j in zip(forces_dict.items(), forces_layout_dict.items()):
        if i[0] in top5_forces:
            figures.append(dict(data=i[1], layout=j[1]))

    for i, j in zip(forces_dict.items(), forces_layout_dict.items()):
        if i[0] in bottom5_forces:
            figures.append(dict(data=i[1], layout=j[1]))

    return figures