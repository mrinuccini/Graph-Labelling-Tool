from dash import dash, html
import json
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc

default_all_labels = []  # Une liste qui contient tous les labels crée par l'utilisateur
default_figs = []  # Contient l'ensemble des figures de notre application sous forme de figure plotly
default_currently_selected_data_range = None  # Contient la zone actuellement sélectionnée par l'utilisateur
default_config = json.load(open('data/ECG_config.json', 'r'))  # Configuration par défaut
default_data = pd.read_csv(f'downloaded\\{default_config["data-file"]}', sep=',', header=None, on_bad_lines='skip')[0:default_config['data_slicing']]  # Les données sur notre graphique par défaut

# Si une colonne correspond au timestamp
if default_config['timestamp_row'] is not None:
    default_data.set_index(default_config['timestamp_row'], inplace=True)  # On la met comme colonne des index

# On récupère un certain % des données selon le data_sampling_ratio
default_data = default_data[::default_config['data_sampling_ratio']]
default_data = (default_data * float(default_config['coefficient'])).round(2)
default_data.columns = [x['name'] for x in default_config['legend']]

def Get_Default_Fig():
    default_fig = px.line(default_data.loc[:, default_data.columns != default_config['timestamp_row']],
                          template='plotly_white')
    default_fig.update_layout(dragmode='select', selectdirection='h', plot_bgcolor='rgba(0, 0, 0, 0)',
                              paper_bgcolor='rgba(0, 0, 0, 0)')

    for i, d in enumerate(default_fig.data):
        d.line['dash'] = default_config['legend'][i]['line-style']
        d.line['color'] = default_config['legend'][i]['line-color']

    return default_fig


# On génère la figure qui sera sur la page par défaut
default_figs.append(Get_Default_Fig())

# Un dictionnaire contenant comme clé des ID de session avec leur figure correspondant (les figures sont stockées ici et non dans le dcc.Store, car elles sont trop volumineuses)
figs = {

}

app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    dash.page_container
])
