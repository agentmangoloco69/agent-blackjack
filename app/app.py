"""Bet-spread analysis dashboard.

Input a card-counting bet spread + game rules, and see the simulated edge:
EV (% of action and $/hr), Risk of Ruin, N0, and a bankroll percentile chart.

Run:
    python -m app.app
then open http://127.0.0.1:8050
"""

from dash import Dash, html, dcc, dash_table, Input, Output, State, ctx, no_update
import plotly.graph_objects as go

from simulator.rules import RuleSet
from simulator.counting import BetRamp
from simulator.analysis import analyze_spread


# --------------------------------------------------------------------------- #
# Presets: label -> RuleSet
# --------------------------------------------------------------------------- #
PRESETS = {
    "6-Deck H17 (Vegas Strip)": RuleSet(num_decks=6, dealer_hits_soft_17=True),
    "6-Deck S17": RuleSet(num_decks=6, dealer_hits_soft_17=False),
    "2-Deck S17 (Downtown)": RuleSet(num_decks=2, dealer_hits_soft_17=False),
    "8-Deck H17": RuleSet(num_decks=8, dealer_hits_soft_17=True),
    "Free Bet 6-Deck H17": RuleSet(num_decks=6, dealer_hits_soft_17=True, free_bet=True),
}
DEFAULT_PRESET = "6-Deck H17 (Vegas Strip)"

# Default bet spread: a 1-2-3-4-6-8 ramp keyed on true count.
DEFAULT_SPREAD = [
    {"tc": -1, "mult": 1},
    {"tc": 0, "mult": 1},
    {"tc": 1, "mult": 2},
    {"tc": 2, "mult": 3},
    {"tc": 3, "mult": 4},
    {"tc": 4, "mult": 6},
    {"tc": 5, "mult": 8},
]
DEFAULT_UNIT = 25.0
DEFAULT_BANKROLL = 10_000.0
DEFAULT_HPH = 100

# --------------------------------------------------------------------------- #
# Small styling helpers (intentionally minimal — polish comes later)
# --------------------------------------------------------------------------- #
CARD = {
    "background": "#ffffff", "border": "1px solid #e2e6ea", "borderRadius": "10px",
    "padding": "16px", "boxShadow": "0 1px 3px rgba(0,0,0,0.06)",
}
LABEL = {"fontWeight": 600, "fontSize": "13px", "color": "#33404d",
         "marginBottom": "4px", "display": "block"}
FIELD = {"marginBottom": "12px"}


def _field(label, control):
    return html.Div([html.Label(label, style=LABEL), control], style=FIELD)


def _metric(card_id, title, color):
    return html.Div([
        html.Div(title, style={"fontSize": "12px", "color": "#6b7785",
                               "textTransform": "uppercase", "letterSpacing": "0.04em"}),
        html.Div("—", id=card_id, style={"fontSize": "28px", "fontWeight": 700,
                                          "color": color, "marginTop": "4px"}),
    ], style={**CARD, "flex": "1", "minWidth": "150px", "textAlign": "center"})


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
app = Dash(__name__, title="Blackjack Bet-Spread Analyzer")
server = app.server


controls = html.Div([
    html.H3("Game & Spread", style={"marginTop": 0}),

    _field("Preset", dcc.Dropdown(
        id="preset", options=[{"label": k, "value": k} for k in PRESETS],
        value=DEFAULT_PRESET, clearable=False)),

    html.Div([
        html.Div(_field("Decks", dcc.Dropdown(
            id="decks", options=[{"label": str(d), "value": d} for d in (1, 2, 4, 6, 8)],
            value=6, clearable=False)), style={"flex": 1}),
        html.Div(_field("Dealer 17", dcc.Dropdown(
            id="h17", options=[{"label": "Hits soft 17 (H17)", "value": 1},
                               {"label": "Stands soft 17 (S17)", "value": 0}],
            value=1, clearable=False)), style={"flex": 1}),
    ], style={"display": "flex", "gap": "10px"}),

    html.Div([
        html.Div(_field("Blackjack pays", dcc.Dropdown(
            id="bjpays", options=[{"label": "3:2", "value": 1.5}, {"label": "6:5", "value": 1.2}],
            value=1.5, clearable=False)), style={"flex": 1}),
        html.Div(_field("Surrender", dcc.Dropdown(
            id="surrender", options=[{"label": "None", "value": "none"},
                                     {"label": "Late", "value": "late"},
                                     {"label": "Early", "value": "early"}],
            value="late", clearable=False)), style={"flex": 1}),
    ], style={"display": "flex", "gap": "10px"}),

    _field("Penetration (fraction of shoe dealt)", dcc.Input(
        id="penetration", type="number", value=0.75, min=0.5, max=0.95, step=0.05,
        style={"width": "100%"})),

    html.Details([
        html.Summary("Advanced rules", style={"cursor": "pointer", "fontWeight": 600,
                                              "fontSize": "13px", "color": "#33404d"}),
        html.Div([
            html.Div(_field("Double after split", dcc.Dropdown(
                id="das", options=[{"label": "Allowed", "value": 1}, {"label": "Not allowed", "value": 0}],
                value=1, clearable=False)), style={"flex": 1}),
            html.Div(_field("Resplit aces", dcc.Dropdown(
                id="rsa", options=[{"label": "Allowed", "value": 1}, {"label": "Not allowed", "value": 0}],
                value=0, clearable=False)), style={"flex": 1}),
        ], style={"display": "flex", "gap": "10px", "marginTop": "8px"}),
        html.Div([
            html.Div(_field("Dealer peeks (US)", dcc.Dropdown(
                id="peek", options=[{"label": "Yes (peek)", "value": 1},
                                    {"label": "No (European)", "value": 0}],
                value=1, clearable=False)), style={"flex": 1}),
            html.Div(_field("Max splits", dcc.Input(
                id="maxsplits", type="number", value=3, min=1, max=4, step=1,
                style={"width": "100%"})), style={"flex": 1}),
        ], style={"display": "flex", "gap": "10px"}),
    ], style={"marginBottom": "12px"}),

    html.Hr(),

    html.Div([
        html.Div(_field("Unit / min bet ($)", dcc.Input(
            id="unit", type="number", value=DEFAULT_UNIT, min=1, step=1,
            style={"width": "100%"})), style={"flex": 1}),
        html.Div(_field("Starting bankroll ($)", dcc.Input(
            id="bankroll", type="number", value=DEFAULT_BANKROLL, min=1, step=100,
            style={"width": "100%"})), style={"flex": 1}),
    ], style={"display": "flex", "gap": "10px"}),
    html.Div(id="bankroll-units-hint",
             style={"fontSize": "12px", "color": "#6b7785", "marginTop": "-6px",
                    "marginBottom": "12px"}),

    _field("Bet spread (true count → units)", dash_table.DataTable(
        id="spread-table",
        columns=[
            {"name": "True Count", "id": "tc", "type": "numeric"},
            {"name": "Multiplier (units)", "id": "mult", "type": "numeric"},
            {"name": "Bet ($)", "id": "amount", "type": "numeric", "editable": False},
        ],
        data=DEFAULT_SPREAD,
        editable=True,
        row_deletable=True,
        style_cell={"textAlign": "center", "fontFamily": "inherit", "padding": "6px"},
        style_header={"fontWeight": 600, "backgroundColor": "#f4f6f8"},
        style_data_conditional=[{"if": {"column_id": "amount"},
                                 "backgroundColor": "#f9fafb", "color": "#6b7785"}],
    )),
    html.Button("+ Add row", id="add-row", n_clicks=0,
                style={"marginBottom": "12px", "fontSize": "12px"}),

    html.Hr(),

    html.Div([
        html.Div(_field("Hands / hour", dcc.Input(
            id="hph", type="number", value=DEFAULT_HPH, min=10, max=400, step=10,
            style={"width": "100%"})), style={"flex": 1}),
        html.Div(_field("Hands / run", dcc.Input(
            id="nhands", type="number", value=2000, min=100, max=100000, step=500,
            style={"width": "100%"})), style={"flex": 1}),
        html.Div(_field("Runs", dcc.Input(
            id="nruns", type="number", value=500, min=10, max=1000, step=10,
            style={"width": "100%"})), style={"flex": 1}),
    ], style={"display": "flex", "gap": "10px"}),

    html.Button("Run Analysis", id="run", n_clicks=0, style={
        "width": "100%", "padding": "12px", "fontSize": "15px", "fontWeight": 600,
        "background": "#1f7a3d", "color": "white", "border": "none",
        "borderRadius": "8px", "cursor": "pointer", "marginTop": "4px"}),
], style={**CARD})


results = html.Div([
    html.Div([
        _metric("m-ev", "EV (% of action)", "#1f7a3d"),
        _metric("m-evhr", "EV ($/hour)", "#1f7a3d"),
        _metric("m-ror", "Risk of Ruin", "#b3261e"),
        _metric("m-n0", "N0 (hands)", "#33404d"),
    ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "16px"}),

    dcc.Loading(dcc.Graph(id="bankroll-chart", style={"height": "440px"}), type="default"),
    html.Div(id="run-note", style={"fontSize": "12px", "color": "#6b7785", "marginTop": "8px"}),
], style={**CARD})


app.layout = html.Div([
    html.H2("Blackjack Bet-Spread Analyzer",
            style={"marginBottom": "4px"}),
    html.Div("Evaluate a card-counting bet spread: EV, Risk of Ruin, N0, and bankroll trajectory.",
             style={"color": "#6b7785", "marginBottom": "18px"}),
    html.Div([
        html.Div(controls, style={"flex": "0 0 460px"}),
        html.Div(results, style={"flex": 1, "minWidth": "420px"}),
    ], style={"display": "flex", "gap": "18px", "alignItems": "flex-start"}),
], style={"maxWidth": "1180px", "margin": "0 auto", "padding": "24px",
          "fontFamily": "system-ui, -apple-system, 'Segoe UI', sans-serif",
          "color": "#1a232e", "background": "#eef1f4"})


# --------------------------------------------------------------------------- #
# Callbacks
# --------------------------------------------------------------------------- #
@app.callback(
    Output("decks", "value"), Output("h17", "value"), Output("bjpays", "value"),
    Output("surrender", "value"), Output("penetration", "value"),
    Output("das", "value"), Output("rsa", "value"), Output("peek", "value"),
    Output("maxsplits", "value"),
    Input("preset", "value"),
)
def apply_preset(name):
    r = PRESETS[name]
    return (r.num_decks, 1 if r.dealer_hits_soft_17 else 0, r.blackjack_pays,
            r.surrender, r.penetration, 1 if r.double_after_split else 0,
            1 if r.resplit_aces else 0, 1 if r.dealer_peeks else 0, r.max_splits)


@app.callback(
    Output("spread-table", "data"),
    Input("spread-table", "data"),
    Input("unit", "value"),
    Input("add-row", "n_clicks"),
    State("spread-table", "data"),
    prevent_initial_call=False,
)
def update_spread(data, unit, add_clicks, state_data):
    """Recompute the read-only $ column, and append a row on '+ Add row'."""
    rows = list(data or [])
    if ctx.triggered_id == "add-row":
        next_tc = (max((int(r.get("tc", 0)) for r in rows), default=0) + 1) if rows else 0
        rows.append({"tc": next_tc, "mult": 1})

    unit = float(unit or 0)
    changed = False
    for r in rows:
        try:
            mult = float(r.get("mult") or 0)
        except (TypeError, ValueError):
            mult = 0
        amount = round(unit * mult, 2)
        if r.get("amount") != amount:
            r["amount"] = amount
            changed = True

    if ctx.triggered_id == "add-row" or changed:
        return rows
    return no_update


@app.callback(
    Output("bankroll-units-hint", "children"),
    Input("bankroll", "value"), Input("unit", "value"),
)
def bankroll_hint(bankroll, unit):
    if not bankroll or not unit:
        return ""
    return f"= {bankroll / unit:.0f} units"


def _build_ruleset(decks, h17, bjpays, surrender, pen, das, rsa, peek, maxsplits, free_bet=False):
    return RuleSet(
        num_decks=int(decks), dealer_hits_soft_17=bool(h17),
        blackjack_pays=float(bjpays), surrender=surrender,
        penetration=float(pen), double_after_split=bool(das),
        resplit_aces=bool(rsa), dealer_peeks=bool(peek),
        max_splits=int(maxsplits), free_bet=free_bet,
    )


def _build_ramp(rows, unit):
    ramp = {}
    for r in rows:
        try:
            tc = int(r["tc"]); mult = float(r["mult"])
        except (KeyError, TypeError, ValueError):
            continue
        ramp[tc] = mult
    if not ramp:
        ramp = {0: 1}
    # Floor: counts below the lowest TC row bet that row's multiplier.
    lowest_tc = min(ramp)
    ramp[-99] = ramp[lowest_tc]
    return BetRamp(unit=float(unit), ramp=ramp)


@app.callback(
    Output("m-ev", "children"), Output("m-evhr", "children"),
    Output("m-ror", "children"), Output("m-n0", "children"),
    Output("bankroll-chart", "figure"), Output("run-note", "children"),
    Input("run", "n_clicks"),
    State("decks", "value"), State("h17", "value"), State("bjpays", "value"),
    State("surrender", "value"), State("penetration", "value"), State("das", "value"),
    State("rsa", "value"), State("peek", "value"), State("maxsplits", "value"),
    State("preset", "value"),
    State("spread-table", "data"), State("unit", "value"), State("bankroll", "value"),
    State("hph", "value"), State("nhands", "value"), State("nruns", "value"),
    prevent_initial_call=True,
)
def run_analysis(n_clicks, decks, h17, bjpays, surrender, pen, das, rsa, peek,
                 maxsplits, preset, spread_rows, unit, bankroll, hph, nhands, nruns):
    free_bet = PRESETS.get(preset, RuleSet()).free_bet
    rules = _build_ruleset(decks, h17, bjpays, surrender, pen, das, rsa, peek,
                           maxsplits, free_bet=free_bet)
    ramp = _build_ramp(spread_rows, unit)

    a = analyze_spread(
        rules, ramp,
        starting_bankroll=float(bankroll), n_hands=int(nhands), n_runs=int(nruns),
        hands_per_hour=int(hph),
    )

    ev_children = _value_with_ci(f"{a.ev_percent:+.3f}%", f"± {a.ev_percent_ci95:.3f}%")
    evhr_children = _value_with_ci(f"${a.ev_per_hour:+,.2f}", f"± ${a.ev_per_hour_ci95:,.2f}")
    ror_str = f"{a.risk_of_ruin * 100:.1f}%"
    n0_str = "∞" if a.n0 == float("inf") else f"{a.n0:,.0f}"

    fig = _make_figure(a)
    note = (f"{a.n_runs:,} runs × {a.n_hands:,} hands · "
            f"std dev ${a.std_dev_per_hand:,.0f}/hand · "
            f"EV shown with 95% confidence interval · "
            f"bands show 10th–90th percentile bankroll, line is the median.")
    return ev_children, evhr_children, ror_str, n0_str, fig, note


def _value_with_ci(value, ci):
    """Big metric value with a smaller, muted confidence-interval suffix."""
    return html.Span([
        value,
        html.Span(f"  {ci}", style={"fontSize": "14px", "fontWeight": 500,
                                     "color": "#6b7785"}),
    ])


def _make_figure(a):
    fig = go.Figure()
    if a.hand_axis:
        fig.add_trace(go.Scatter(
            x=a.hand_axis, y=a.pct_high, mode="lines", line=dict(width=0),
            name="90th pct", hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(
            x=a.hand_axis, y=a.pct_low, mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor="rgba(31,122,61,0.15)",
            name="10th–90th pct", hoverinfo="x+y"))
        fig.add_trace(go.Scatter(
            x=a.hand_axis, y=a.pct_median, mode="lines",
            line=dict(color="#1f7a3d", width=2.5), name="Median"))
        fig.add_hline(y=a.starting_bankroll, line_dash="dot",
                      line_color="#6b7785", annotation_text="Start")
    fig.update_layout(
        margin=dict(l=50, r=20, t=30, b=40),
        xaxis_title="Hands played", yaxis_title="Bankroll ($)",
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#eef1f4")
    fig.update_yaxes(gridcolor="#eef1f4", tickformat=",")
    return fig


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    # use_reloader=False: avoids the Werkzeug parent/child reloader spawning an
    # orphan process that keeps holding the port.
    app.run(debug=True, port=port, use_reloader=False)
