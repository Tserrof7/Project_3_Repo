import pandas as pd
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
from sqlalchemy import create_engine
import dash_bootstrap_components as dbc

# ---------------- Setup Dash App ----------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Steam Game Visualizations"

# ---------------- Load + Clean Data ----------------
# Connect to SQLite database
engine = create_engine('sqlite:///Steam_Games_db.sqlite')
df = pd.read_sql("SELECT * FROM general_info", engine)

# Clean column names (remove spaces)
df.columns = df.columns.str.strip()

# Convert date column to year
df['Year'] = pd.to_datetime(df['Release date'], errors='coerce').dt.year

# Handle missing values
df['Genres'] = df['Genres'].fillna("Unknown")
df['Name'] = df['Name'].fillna("Unnamed")
df['User score'] = pd.to_numeric(df['User score'], errors='coerce')
df['Average playtime forever'] = pd.to_numeric(df['Average playtime forever'], errors='coerce')

# Generate list of unique genres for dropdown
genre_list = sorted({g.strip() for genre in df['Genres'] for g in str(genre).split(',')})

# ---------------- Layout ----------------
app.layout = dbc.Container([
    html.H1("🎮 Steam Games Dashboard", className="text-center my-4"),

    dbc.Row([
        # Sidebar: Genre Dropdown
        dbc.Col([
            html.Label("Filter by Genre:"),
            dcc.Dropdown(
                id='genre-dropdown',
                options=[{'label': g, 'value': g} for g in genre_list],
                placeholder="Select genre"
            )
        ], width=3),

        # Main: Graphs
        dbc.Col([
            dcc.Graph(id='playtime-bar', style={'height': '500px'}),
            dcc.Graph(id='year-line', style={'height': '400px'}),
            dcc.Graph(id='rating-bar', style={'height': '450px'})
        ], width=9)
    ])
], fluid=True)

# ---------------- Interactivity: Callback ----------------
@app.callback(
    [Output('playtime-bar', 'figure'),
     Output('year-line', 'figure'),
     Output('rating-bar', 'figure')],
    [Input('genre-dropdown', 'value')]
)
def update_graphs(selected_genre):
    # Filter data by genre if selected
    filtered = df[df['Genres'].str.contains(selected_genre, na=False)] if selected_genre else df

    # ---- Chart 1: Top 10 by Avg Playtime ----
    playtime = filtered[['Name', 'Average playtime forever']].dropna()
    playtime = playtime[playtime['Average playtime forever'] > 0]
    top10 = playtime.sort_values('Average playtime forever', ascending=False).head(10)
    fig1 = px.bar(top10, x='Average playtime forever', y='Name', orientation='h',
                  title="Top 10 Most-Played Games")
    fig1.update_layout(xaxis_title="Minutes", yaxis_title="Game", yaxis={'categoryorder': 'total ascending'})

    # ---- Chart 2: Games Released per Year ----
    year_count = filtered['Year'].value_counts().reset_index()
    year_count.columns = ['Year', 'Count']
    year_count = year_count.sort_values('Year')
    fig2 = px.line(year_count, x='Year', y='Count', title='Games Released by Year')
    fig2.update_layout(xaxis_title="Year", yaxis_title="Games")

    # ---- Chart 3: Avg Score by Publisher ----
    scores = filtered.groupby('Publishers')['User score'].mean().reset_index()
    top_scores = scores.sort_values('User score', ascending=False).head(10)
    fig3 = px.bar(top_scores, x='Publishers', y='User score', title='Top Publishers by Avg User Score')
    fig3.update_layout(xaxis_title="Publisher", yaxis_title="Score", xaxis_tickangle=-45)

    return fig1, fig2, fig3

# ---------------- Run the App ----------------
if __name__ == '__main__':
    app.run(debug=True)