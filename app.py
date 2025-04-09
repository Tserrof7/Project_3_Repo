import sqlite3
import pandas as pd
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px


# Database Query Functions
def run_steam_query(query):
    with sqlite3.connect("archive/Steam_Games_db.sqlite") as conn:
        return pd.read_sql_query(query, conn)

def run_revenue_query(query):
    with sqlite3.connect("archive/revenue.sqlite") as conn:
        return pd.read_sql_query(query, conn)


# Data Preparation
# Top 10 publishers by user score
top_publishers = run_steam_query("""
SELECT Publishers, AVG(CAST([User score] AS FLOAT)) AS avg_score
FROM general_info
WHERE [User score] IS NOT NULL
GROUP BY Publishers
ORDER BY avg_score DESC
LIMIT 10
""")

# List of genres
genres_df = run_steam_query("SELECT Genres FROM general_info")
genres_df['Genres'] = genres_df['Genres'].fillna("Unknown")
genre_list = sorted({g.strip() for genre in genres_df['Genres'] for g in str(genre).split(',')})

# Revenue data
df_3 = run_revenue_query("SELECT * FROM revenue_data")
df_3['revenue'] = pd.to_numeric(df_3['revenue'], errors='coerce').astype(float)
df_3.dropna(subset=['revenue'], inplace=True)

# Free vs Paid revenue summary
free_paid_df = run_revenue_query("""
SELECT
    CASE WHEN price = 0 THEN 'Free' ELSE 'Paid' END AS price_category,
    AVG(revenue) AS avg_revenue,
    AVG(CAST(copies_sold AS INTEGER)) AS avg_copies_sold,
    AVG(avg_playtime) AS avg_playtime,
    AVG(review_score) AS avg_review_score
FROM revenue_data
GROUP BY price_category
""")

query_3 = run_revenue_query ("""SELECT * FROM revenue_data""")

# Monthly revenue summary
revenue_df = run_revenue_query("""
SELECT 
    CASE STRFTIME('%m', formatted_date)
        WHEN '01' THEN 'January' WHEN '02' THEN 'February'
        WHEN '03' THEN 'March' WHEN '04' THEN 'April'
        WHEN '05' THEN 'May' WHEN '06' THEN 'June'
        WHEN '07' THEN 'July' WHEN '08' THEN 'August'
        WHEN '09' THEN 'September' WHEN '10' THEN 'October'
        WHEN '11' THEN 'November' WHEN '12' THEN 'December'
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

# Playtime buckets
playtime_df = run_revenue_query("""
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
ORDER BY 
    CASE 
        WHEN playtime_bucket = 'Under 5 hrs' THEN 1
        WHEN playtime_bucket = '5–10 hrs' THEN 2
        WHEN playtime_bucket = '10–20 hrs' THEN 3
        WHEN playtime_bucket = '20–50 hrs' THEN 4
        WHEN playtime_bucket = '50–100 hrs' THEN 5
        WHEN playtime_bucket = '100+ hrs' THEN 6
    END
""")

# Dash App Setup
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Steam Games Dashboard"

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

# App Layout and tab selector

app.layout = html.Div([
    html.H1("Steam Games Dashboard", className="text-center my-4"),

    dcc.Tabs(id="tabs", value='tab-info', children=[
        dcc.Tab(label='Games Analysis', value='tab-info'),
        dcc.Tab(label='Revenue Analysis', value='tab-revenue'),
    ]),

    html.Div(id='tab-content')
], style={"marginLeft": "30px", "marginRight": "30px"})


# Tab Content Callback
@callback(Output('tab-content', 'children'), Input('tabs', 'value'))
def render_tab(tab):
    if tab == 'tab-info':
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id="genre-dropdown",
                        options=[{"label": g, "value": g} for g in genre_list],
                        placeholder="Select a Genre",
                        style={"width": "60%"}
                    ),
                    dcc.Graph(id="playtime-bar")
                ], width=6),

                dbc.Col([
                    dcc.Graph(id="year-line")
                ], width=6)
            ]),

            dbc.Row([
                dbc.Col([
                    dcc.RadioItems(
                        id='pie-radio',
                        options=[
                            {'label': 'Average Playtime', 'value': 'avg'},
                            {'label': 'Total Playtime', 'value': 'sum'},
                            {'label': 'Game Count', 'value': 'count'}
                        ],
                        value='avg',
                        inline=True
                    ),
                    dcc.Graph(id="genre-pie")
                ], width=6),

                dbc.Col([
                    dcc.Graph(
                        id="publisher-bar",
                        figure=px.bar(
                            top_publishers,
                            x='Publishers',
                            y='avg_score',
                            title='Top 10 Publishers by Avg User Score'
                        )
                    )
                ], width=6)
            ])
        ])
    
    elif tab == 'tab-revenue':
        return html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id="dropdown-free-paid",
                options=[
                    {"label": "Average Revenue", "value": "avg_revenue"},
                    {"label": "Average Copies Sold", "value": "avg_copies_sold"},
                    {"label": "Average Playtime", "value": "avg_playtime"},
                    {"label": "Average Review Score", "value": "avg_review_score"},
                ],
                value="avg_revenue",
                clearable=False,
                style={"width": "60%"}
            ),
            dcc.Graph(id="graph-free-paid")
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id="playtime-analysis-graph",
                figure=px.bar(
                    playtime_df,
                    x="playtime_bucket",
                    y="avg_revenue",
                    title="Avg Revenue by Playtime Bucket"
                )
            )
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id="graph-monthly-revenue",
                figure=px.line(
                    revenue_df,
                    x="release_month",
                    y="avg_monthly_revenue",
                    markers=True,
                    title="Average Monthly Revenue"
                )
            )
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Filter by Revenue:"),
                    create_revenue_dropdown(),
                    dcc.Graph(id='revenue-bar', style={'height': '100%', 'width': '100%','border': 'none'})
                ],style={'border': 'none'})
            ], style={'border': 'none'}, className="mb-4"),
        ], width=12)
    ], className="d-flex flex-wrap", justify="center"),
])

# Callback: Genre Filters
@callback(
    [Output('playtime-bar', 'figure'), Output('year-line', 'figure')],
    Input('genre-dropdown', 'value')
)
def update_genre_charts(genre):
    where_clause = f"WHERE Genres LIKE '%{genre}%' AND" if genre else "WHERE"

    play_query = f"""
        SELECT Name, CAST([Average playtime forever] AS FLOAT) AS playtime
        FROM general_info
        {where_clause} [Average playtime forever] IS NOT NULL
        ORDER BY playtime DESC LIMIT 10
    """
    play_df = run_steam_query(play_query)
    fig1 = px.bar(play_df, x='playtime', y='Name', orientation='h',
                title="Top 10 Games by Average Playtime Forever").update_layout(
        yaxis={'categoryorder': 'total ascending'})

    year_query = f"""
        SELECT [Release date]
        FROM general_info
        {where_clause} [Release date] IS NOT NULL
    """
    year_df = run_steam_query(year_query)
    year_df['Release date'] = pd.to_datetime(year_df['Release date'], errors='coerce')
    year_df['Year'] = year_df['Release date'].dt.year
    year_counts = year_df['Year'].value_counts().sort_index().reset_index()
    year_counts.columns = ['Year', 'Count']
    fig2 = px.line(year_counts, x='Year', y='Count', title="Games Released by Year", markers=True)
    return fig1, fig2


# Callback: Pie Chart by Genre

@callback(Output('genre-pie', 'figure'), Input('pie-radio', 'value'))
def update_pie(metric):
    df = run_steam_query("SELECT Genres, [Average playtime forever] FROM general_info")
    df = df.dropna(subset=["Genres", "Average playtime forever"]).copy()
    df["Average playtime forever"] = pd.to_numeric(df["Average playtime forever"], errors='coerce')
    df = df[df["Average playtime forever"] > 0].copy()
    
    df = df.reset_index(drop=True)
    df_exploded = df.copy()
    df_exploded["Genres"] = df_exploded["Genres"].str.split(",")
    df_exploded = df_exploded.explode("Genres").reset_index(drop=True)
    df_exploded["Genres"] = df_exploded["Genres"].str.strip()

    non_game = {
        "Audio Production", "Utilities", "Game Development", "Software Training",
        "Design & Illustration", "Animation & Modeling", "Video Production",
        "Photo Editing", "Accounting", "Education", "Web Publishing"
    }
    df_exploded = df_exploded[~df_exploded["Genres"].isin(non_game)]

    if df_exploded.empty:
        return px.pie(title="No data available")

    if metric == 'avg':
        data = df_exploded.groupby("Genres")["Average playtime forever"].mean()
    elif metric == 'sum':
        data = df_exploded.groupby("Genres")["Average playtime forever"].sum()
    else:
        data = df_exploded["Genres"].value_counts()

    top_10 = data.sort_values(ascending=False).head(10).reset_index()
    top_10.columns = ["Genre", "Value"]
    return px.pie(top_10, names="Genre", values="Value", title=metric.title() + " Playtime by Genre", hole=0.3)


# Callback: Free vs Paid Chart
@callback(Output("graph-free-paid", "figure"), Input("dropdown-free-paid", "value"))
def update_free_paid(metric):
    return px.bar(
        free_paid_df,
        x="price_category", y=metric,
        color="price_category",
        title=f"Free vs Paid — {metric.replace('_', ' ').title()}",
        labels={"price_category": "Game Type", metric: metric.replace("_", " ").title()}
    )

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

# Run the App
if __name__ == '__main__':
    app.run(debug=True)
