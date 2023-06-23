import pandas as pd
import plotly.express as px
from dash import ctx
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import json
import base64
from dashapp import figs

""" Renvoie la plus grande valeur dans l'ensemble d'un Data Frame  """
def GetMaxValueInDataFrame(data_frame: pd.DataFrame) -> float:
    return data_frame.max().max()


""" Renvoie la plus petite valeur dans l'ensemble d'un Data Frame  """
def GetMinValueInDataFrame(data_frame: pd.DataFrame) -> float:
    return data_frame.min().min()


""" Retourne une figure ainsi que la mémoire modifiée """
def Create_Fig(memory: dict) -> tuple:
    # On Charge les données pandas depuis notre fichier de config
    data = pd.read_csv(f'downloaded\\{memory["currently_uploaded_file"]}', sep=',', header=None, on_bad_lines='skip')[0:memory['config']['data_slicing']]

    # On récupère un certain % des données selon le data_sampling_ratio
    data = data[::memory['config']['data_sampling_ratio']]

    data = (data * float(memory['config']['coefficient'])).round(2)

    if memory['config']['timestamp_row'] is not None:
        data.set_index(memory['config']['timestamp_row'], inplace=True)

    if len(data.columns) == len(memory['config']['legend']):
        data.columns = [x['name'] for x in memory['config']['legend']]

    # On génère notre figure
    main_fig = px.line(data.loc[:, data.columns != memory['config']['timestamp_row']], template='plotly_white')

    # On fait en sorte que l'on puisse sélectionner des zones
    main_fig.update_layout(dragmode='select', selectdirection='h', plot_bgcolor='rgba(0, 0, 0, 0)', paper_bgcolor='rgba(0, 0, 0, 0)')

    # On met à jour les données de notre légende
    if len(data.columns) == len(memory['config']['legend']):
        for i, d in enumerate(main_fig.data):
            d.line['dash'] = memory['config']['legend'][i]['line-style']
            d.line['color'] = memory['config']['legend'][i]['line-color']

    # On la stocke dans notre cache
    figs[memory['session_id']][0][0] = main_fig

    # On stocke l'ordonnée minimale et maximale
    memory['max_data'] = GetMaxValueInDataFrame(data.loc[:, data.columns != memory['config']['timestamp_row']]) + 1000
    memory['min_data'] = GetMinValueInDataFrame(data.loc[:, data.columns != memory['config']['timestamp_row']]) - 1000

    return main_fig, memory


""" Renvoie l'index du bouton (accessoirement l'index du label) qui a été pressé (Déclenche une PreventUpdate si le contexte est invalide)  """
def Get_Label_Index_From_CTX(memory: dict) -> int:
    if not ctx.triggered_prop_ids:
        raise PreventUpdate

    try:
        index = ctx.triggered_prop_ids[list(ctx.triggered_prop_ids.keys())[0]]['index']
    except TypeError:  # Il est possible que le contexte soit invalide. Dans ce cas, on renvoie -1
        raise PreventUpdate

    # Trouve un label avec un index correspondant
    for j, label in enumerate(memory['all_labels']):
        if label['id'] == index:
            return j


""" Renvoi un objet de type figure avec toutes les zones colorées et les annotations """
def Update_Fig(memory: dict) -> go.Figure:
    # On récupère notre figure depuis le cache
    figure: go.Figure = figs[memory['session_id']][0][0]

    # Dessine les zones sur notre figure
    shape_list = []

    for label in memory['all_labels']:
        shape_list.append(dict(type="rect", xref="x", yref="y", x0=str(label["positions"][0]), y0=memory['max_data'],
                               x1=str(label["positions"][1]), y1=memory['min_data'], fillcolor=label["color"],
                               opacity=0.4,
                               line_width=0, layer="below"))

    # Ajoute les annotations sur notre figure
    annotation_list = []

    # Si les annotations sont activées alors on les affiche sinon, on ne les affiche pas
    if memory['annotations_visible']:
        for label in memory['all_labels']:
            annotation_list.append(dict(x=int((label["positions"][0] + label["positions"][1]) / 2), y=memory['max_data'],
                                        text=f"{label['label']} ({label['id']})",
                                        font=dict(family="Helvetica", size=16, color="#000000"), align="center",
                                        bordercolor="#c7c7c7", borderwidth=2, borderpad=4, bgcolor="#ff7f0e", opacity=0.8))
    else:
        annotation_list.append(dict(x=0, y=0, text='', opacity=0))

    # Cependant, s'il n'y aucun label (donc aucun shape) il est impératif de mettre un shape par défaut (invisible) car sinon la figure n'est pas mise à jour
    if not shape_list:
        shape_list.append(dict(type="rect", x0=0, y0=0, x1=0, y1=0, opacity=0))
        annotation_list.append(dict(x=0, y=0, text='', opacity=0))

    currently_visible_data_range = memory['current_visible_data_range']

    # On met à jour notre figure
    figure.update_layout(shapes=shape_list, annotations=annotation_list, dragmode="select", selectdirection='h', xaxis=dict(range=currently_visible_data_range[0], autorange=currently_visible_data_range[2]), yaxis=dict(range=currently_visible_data_range[1], autorange=currently_visible_data_range[2]))

    return figure


""" Génère une chaine de caractère JSON de toutes les données nécessaires à la sauvegarde """
def Generate_Save_Content(memory: dict) -> str:
    output = {
        'config': memory['config'],  # Sauvegarde la configuration dans notre fichier de sortie,
        'file_name': memory['currently_uploaded_file'],
        'labels': {}  # Les labels (zones) que nous avons créé
    }

    # Sauvegarde nos zones dans le fichier de sortie
    for j, label in enumerate(memory['all_labels']):
        output['labels'][j] = label

    return json.dumps(output)


""" Renvoie une chaine de caractère à partir d'une chaine de caractère encodée en base 64 """
def Decode_Str(content: str) -> str:
    if content is None:
        raise PreventUpdate

    byte_decoded_content = base64.b64decode(content.split(',')[1])
    decoded = byte_decoded_content.decode('utf-8')

    return decoded


""" Permet de s'assurer que deux label ne se superpose jamais """
def Collapse_Labels(memory: dict, label_index, children: list) -> tuple:
    all_labels = memory['all_labels']  # On récupère nos labels
    label = all_labels[label_index]  # Le label par rapport auquel on effectue notre vérification
    label_pos = label['positions']  # Sa position

    indexes_to_delete = []  # La liste des index des labels qu'il faudra supprimer (on ne les supprime pas maintenant pour éviter les conflits)

    for j, _label in enumerate(all_labels):
        if j == label_index:
            continue

        # On récupère la position de l'autre label
        _label_pos = _label['positions']

        # Si ce label est englobé par l'autre label alors on l'ajoute à la liste des labels à supprimer
        if label_pos[0] < _label_pos[0] < label_pos[1] and label_pos[0] < _label_pos[1] < label_pos[1]:
            indexes_to_delete.append(j)

            continue

        # Si notre nouveau label déborde sur le début d'un autre label
        if _label_pos[0] < label_pos[1] < _label_pos[1]:
            # On dimensionne les deux en leur enlevant chacun la même quantité d'espace
            intersection_middle = (label_pos[1] + _label_pos[0]) / 2

            label_pos[1], _label_pos[0] = intersection_middle, intersection_middle
        elif _label_pos[0] < label_pos[0] < _label_pos[1]:  # Cas inverse, notre nouveau label déborde sur la fin d'un autre label
            # Alors, on effectue la même chose sur les deux labels
            intersection_middle = (label_pos[0] + _label_pos[1]) / 2

            label_pos[0], _label_pos[1] = intersection_middle, intersection_middle

        # On demande une mise à jour pour les deux
        _label['updated'], label['updated'] = 0, 0

    # On supprime tous les labels qu'il faut supprimer (dans l'ordre inverse pour éviter les conflits)
    for index in sorted(indexes_to_delete, reverse=True):
        all_labels.pop(index)
        children.pop(index)
        memory['edit']['precedent_clicks'].pop(index)

    # On met à jour notre mémoire
    memory['all_labels'] = all_labels

    return memory, children


""" Permet de supprimer toutes les boites de sélection d'une figure """
def clear_selection(self):
    if 'selections' in self['layout']:
        self['layout']['selections'] = ()


go.Figure.clear_selection = clear_selection  # On implémente la méthode clear_selection
