import sqlite3
import pandas as pd
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px

# Function to run SQL queries
def run_query(query_1):
    with sqlite3.connect("Steam_Games_db.sqlite") as conn_1:
        return pd.read_sql_query(query_1, conn_1)

def run_query(query_2):
    conn_2 = sqlite3.connect("archive/revenue.sqlite")
    df_2 = pd.read_sql_query(query_2, conn_2)
    conn_2.close()
    return df_2

sqlite_file_3 = 'revenue.sqlite'
conn_3 = sqlite3.connect(sqlite_file_3)
query_3 = "SELECT * FROM revenue_data"
df_3 = pd.read_sql_query(query_3, conn_3)
conn_3.close()

##Update the query names##

free_paid_df = run_query("""SELECT
    CASE 
        WHEN price = 0 THEN 'Free'
        ELSE 'Paid'
    END AS price_category,
    AVG(revenue) AS avg_revenue,
    AVG(CAST(copies_sold AS INTEGER)) AS avg_copies_sold,
    AVG(avg_playtime) AS avg_playtime,
    AVG(review_score) AS avg_review_score
FROM revenue_data
GROUP BY price_category""")

revenue_df = run_query("""
SELECT 
    CASE STRFTIME('%m', formatted_date)
        WHEN '01' THEN 'January'
        WHEN '02' THEN 'February'
        WHEN '03' THEN 'March'
        WHEN '04' THEN 'April'
        WHEN '05' THEN 'May'
        WHEN '06' THEN 'June'
        WHEN '07' THEN 'July'
        WHEN '08' THEN 'August'
        WHEN '09' THEN 'September'
        WHEN '10' THEN 'October'
        WHEN '11' THEN 'November'
        WHEN '12' THEN 'December'
    END AS release_month,
    AVG(revenue) AS avg_monthly_revenue
FROM (
    SELECT 
        revenue, 
        DATE(SUBSTR(release_date, 7, 4) || '-' || 
            SUBSTR(release_date, 4, 2) || '-' || 
            SUBSTR(release_date, 1, 2)) AS formatted_date
    FROM revenue_data
    WHERE release_date IS NOT NULL
)
GROUP BY STRFTIME('%m', formatted_date)
ORDER BY STRFTIME('%m', formatted_date);
""")

playtime_df = run_query("""SELECT *
FROM (
    SELECT 
        CASE
            WHEN avg_playtime < 5 THEN 'Under 5 hrs'
            WHEN avg_playtime BETWEEN 5 AND 10 THEN '5–10 hrs'
            WHEN avg_playtime BETWEEN 10 AND 20 THEN '10–20 hrs'
            WHEN avg_playtime BETWEEN 20 AND 50 THEN '20–50 hrs'
            WHEN avg_playtime BETWEEN 50 AND 100 THEN '50–100 hrs'
            ELSE '100+ hrs'
        END AS playtime_bucket,
        COUNT(*) AS game_count,
        AVG(revenue) AS avg_revenue,
        AVG(review_score) AS avg_review_score
    FROM revenue_data
    GROUP BY playtime_bucket
)
ORDER BY 
    CASE playtime_bucket
        WHEN 'Under 5 hrs' THEN 1
        WHEN '5–10 hrs' THEN 2
        WHEN '10–20 hrs' THEN 3
        WHEN '20–50 hrs' THEN 4
        WHEN '50–100 hrs' THEN 5
        WHEN '100+ hrs' THEN 6
    END""")

publishers_df = run_query("""SELECT publishers, AVG(revenue) AS avg_revenue, COUNT(*) AS game_count FROM revenue_data GROUP BY publishers ORDER BY avg_revenue DESC""")

top_publishers = run_query("""
    SELECT Publishers, AVG(CAST([User score] AS FLOAT)) AS avg_score
    FROM general_info
    WHERE [User score] IS NOT NULL
    GROUP BY Publishers
    ORDER BY avg_score DESC
    LIMIT 10
""")

# Data cleaning
df_3['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').astype(float)
df_3.dropna(subset=['revenue'], inplace=True)

# Get genre list for dropdown
genres_df = run_query("SELECT Genres FROM general_info")
genres_df['Genres'] = genres_df['Genres'].fillna("Unknown")
genre_list = sorted({g.strip() for genre in genres_df['Genres'] for g in str(genre).split(',')})

# Static chart: Top publishers by user score

fig4 = px.bar(
    top_publishers, x="Publishers", y="avg_score", title="Top 10 Publishers by Avg User Score"
).update_layout(
    xaxis_title="Publisher", yaxis_title="Score", xaxis_tickangle=-45
)

# Dash app setup
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True)
app.title = "Steam Analysis Dashboard"

def create_revenue_dropdown():
    return dcc.Dropdown(
        id='revenue-dropdown',
        options=[
            {'label': '0-200M', 'value': '0-200'},
            {'label': '200M-400M', 'value': '200-400'},
            {'label': '400M-600M', 'value': '400-600'},
            {'label': '600-800M', 'value': '600-800'},
            {'label': '800M+', 'value': '800+'}
        ],
        value='0-200',
        placeholder="Select Revenue Range"
    )

def filter_by_revenue(df_3, revenue_range):
    if revenue_range == '0-200':
        return df_3[(df_3['revenue'] >= 0) & (df_3['revenue'] <= 200000000)]
    elif revenue_range == '200-400':
        return df_3[(df_3['revenue'] > 200000000) & (df_3['revenue'] <= 400000000)]
    elif revenue_range == '400-600':
        return df_3[(df_3['revenue'] > 400000000) & (df_3['revenue'] <= 600000000)]
    elif revenue_range == '600-800':
        return df_3[(df_3['revenue'] > 600000000) & (df_3['revenue'] <= 800000000)]
    elif revenue_range == '800+':
        return df_3[df_3['revenue'] > 800000000]
    else:
        return df_3  

# Layout
app.layout = html.Div([
    html.H1("Steam Analysis Dashboard", className="text-center my-4"),

    dcc.Tabs(id="tabs-styled-with-props", value='tab-1', children=[
        dcc.Tab(label='Main Dashboard', value='tab-1'),
        dcc.Tab(label='2024 Revenue Analysis', value='tab-2'),
    ], colors={
        "border": "grey",
        "primary": "white",
        "background": "grey"
    }),

    html.Div(id='tabs-content-props')
])

@callback(Output('tabs-content-props', 'children'),
        Input('tabs-styled-with-props', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
            dbc.Row([
                dbc.Col([
                html.Label("Filter by Genre:"),
                dcc.Dropdown(
                id='genre-dropdown',
                options=[{'label': g, 'value': g} for g in genre_list],
                placeholder="Select genre"
            )
            ], width=3),
                dbc.Col([
                    dbc.Card([dbc.CardBody([dcc.Graph(id='playtime-bar', style={'height': '450px'})])], className="mb-4"),
                    dbc.Card([dbc.CardBody([dcc.Graph(id='year-line', style={'height': '400px'})])], className="mb-4"),
                    dbc.Card([dbc.CardBody([dcc.Graph(figure=fig4, style={'height': '450px'})])], className="mb-4"),

                    # Radio + pie chart
                    dbc.Card([
                        dbc.CardBody([
                            html.Label("Pie Chart Metric:"),
                            dcc.RadioItems(
                                id='pie-radio',
                                options=[
                                    {'label': 'Average Playtime', 'value': 'avg'},
                                    {'label': 'Total Playtime', 'value': 'sum'},
                                    {'label': 'Game Count', 'value': 'count'}
                                ],
                                value='avg',
                                inline=True,
                                style={"marginBottom": "1rem"}
                            ),
                            dcc.Graph(id='genre-pie', style={'height': '400px'})
                        ])
                    ], className="mb-4")
                ], width=12)  
            ])
        ])
    elif tab == 'tab-2':
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Free vs Paid to Play Games'),
                        dbc.CardBody([
                            dcc.Dropdown(
                                id="dropdown-free-paid",
                                options=[
                                    {"label": "Average Revenue", "value": "avg_revenue"},
                                    {"label": "Average Copies Sold", "value": "avg_copies_sold"},
                                    {"label": "Average Playtime", "value": "avg_playtime"},
                                    {"label": "Average Review Score", "value": "avg_review_score"},
                                ],
                                value="avg_revenue",
                                clearable=False
                            ),
                            dcc.Graph(id="graph-free-paid")
                        ])
                    ], className="mb-4", style={'width': '100%', 'max-height': '100%'}),  # Added style
                ], width=6),  # Adjusted width
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Playtime Analysis"),
                        dbc.CardBody([
                            dcc.Graph(
                                id="playtime-analysis-graph",
                                figure=px.bar(
                                    playtime_df,
                                    x="playtime_bucket",
                                    y="avg_revenue",
                                    title="Average Revenue by Playtime",
                                    labels={"playtime_bucket": "Playtime", "avg_revenue": "Average Revenue"}
                                )
                            )
                        ])
                    ], className="mb-4", style={'width': '100%', 'max-height': '100%'}),  # Added style
                ], width=6),  # Adjusted width
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Top Revenue Games'),
                        dbc.CardBody([
                            html.Label("Filter by Revenue:"),
                            create_revenue_dropdown(),
                            dcc.Graph(id='revenue-bar', style={'height': '100%', 'width': '100%'})
                        ])
                    ], className="mb-4", style={'width': '100%', 'max-height': '100%'}),
                ], width=12),  # Adjusted width
            ], className="d-flex flex-wrap",
                justify="center"),
            dbc.Card([
                dbc.CardHeader("Monthly Average Revenue"),
                dbc.CardBody([
                    dcc.Graph(
                        id="graph-monthly-revenue",
                        figure=px.line(
                            revenue_df,
                            x="release_month",
                            y="avg_monthly_revenue",
                            markers=True,
                            title="Average Monthly Revenue",
                            labels={"release_month": "Month", "avg_revenue": "Average Revenue"}
                        )
                    )
                ])
            ], className="mb-4")
        ])
# Callback to update bar and line charts based on selected genre
@app.callback(
    [Output('playtime-bar', 'figure'),
    Output('year-line', 'figure')],
    Input('genre-dropdown', 'value')
)
def update_graphs(selected_genre):
    genre_filter = f"WHERE Genres LIKE '%{selected_genre}%' AND" if selected_genre else "WHERE"

    # Bar chart: Top 10 most-played games
    playtime_query = f"""
        SELECT Name, CAST([Average playtime forever] AS FLOAT) AS playtime
        FROM general_info
        {genre_filter} [Average playtime forever] IS NOT NULL
        ORDER BY playtime DESC
        LIMIT 10
    """
    play_df = run_query(playtime_query)
    fig1 = px.bar(
        play_df, x="playtime", y="Name", orientation="h", title="Top 10 Games by Average Playtime Forever"
    ).update_layout(xaxis_title="Play Time in Minutes", yaxis_title="Game", yaxis={'categoryorder': 'total ascending'})

    # Line chart: Games released by year
    year_query = f"""
        SELECT [Release date]
        FROM general_info
        {genre_filter} [Release date] IS NOT NULL
    """
    year_df = run_query(year_query)
    year_df['Release date'] = pd.to_datetime(year_df['Release date'], errors='coerce')
    year_df['Year'] = year_df['Release date'].dt.year
    year_counts = year_df['Year'].dropna().value_counts().sort_index().reset_index()
    year_counts.columns = ['Year', 'Count']

    fig2 = px.line(year_counts, x='Year', y='Count', title="Games Released by Year")

# CALLBACK: Update two graphs based on selected genre
@app.callback(
    [Output('playtime-bar', 'figure'),  # Graph 1
    Output('year-line', 'figure')],    # Graph 2
    [Input('genre-dropdown', 'value')]  # Triggered when genre is selected
)
def update_graphs(selected_genre):
    # Filter the dataset if a genre is selected
    filtered = df[df['Genres'].str.contains(selected_genre, na=False)] if selected_genre else df

    # 1️ Top 10 Most-Played Games
    playtime = filtered[['Name', 'Average playtime forever']].dropna()
    playtime = playtime[playtime['Average playtime forever'] > 0]
    top10 = playtime.sort_values('Average playtime forever', ascending=False).head(10)

    fig1 = px.bar(
        top10,
        x='Average playtime forever',
        y='Name',
        orientation='h',
        title="Top 10 Most-Played Games"
    )
    fig1.update_layout(xaxis_title="Minutes", yaxis_title="Game",
                    yaxis={'categoryorder': 'total ascending'})

    # 2️ Games Released per Year
    year_count = filtered['Year'].value_counts().reset_index()
    year_count.columns = ['Year', 'Count']
    year_count = year_count.sort_values('Year')

    fig2 = px.line(
        year_count,
        x='Year',
        y='Count',
        title='Games Released by Year'
    )

    fig2.update_layout(xaxis_title="Year", yaxis_title="Games")

    return fig1, fig2

# Callback to update pie chart based on selected metric
@app.callback(
    Output('genre-pie', 'figure'),
    Input('pie-radio', 'value')
)
def update_pie_chart(metric):
    df = run_query("SELECT `Genres`, `Average playtime forever` FROM general_info")
    df = df[df["Average playtime forever"] > 0].dropna(subset=["Genres"])
    df["Genres"] = df["Genres"].str.split(",")
    df = df.explode("Genres")

    non_game_genres = {
        "Audio Production", "Utilities", "Game Development", "Software Training",
        "Design & Illustration", "Animation & Modeling", "Video Production",
        "Photo Editing", "Accounting", "Education", "Web Publishing"
    }
    df = df[~df["Genres"].isin(non_game_genres)]

    if metric == 'avg':
        data = df.groupby("Genres")["Average playtime forever"].mean()
        title = "Average Playtime by Genre"
    elif metric == 'sum':
        data = df.groupby("Genres")["Average playtime forever"].sum()
        title = "Total Playtime by Genre"
    else:  # 'count'
        data = df["Genres"].value_counts()
        title = "Number of Games by Genre"

    top_10 = data.sort_values(ascending=False).head(10).reset_index()
    top_10.columns = ["Genre", "Value"]

    return px.pie(top_10, names="Genre", values="Value", title=title, hole=0.3)

#tab-2 config
@app.callback(
    Output("graph-free-paid", "figure"),
    Input("dropdown-free-paid", "value")
)
def update_free_paid(metric):
    fig = px.bar(
        free_paid_df,
        x="price_category",
        y=metric,
        color="price_category",
        labels={"price_category": "Game Type", metric: metric.replace("_", " ").title()},
        title=f"Free vs Paid — {metric.replace('_', ' ').title()}"
    )
    return fig

# CALLBACK: Update revenue bar chart
@app.callback(
    Output('revenue-bar', 'figure'),
    Input('revenue-dropdown', 'value')
)
def update_revenue_bar(selected_revenue):
    filtered_df = filter_by_revenue(df_3, selected_revenue)
    top10_revenue = filtered_df.sort_values('revenue', ascending=False).head(10)
    fig7 = px.bar(top10_revenue, x='revenue', y='name',  orientation='h', title='Top 10 Games by Revenue',
            labels={'revenue': 'Revenue', 'name': 'Game Title'},
            hover_data = ['name','price','revenue'])
    fig7.update_layout(yaxis={'categoryorder': 'total ascending'},  
                    height=600,)
    return fig7

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

