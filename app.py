import sqlite3
import pandas as pd
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px

def run_query(query):
    conn = sqlite3.connect("archive/revenue.sqlite")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

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

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
           suppress_callback_exceptions=True)
app.title = "Steam Analysis Dashboard"

app.layout = html.Div([
    html.H1("Steam Analysis Dashboard", className="text-center my-4"),

    dcc.Tabs(id="tabs-styled-with-props", value='tab-1', children=[
        dcc.Tab(label='Games', value='tab-1'),
        dcc.Tab(label='Revenue', value='tab-2'),
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
            html.H3("Games Tab Content Placeholder")
            # Add the games data and charts here
        ])
    elif tab == 'tab-2':
        return html.Div([
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
            ], className="mb-4"),

            dbc.Card([
                dbc.CardHeader("Playtime Analysis"),
                dbc.CardBody([
                    dcc.Graph(
                        figure=px.bar(
                            playtime_df,
                            x="playtime_bucket",
                            y="avg_revenue",
                            title="Average Revenue by Playtime",
                            labels={"playtime_bucket": "Playtime", "avg_revenue": "Average Revenue"}
                        )
                    )
                ])
            ], className="mb-4"),

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


if __name__ == '__main__':
    app.run(debug=True)