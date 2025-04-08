import sqlite3
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px

# Function to run SQL queries
def run_query(query):
    with sqlite3.connect("Steam_Games_db.sqlite") as conn:
        return pd.read_sql_query(query, conn)

# Get genre list for dropdown
genres_df = run_query("SELECT Genres FROM general_info")
genres_df['Genres'] = genres_df['Genres'].fillna("Unknown")
genre_list = sorted({g.strip() for genre in genres_df['Genres'] for g in str(genre).split(',')})

# Static chart: Top publishers by user score
top_publishers = run_query("""
    SELECT Publishers, AVG(CAST([User score] AS FLOAT)) AS avg_score
    FROM general_info
    WHERE [User score] IS NOT NULL
    GROUP BY Publishers
    ORDER BY avg_score DESC
    LIMIT 10
""")

fig4 = px.bar(
    top_publishers, x="Publishers", y="avg_score", title="Top 10 Publishers by Avg User Score"
).update_layout(
    xaxis_title="Publisher", yaxis_title="Score", xaxis_tickangle=-45
)

# Dash app setup
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Steam Game Visualizations"

# Layout
app.layout = dbc.Container([
    html.H1("Steam Games Dashboard", className="text-center my-4"),

    dbc.Row([
        # Left column: genre dropdown
        dbc.Col([
            html.Label("Filter by Genre:"),
            dcc.Dropdown(
                id='genre-dropdown',
                options=[{'label': g, 'value': g} for g in genre_list],
                placeholder="Select genre"
            )
        ], width=3),

        # Right column: charts
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
            ])
        ], width=9)
    ])
], fluid=True)

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

# Run app
if __name__ == '__main__':
    app.run(debug=True)
