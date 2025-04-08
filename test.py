import sqlite3
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px

# Database file name
DB_FILE = "Steam_Games_db.sqlite"  # Use a constant for the database file

# Function to run SQL queries
def run_query(query):
    with sqlite3.connect(DB_FILE) as conn:
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

    dcc.Tabs(id="tabs-styled-with-props", value='tab-1', children=[
        dcc.Tab(label='Games', value='tab-1'),
        dcc.Tab(label='Revenue', value='tab-2'),
        dcc.Tab(label='Scatter Plots', value='tab-3'),  # Added a new tab for scatter plots
    ], colors={
        "border": "grey",
        "primary": "white",
        "background": "grey"
    }),

    html.Div(id='tabs-content-props')
], fluid=True)

# Callback to render tab content
@app.callback(Output('tabs-content-props', 'children'),
              Input('tabs-styled-with-props', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
            html.H3("Games Tab Content Placeholder")
            # Add the games data and charts here
        ])
    elif tab == 'tab-2':
        return html.Div([
            html.H3("Revenue Tab Content Placeholder")
            # Add the revenue data and charts here
        ])
    elif tab == 'tab-3':
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Price vs. Revenue Scatter Plot"),
                            dcc.Graph(id='price-revenue-scatter')
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Average Playtime vs. Revenue Scatter Plot"),
                            dcc.Graph(id='playtime-revenue-scatter')
                        ])
                    ])
                ], width=6)
            ])
        ])
    else:
        return html.P("Select a tab to view content.")

# Callback to update scatter plots
@app.callback(
    [Output('price-revenue-scatter', 'figure'),
     Output('playtime-revenue-scatter', 'figure')],
    Input('tabs-styled-with-props', 'value')  # Trigger when the tab changes
)
def update_scatter_plots(tab):
    if tab != 'tab-3':
        return {}, {}  # Return empty figures if not on the scatter plot tab

    # Price vs. Revenue Scatter Plot
    fig_price_revenue = px.scatter(
        df, x='price', y='revenue',
        title='Price vs. Revenue',
        labels={'price': 'Price', 'revenue': 'Revenue'}
    )

    # AvgPlaytime vs. Revenue Scatter Plot
    fig_playtime_revenue = px.scatter(
        df, x='avg_playtime', y='revenue',
        title='Average Playtime vs. Revenue',
        labels={'avg_playtime': 'Average Playtime', 'revenue': 'Revenue'}
    )

    return fig_price_revenue, fig_playtime_revenue

# Run app
if __name__ == '__main__':
    app.run(debug=True)