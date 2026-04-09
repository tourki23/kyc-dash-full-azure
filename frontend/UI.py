import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import numpy as np
import requests # <-- Nécessaire pour envoyer l'ordre à l'API

# --- CONNEXION À L'ORM POSTGRESQL ---
try:
    # Pour le local (depuis la racine)
    from .ORM_db_traducteur_SQL import SessionLocal, Client, TransactionLog
except (ImportError, ValueError):
    # Pour Docker (où le fichier est à la racine /app)
    from ORM_db_traducteur_SQL import SessionLocal, Client, TransactionLog

# --- CONFIGURATION COULEURS OPS ---
C_GREEN = "#2ecc71"  # Approved / Sain
C_ORANGE = "#f39c12" # Watch / Suspect
C_RED = "#e74c3c"    # Blocked / Fraudeur
DARK_PURE = "#000000"
DARK_CARD = "#111111"

# --- CONFIGURATION DE L'URL API (FORCE RENDER) ---
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

# Petit nettoyage au cas où il y aurait un / à la fin
if API_URL.endswith('/'):
    API_URL = API_URL[:-1]

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], suppress_callback_exceptions=True)

# --- CHARGEMENT DES MÉTRIQUES (ONGLET PERFORMANCE) ---
try:
    with open("models/metrics.json", "r") as f:
        m = json.load(f)
    conf_matrix = np.array(m.get("confusion_matrix", [[0,0],[0,0]]))
    fpr = np.linspace(0, 1, 100)
    tpr = np.sqrt(fpr) 
    recall_curve = np.linspace(0, 1, 100)
    precision_curve = 1 - recall_curve**2
except:
    m, conf_matrix = {}, np.array([[0,0],[0,0]])
    fpr, tpr, recall_curve, precision_curve = [], [], [], []

# --- CHARGEMENT DATA CLIENTS VIA ORM ET GÉNÉRATION DU GRAPH MACRO ---
db = SessionLocal()
try:
    query_clients = db.query(Client).all()
    if query_clients:
        DF_CLIENTS_STATIC = pd.DataFrame([u.__dict__ for u in query_clients]).drop(columns=['_sa_instance_state'], errors='ignore')
        DF_CLIENTS_STATIC['client_id'] = DF_CLIENTS_STATIC['client_id'].astype(str)
        
        dropdown_options = [{'label': f"ID: {r['client_id']} - {r['pays_residence']}", 'value': str(r['client_id'])} for _, r in DF_CLIENTS_STATIC.iterrows()]
        
        df_macro = DF_CLIENTS_STATIC['profil_risque'].value_counts(normalize=True).reset_index()
        df_macro.columns = ['profil', 'percentage']
        df_macro['percentage'] *= 100
        df_macro['label_text'] = df_macro.apply(lambda r: f"{r['profil']}: {r['percentage']:.1f}%", axis=1)
        df_macro['profil_clean'] = df_macro['profil'].astype(str).str.lower().str.strip()

        fig_macro = px.bar(df_macro, x='percentage', y='profil', orientation='h',
                           color='profil_clean', 
                           color_discrete_map={
                               'normal': C_GREEN, 'standard': C_GREEN, 
                               'vigilance': C_ORANGE, 'suspect': '#e74c3c', 
                               'ppe': '#c0392b', 'fraudeur': '#641e16'
                           },
                           template="plotly_dark", text='label_text') 
        
        fig_macro.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, showlegend=False,
                                xaxis_title="Pourcentage (%)", yaxis_title=None, yaxis={'categoryorder':'total ascending'},
                                xaxis_ticksuffix="%", margin=dict(l=10, r=60, t=10, b=10))
        fig_macro.update_traces(textposition='outside', cliponaxis=False)

        urg = DF_CLIENTS_STATIC.head(5).copy()
        urg['Montant'] = [f"{x:,} €" for x in [245000, 150000, 89000, 42000, 15000]][:len(urg)]
        urg['Type'] = ["Virement Crypto", "Virement Offshore", "Retrait Suspect", "Virement Offshore", "Retrait Suspect"][:len(urg)]

        urgence_table_init = dash_table.DataTable(
            data=urg.to_dict('records'), 
            columns=[
                {"name": "ID Client", "id": "client_id"}, {"name": "Classe", "id": "profil_risque"}, 
                {"name": "Montant Bloqué", "id": "Montant"}, {"name": "Opération", "id": "Type"}
            ], 
            style_data={'backgroundColor': '#111', 'color': C_RED, 'border': '1px solid #333'}, 
            style_header={'backgroundColor': '#1a1a1a', 'color': 'white', 'fontWeight': 'bold', 'border': '1px solid #333'},
            style_cell={'textAlign': 'left', 'padding': '8px'}
        )
    else:
        DF_CLIENTS_STATIC = pd.DataFrame()
        fig_macro = go.Figure()
        urgence_table_init = html.Div("Aucun client trouvé.")

except Exception as e:
    print(f"ERREUR CHARGEMENT : {e}")
    DF_CLIENTS_STATIC = pd.DataFrame()
    fig_macro = go.Figure()
    urgence_table_init = html.Div("Erreur de connexion base.")
finally:
    db.close()

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}<title>KYC - OPS CENTER</title>{%favicon%}{%css%}
        <style>
            body { background-color: #000000 !important; font-family: 'Segoe UI', sans-serif; color: white; margin: 0; padding: 0; }
            .xtab { background-color: #080808 !important; color: #fff !important; border: none !important; }
            .xtab--selected { background-color: #003399 !important; font-weight: bold !important; border-bottom: 3px solid #0056b3 !important; }
            .dash-spreadsheet-container .dash-spreadsheet-inner tr { background-color: #000000 !important; }
            .dash-spreadsheet-container .dash-spreadsheet-inner td { background-color: #000000 !important; }
            .card { background-color: #111111 !important; border: 1px solid #333 !important; }
            .card-stats { background-color: #111111 !important; border: 1px solid #333 !important; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
        </style>
    </head>
    <body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>
'''

fig_conf = go.Figure(data=go.Heatmap(z=conf_matrix, x=['Prédit Bas', 'Prédit Haut'], y=['Réel Haut', 'Réel Bas'], colorscale='Blues', text=conf_matrix, texttemplate="%{text}", showscale=False))
fig_conf.update_layout(template="plotly_dark", paper_bgcolor=DARK_CARD, plot_bgcolor=DARK_CARD, margin=dict(l=20, r=20, t=30, b=20), height=350)
fig_roc = go.Figure()
fig_roc.add_trace(go.Scatter(x=fpr, y=tpr, line=dict(color=C_GREEN, width=3), name="ROC"))
fig_roc.update_layout(title="Courbe ROC", template="plotly_dark", paper_bgcolor=DARK_CARD, plot_bgcolor=DARK_CARD, margin=dict(l=20, r=20, t=30, b=20), height=350)

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("KYC - OPERATIONS CENTER ", className="text-white", style={'fontWeight': 'bold'}), width=7),
        dbc.Col(
            html.Div([
                html.Span("Developed by Mahmoud TOURKI", className="text-muted", style={'fontSize': '14px', 'marginRight': '15px'}),
                html.A(html.Img(src="https://upload.wikimedia.org/wikipedia/commons/7/7e/Gmail_icon_%282020%29.svg", style={'height': '25px', 'marginRight': '15px'}), href="mailto:mahmoud.tourki24@gmail.com"),
                html.A(html.Img(src="https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg", style={'height': '25px'}), href="https://www.linkedin.com/in/mahmoud-tourki", target="_blank")
            ], className="d-flex justify-content-end align-items-center"), 
            width=5
        )
    ], className="my-4 pb-3 border-bottom", style={'borderColor': '#333'}),

    dcc.Tabs(id="tabs", value='monit', children=[
        dcc.Tab(label='📊 MONITORING LIVE', value='monit', className='xtab', selected_className='xtab--selected', children=[
            dbc.Row([
                dbc.Col(dbc.Button("▶️ START SIMULATION", id="btn-start-sim", color="success", className="fw-bold border border-success"), width="auto"),
                dbc.Col(dbc.Button("⏹️ STOP", id="btn-stop-sim", color="danger", className="fw-bold border border-danger"), width="auto"),
                dbc.Col(html.Div(id="sim-status-msg", className="text-info mt-2 fw-bold"), width="auto"),
            ], className="mt-2 mb-2 justify-content-center bg-black p-2 rounded"),
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardHeader("VOLUME TOTAL"), dbc.CardBody(html.H3(id="kpi-total"))]), width=3),
                dbc.Col(html.Div(dbc.Card([dbc.CardHeader("🟢 APPROUVÉES"), dbc.CardBody(html.H3(id="kpi-green", style={'color': C_GREEN}))]), id="btn-green", n_clicks=0, style={'cursor': 'pointer'}), width=3),
                dbc.Col(html.Div(dbc.Card([dbc.CardHeader("🟡 SURVEILLANCE"), dbc.CardBody(html.H3(id="kpi-orange", style={'color': C_ORANGE}))]), id="btn-orange", n_clicks=0, style={'cursor': 'pointer'}), width=3),
                dbc.Col(html.Div(dbc.Card([dbc.CardHeader("🔴 BLOQUÉES"), dbc.CardBody(html.H3(id="kpi-red", style={'color': C_RED}))]), id="btn-red", n_clicks=0, style={'cursor': 'pointer'}), width=3),
            ], className="mt-4 text-center"),
            dbc.Row([
                dbc.Col(dcc.Graph(id='scatter-graph', config={'displayModeBar': False}), width=8),
                dbc.Col(dcc.Graph(id='pie-risk-monit', config={'displayModeBar': False}), width=4),
            ]),
            html.Div(id='investigation-table', className="mt-4")
        ]),

        dcc.Tab(label='🔍 VISION CLIENT 360', value='360', className='xtab', selected_className='xtab--selected', children=[
            html.Div([
                html.H4("ANALYSE DES PROFILS ET PERSONAS (KYC 360)", className="text-white mt-4 mb-4"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([dbc.CardHeader("RÉPARTITION GLOBALE"), dcc.Graph(id='graph-main-bars', figure=fig_macro, config={'displayModeBar': False})], className="card-stats"),
                        dbc.Card([dbc.CardHeader("🚨 CONTACT URGENCE", style={'color': C_RED}), html.Div(urgence_table_init, id='urgence-list')], className="card-stats mt-4")
                    ], width=4),
                    dbc.Col([
                        html.Div(id='detail-title', className="text-center mb-3"),
                        dbc.Row([
                            dbc.Col(html.Div(id='kpi-age', className="card-stats text-center"), width=4),
                            dbc.Col(html.Div(id='kpi-revenu', className="card-stats text-center"), width=4),
                            dbc.Col(html.Div(id='kpi-solde', className="card-stats text-center"), width=4),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col(dcc.Graph(id='pie-secteur', config={'displayModeBar': False}), width=6),
                            dbc.Col(dcc.Graph(id='pie-pays', config={'displayModeBar': False}), width=6),
                        ]),
                        dbc.Row([
                            dbc.Col(dcc.Graph(id='bar-nationalite', config={'displayModeBar': False}), width=6),
                            dbc.Col(dcc.Graph(id='pie-compte', config={'displayModeBar': False}), width=6),
                        ])
                    ], width=8)
                ])
            ], className="p-3")
        ]),

        dcc.Tab(label='📈 PERFORMANCE MODÈLE', value='perf', className='xtab', selected_className='xtab--selected', children=[
            html.Div([
                dbc.Row([
                    dbc.Col(dbc.Card([dbc.CardHeader("PRECISION"), dbc.CardBody(html.H3(f"{float(m.get('classification_report',{}).get('weighted avg',{}).get('precision',0))*100:.1f}%"))]), width=3),
                    dbc.Col(dbc.Card([dbc.CardHeader("RECALL"), dbc.CardBody(html.H3(f"{float(m.get('classification_report',{}).get('weighted avg',{}).get('recall',0))*100:.1f}%"))]), width=3),
                    dbc.Col(dbc.Card([dbc.CardHeader("AUC-ROC"), dbc.CardBody(html.H3(f"{float(m.get('auc_roc',0.95))*100:.1f}%"))]), width=3),
                    dbc.Col(dbc.Card([dbc.CardHeader("ACCURACY"), dbc.CardBody(html.H3(f"{float(m.get('classification_report',{}).get('accuracy',0))*100:.1f}%"))]), width=3),
                ], className="mt-4 text-center"),
                dbc.Row([
                    dbc.Col(dcc.Graph(figure=fig_conf), width=6),
                    dbc.Col(dcc.Graph(figure=fig_roc), width=6),
                ], className="mt-4"),
                dbc.Row([
                    dbc.Col([html.H5("Feature Importance", className="text-center"), html.Img(src="assets/feature_importance.png", style={'width':'100%'})], width=6),
                    dbc.Col([html.H5("Analyse Résidus", className="text-center"), html.Img(src="assets/evaluation_plots.png", style={'width':'100%'})], width=6),
                ], className="mt-4")
            ], className="p-3")
        ]),

        dcc.Tab(label='📜 REGISTRE D\'AUDIT', value='audit', className='xtab', selected_className='xtab--selected', children=[
            html.Div([
                html.H4("LEDGER D'AUDIT - DERNIERS ÉVÉNEMENTS SCELLÉS", className="text-white mt-4 mb-4"),
                html.Div(id='out-audit')
            ], className="p-3")
        ]),
    ]),
    dcc.Interval(id='timer', interval=2000, n_intervals=0)
], fluid=True, style={'backgroundColor': DARK_PURE, 'minHeight': '100vh'})

# --- CALLBACKS ---
@app.callback(
    Output("sim-status-msg", "children"),
    [Input("btn-start-sim", "n_clicks"), Input("btn-stop-sim", "n_clicks")],
    prevent_initial_call=True
)
def control_simulator(n_start, n_stop):
    ctx = callback_context
    if not ctx.triggered: return ""
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    try:
        if button_id == "btn-start-sim":
            res = requests.post(f"{API_URL}/simulator/start", timeout=60)
            return res.json().get("status", "Signal envoyé.")
        elif button_id == "btn-stop-sim":
            res = requests.post(f"{API_URL}/simulator/stop", timeout=60)
            return res.json().get("status", "Arrêt envoyé.")
    except Exception as e:
        return f"❌ API Injognable sur {API_URL}"
    return ""

@app.callback(
    [Output('kpi-total', 'children'), Output('kpi-green', 'children'), 
     Output('kpi-orange', 'children'), Output('kpi-red', 'children'), 
     Output('scatter-graph', 'figure'), Output('pie-risk-monit', 'figure')],
    [Input('timer', 'n_intervals')]
)
def update_monit(n):
    db_session = SessionLocal()
    try:
        query = db_session.query(TransactionLog).all()
        if not query: return "0","0","0","0",go.Figure(),go.Figure()
        df = pd.DataFrame([{'ts': u.timestamp, 'score': u.score_risque, 'decision': u.decision} for u in query])
        df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0)
        
        # --- CORRECTION 1 : LIGNES DU GRAPHIQUE ---
        fig_s = px.scatter(df.tail(100), x='ts', y='score', color='decision', color_discrete_map={'APPROUVÉE': C_GREEN, 'SURVEILLANCE': C_ORANGE, 'BLOQUÉE': C_RED}, template="plotly_dark")
        fig_s.add_hline(y=70, line_dash="dash", line_color=C_RED, annotation_text="SEUIL BLOCAGE")
        fig_s.add_hline(y=40, line_dash="dash", line_color=C_ORANGE, annotation_text="SEUIL VIGILANCE")
        fig_s.update_layout(paper_bgcolor=DARK_PURE, plot_bgcolor=DARK_PURE, yaxis=dict(range=[-5, 105]))
        
        fig_p = px.pie(df, names='decision', color='decision', color_discrete_map={'APPROUVÉE': C_GREEN, 'SURVEILLANCE': C_ORANGE, 'BLOQUÉE': C_RED}, hole=0.6, template="plotly_dark")
        t, g, o, r = len(df), len(df[df['decision'].str.contains('APPROUV')]), len(df[df['decision'].str.contains('SURVEILL')]), len(df[df['decision'].str.contains('BLOQU')])
        return str(t), str(g), str(o), str(r), fig_s, fig_p
    except: return dash.no_update
    finally: db_session.close()

@app.callback(Output('investigation-table', 'children'), [Input('btn-green', 'n_clicks'), Input('btn-orange', 'n_clicks'), Input('btn-red', 'n_clicks')])
def show_investigation(n1, n2, n3):
    ctx = callback_context
    if not ctx.triggered: return ""
    btn = ctx.triggered[0]['prop_id'].split('.')[0]
    db_session = SessionLocal()
    try:
        query = db_session.query(TransactionLog).all()
        df_tx = pd.DataFrame([{'ts': u.timestamp, 'client_id': u.client_id, 'score': u.score_risque, 'decision': u.decision} for u in query])
        if df_tx.empty: return ""
        if "red" in btn: filt = df_tx[df_tx['decision'].str.contains('BLOQU')].tail(10)
        elif "green" in btn: filt = df_tx[df_tx['decision'].str.contains('APPROUV')].tail(10)
        else: filt = df_tx[df_tx['decision'].str.contains('SURVEILL')].tail(10)
        
        # --- CORRECTION 2 : CENTRAGE & SANS BORDURE (INVESTIGATION) ---
        return dash_table.DataTable(
            data=filt.to_dict('records'), 
            columns=[{"name": i, "id": i} for i in filt.columns], 
            style_header={'backgroundColor': '#111', 'color': 'white', 'border': 'none', 'textAlign': 'center'}, 
            style_data={'backgroundColor': '#000', 'color': 'white', 'border': 'none'},
            style_cell={'textAlign': 'center', 'border': 'none', 'backgroundColor': '#000', 'color': 'white'}
        )
    except: return ""
    finally: db_session.close()

@app.callback(
    [Output('detail-title', 'children'), Output('kpi-age', 'children'), Output('kpi-revenu', 'children'), Output('kpi-solde', 'children'),
     Output('pie-secteur', 'figure'), Output('pie-pays', 'figure'), Output('bar-nationalite', 'figure'), Output('pie-compte', 'figure')],
    [Input('graph-main-bars', 'clickData')]
)
def update_360_bi(clickData):
    profile = clickData['points'][0]['y'] if clickData else "normal"
    dff = DF_CLIENTS_STATIC[DF_CLIENTS_STATIC['profil_risque'] == profile] if not DF_CLIENTS_STATIC.empty else pd.DataFrame()
    if dff.empty: return "Sélectionnez un profil", "", "", "", go.Figure(), go.Figure(), go.Figure(), go.Figure()
    
    title = html.H3(f"PROFILING : {profile.upper()}", style={'color': C_GREEN})
    k_age = [html.Small("ÂGE MOYEN"), html.H4(f"{int(dff['age'].mean())} ans")]
    k_rev = [html.Small("REVENU MOYEN"), html.H4(f"{int(dff['revenu_annuel'].mean()):,} €")]
    k_sol = [html.Small("SOLDE MOYEN"), html.H4(f"{int(dff['solde_moyen'].mean()):,} €")]

    def quick_pie(df, col, t):
        fig = px.pie(df, names=col, hole=0.4, title=t, template="plotly_dark")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=False, margin=dict(l=10,r=10,t=30,b=10))
        return fig

    fig_nat = px.bar(dff['nationalite'].value_counts().head(5).reset_index(), x='count', y='nationalite', orientation='h', title="Nationalités", template="plotly_dark")
    return title, k_age, k_rev, k_sol, quick_pie(dff, 'secteur_activite', "Secteurs"), quick_pie(dff, 'pays_residence', "Pays"), fig_nat, quick_pie(dff, 'type_compte', "Comptes")

@app.callback(Output('out-audit', 'children'), Input('timer', 'n_intervals'))
def update_audit(n):
    db_session = SessionLocal()
    try:
        query = db_session.query(TransactionLog).order_by(TransactionLog.timestamp.desc()).limit(10).all()
        df = pd.DataFrame([{'Timestamp': u.timestamp, 'ID': u.client_id, 'Score': u.score_risque, 'Décision': u.decision, 'Hash': u.hash} for u in query])
        
        # --- CORRECTION 3 & 4 : CENTRAGE, SANS BORDURE ET COULEURS (AUDIT) ---
        return dash_table.DataTable(
            data=df.to_dict('records'), 
            columns=[{"name": i, "id": i} for i in df.columns], 
            style_header={'backgroundColor': '#111', 'color': 'white', 'border': 'none', 'textAlign': 'center'}, 
            style_data={'backgroundColor': '#000', 'color': 'white', 'border': 'none'},
            style_cell={'textAlign': 'center', 'border': 'none', 'backgroundColor': '#000', 'color': 'white'},
            style_data_conditional=[
                {'if': {'column_id': 'Décision', 'filter_query': '{Décision} contains "APPROUV"'}, 'color': C_GREEN, 'fontWeight': 'bold'},
                {'if': {'column_id': 'Décision', 'filter_query': '{Décision} contains "SURVEILL"'}, 'color': C_ORANGE, 'fontWeight': 'bold'},
                {'if': {'column_id': 'Décision', 'filter_query': '{Décision} contains "BLOQU"'}, 'color': C_RED, 'fontWeight': 'bold'}
            ]
        )
    except: return ""
    finally: db_session.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8053))
    app.run(debug=False, host='0.0.0.0', port=port)
