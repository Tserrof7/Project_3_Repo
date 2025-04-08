import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import sqlite3

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Steam Game Visualizations"

# --- Data Loading ---
sqlite_file = 'revenue.sqlite'
conn = sqlite3.connect(sqlite_file)
query = "SELECT * FROM revenue_data"
df = pd.read_sql_query(query, conn)
conn.close()

#data clean

df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').astype(float)
df.dropna(subset=['revenue'], inplace=True)


# --- Helper Functions ---
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


def filter_by_revenue(df, revenue_range):
    if revenue_range == '0-200':
        return df[(df['revenue'] >= 0) & (df['revenue'] <= 200000000)]
    elif revenue_range == '200-400':
        return df[(df['revenue'] > 200000000) & (df['revenue'] <= 400000000)]
    elif revenue_range == '400-600':
        return df[(df['revenue'] > 400000000) & (df['revenue'] <= 600000000)]
    elif revenue_range == '600-800':
        return df[(df['revenue'] > 600000000) & (df['revenue'] <= 800000000)]
    elif revenue_range == '800+':
        return df[df['revenue'] > 800000000]
    else:
        return df  


# APP LAYOUT: Organize page elements
app.layout = dbc.Container([
    # Dashboard title
    html.H1("Steam Games Dashboard", className="text-center my-4"),

    dcc.Tabs(id="main-tabs", value='tab-1', children=[
        dcc.Tab(label='Main Dashboard', value='tab-1'),
        dcc.Tab(label='2024 Revenue Analysis', value='tab-2'),
    ]),
    html.Div(id='tabs-content')
], fluid=True) 


# CALLBACK: Update tab content
@app.callback(
    Output('tabs-content', 'children'),
    Input('main-tabs', 'value')
)
def render_tab_content(tab):
    if tab == 'tab-1':
        return dbc.Row([
            # Dropdown filter for selecting game genre
            dbc.Col([
                html.Label("Filter by Genre:"),
                dcc.Dropdown(
                    id='genre-dropdown',
                    options=[{'label': g, 'value': g}
                            for g in sorted({g.strip() for gs in df['Genres'] for g in gs.split(',')})],
                    placeholder="Select genre"
                )
            ], width=3),  # Sidebar column width

            # Column with interactive graphs
            dbc.Col([
                dcc.Graph(id='playtime-bar', style={'height': '500px'}),  # Graph 1: Playtime
                dcc.Graph(id='year-line', style={'height': '400px'}),     # Graph 2: Release year trend
                # dcc.Graph(figure=fig3, id='rating-bar', style={'height': '450px'})  # Graph 3: Static publisher chart
            ], width=9)
        ])
    elif tab == 'tab-2':
        return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('Top Revenue Games'),
                dbc.CardBody([
                    html.Label("Filter by Revenue:"),
                    create_revenue_dropdown(),
                    dcc.Graph(id='revenue-bar', style={'height': '100%', 'width': '100%'})
                ])
            ], className="mb-4", style={'width': '100%', 'max-height': '100%'})
        ], width=11),  
        dbc.Col([], width=7),  
    ], className="d-flex flex-wrap",
        justify="center")
    else:
        return html.P("Select a tab to view content.")


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


# CALLBACK: Update revenue bar chart
@app.callback(
    Output('revenue-bar', 'figure'),
    Input('revenue-dropdown', 'value')
)
def update_revenue_bar(selected_revenue):
    filtered_df = filter_by_revenue(df, selected_revenue)
    top10_revenue = filtered_df.sort_values('revenue', ascending=False).head(10)
    fig7 = px.bar(top10_revenue, x='revenue', y='name',  orientation='h', title='Top 10 Games by Revenue',
            labels={'revenue': 'Revenue', 'name': 'Game Title'},
            hover_data = ['name','price','revenue'])
    fig7.update_layout(yaxis={'categoryorder': 'total ascending'},  
                    height=600,)
    return fig7


# Run the app in Jupyter Notebook (use "external" to see it in a  browser or "inline" to run it within the notbook)vbnbm./
if __name__ == '__main__':
    app.run(debug=True)