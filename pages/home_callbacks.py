import random

from dash import Output, Input, State, html, dcc, ALL, no_update
from dash.exceptions import PreventUpdate
import time
import uuid
import json
from dashapp import app, figs, Get_Default_Fig
from functions import Update_Fig, Collapse_Labels, Get_Label_Index_From_CTX, Generate_Save_Content, Decode_Str, Create_Fig
import plotly.graph_objs as go
import os
from operator import itemgetter
import filecmp

@app.callback(
    Output('figs_interval_cleaner', 'n_intervals'),
    Input('figs_interval_cleaner', 'n_intervals')
)
def Figs_Interval_Cleaner(n_intervals: int) -> int:  # Est appelé périodiquement toutes les minutes pour vérifier si des ID de sessions ont expiré
    # On récupère le temps actuel
    current_time = time.time()
    sessions_to_pop = []

    # Pour chaque session
    for session in figs:
        # On calcule depuis combien de temps elle existe
        session_time = figs[session][1]
        delta = current_time - session_time

        # Si elle existe depuis plus de 24 heures alors on l'ajoute à la liste des sessions à supprimer
        if delta > 86400:
            sessions_to_pop.append(session)

    # On supprime toutes les sessions à supprimer
    for session_to_pop in sessions_to_pop:
        figs.pop(session_to_pop)
        print(f"Cleared session : {session_to_pop}")

    return n_intervals


@app.callback(
    [Output('memory', 'data'), Output('session_id_div', 'children'), Output('fig', 'figure')],
    Input('session_id_div', 'children'),
    State('memory', 'data')
)
def On_Page_Loaded(children, memory: dict) -> tuple:  # Appelé lorsque la page est chargé, utilisé pour générer une ID de session
    # Si nous n'avons pas encore créé d'id de session
    if memory['session_id'] == '':
        # On crée un id de session puis on lui assigne une figure
        memory['session_id'] = str(uuid.uuid4())
        figs[memory['session_id']] = [[Get_Default_Fig()], time.time()]

    return memory, f'Session ID : {memory["session_id"]}', Update_Fig(memory)


@app.callback(
    [Output('test', 'children', allow_duplicate=True), Output('memory', 'data', allow_duplicate=True), Output('fig', 'figure', allow_duplicate=True), Output('label_div', 'children', allow_duplicate=True)],
    Input('fig', 'relayoutData'),
    [State('memory', 'data'), State('label_div', 'children')],
    prevent_initial_call=True
)
def On_Graph_Area_Selected(relayout_data, memory: dict, children) -> tuple:  # Appelé lorsque l'utilisateur change la zone sélectionnée du graphique
    if relayout_data is None or not relayout_data:  # Si on reçoit une valeur None (initial call) ou une liste vide (?) alors on empêche la mise à jour du layout
        raise PreventUpdate

    # On récupère la zone sélectionnée en fonction du format dans lequel elle nous est donnée
    if 'selections' in relayout_data:  # Pour les sélections faites par l'utilisateur
        if not relayout_data['selections']:
            raise PreventUpdate

        x0 = int(relayout_data['selections'][0]['x0'])
        x1 = int(relayout_data['selections'][0]['x1'])
    elif 'selections[0].x0' in relayout_data:  # Pour les sélections faites lorsqu'on modifie
        x0 = int(relayout_data['selections[0].x0'])
        x1 = int(relayout_data['selections[0].x1'])
    elif 'xaxis.range[0]' in relayout_data:  # Pour les sélections de zoom
        # On récupère le zoom
        x_range = (relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]'])
        y_range = (relayout_data['yaxis.range[0]'], relayout_data['yaxis.range[1]'])

        # On les stocke dans la mémoire
        memory['current_visible_data_range'] = (x_range, y_range, False)

        return f"Selected area : {memory['currently_selected_data_range']}", memory, no_update, no_update
    elif 'xaxis.autorange' in relayout_data:  # Lorsqu'on active l'autoscale ou qu'on quitte le mode de zoom
        memory['current_visible_data_range'] = ((0, 0), (0, 0), relayout_data['xaxis.autorange'])

        return f"Selected area : {memory['currently_selected_data_range']}", memory, no_update, no_update
    else:  # Sinon, on empêche la mise à jour de l'application
        raise PreventUpdate

    # Si les valeurs sont inversées (fin = debut et début = fin) alors on les retourne
    if x1 < x0:
        x0, x1 = x1, x0

    # On sauvegarde la zone actuellement sélectionnée dans la mémoire
    memory['currently_selected_data_range'] = (x0, x1)

    # Si on est en train de modifier un label
    if memory['edit']['is_editing']:
        # On modifie le label
        memory['all_labels'][memory['edit']['editing_id'][0]]['positions'] = [x0, x1]

        # On demande une mise à jour de label (pour que les inputs START et END soient mises à jour)
        memory['all_labels'][memory['edit']['editing_id'][0]]['updated'] = 0

        # On s'assure que deux labels ne se chevauche jamais
        memory, children = Collapse_Labels(memory, memory['edit']['editing_id'][0], children)

        # On récupère le nouvel index de notre label grâce à son ID
        for i, label in enumerate(memory['all_labels']):
            if label['id'] == memory['edit']['editing_id'][1]:
                memory['edit']['editing_id'][0] = i
                break

        # On efface la sélection actuelle pour la retracer à la nouvelle taille
        figs[memory['session_id']][0][0].clear_selection()
        figs[memory['session_id']][0][0].add_selection(x0=memory['all_labels'][memory['edit']['editing_id'][0]]['positions'][0], y0=memory['max_data'], x1=memory['all_labels'][memory['edit']['editing_id'][0]]['positions'][1], y1=memory['min_data'])

        return f"Selected area : {memory['currently_selected_data_range']}", memory, Update_Fig(memory), children

    return f"Selected area : {memory['currently_selected_data_range']}", memory, no_update, no_update


@app.callback(
    [Output('label_div', 'children', allow_duplicate=True), Output('confirm_no_area_selected', 'displayed'),
     Output('memory', 'data', allow_duplicate=True)],
    Input('add_label_button', 'n_clicks'),
    [State('label_div', 'children'), State('memory', 'data')],
    prevent_initial_call=True
)
def Add_Label(n_clicks, old_children: list, memory: dict) -> tuple:  # Callback exécuté lorsque l'utilisateur appuie sur le bouton pour créer un nouveau label
    # S'il s'agit de l'appel initial, on empêche la mise à jour
    if n_clicks is None:
        raise PreventUpdate

    # Si aucune plage de donnée n'est sélectionnée, on ne met pas à jour le contenu et on affiche un pop-up pour en informer l'utilisateur
    if memory['currently_selected_data_range'] is None:
        return old_children, True, memory

    # La liste de tous les labels
    labels = [label for label in memory['config']["labels"]]

    # On ajoute le nouveau label créé au back-end
    memory['all_labels'].append({
        'id': n_clicks - 1,  # l'id de notre label
        'label': labels[0],  # A quel label correspond t'il
        'positions': memory['currently_selected_data_range'],  # Les positions de début et de fin de notre label
        'color': memory['config']["labels"][labels[0]]['color'],  # La couleur de notre label
        'updated': 2  # Le statut du label par rapport à l'interface. 0 : L'interface n'est pas à jour par rapport au label. 1 : L'interface est partiellement à jour par rapport au label. 2 : L'interface est à jour, peut être même plus à jour que le label
    })

    memory, old_children = Collapse_Labels(memory, len(memory['all_labels']) - 1, old_children)

    # On trie notre liste de label en fonction de leur position
    memory['all_labels'] = sorted(memory['all_labels'], key=itemgetter('positions'))

    # Comme on vient de trier notre liste, on récupère le nouvel index du label
    new_label_index = 0

    for i, x in enumerate(memory['all_labels']):
        if x['id'] == n_clicks - 1:
            new_label_index = i
            break

    memory['edit']['precedent_clicks'].append(None)

    # On efface la boite de sélection
    memory['currently_selected_data_range'] = None
    figs[memory['session_id']][0][0].clear_selection()

    # On met à jour l'interface graphique de l'application
    old_children.insert(new_label_index, html.Div(style={'height': '50px', 'width': '100vw', 'display': 'flex', 'justify-content': 'left'}, children=[
            html.P(str(n_clicks - 1), style={'height': 'inherit'}),
            dcc.Dropdown(labels, labels[0], id={"type": "label_selector_dropdown", "index": n_clicks - 1}, className="dropdown"),
            dcc.Input(type="text", value=memory['all_labels'][-1]['positions'][0], id={"type": "start_selector_input", "index": n_clicks - 1}, className='input', style={"height": '25px'}),
            dcc.Input(type="text", value=memory['all_labels'][-1]['positions'][1], id={"type": "end_selector_input", "index": n_clicks - 1}, className='input', style={"height": '25px'}),
            html.Button(children=[html.Img(src='../assets/icons/delete.png', alt='del icon'), 'Delete'], id={"type": "delete_label_button", "index": n_clicks - 1}, className="labelActionButton"),
            html.Button(children=[html.Img(src='../assets/icons/edit.png', alt='edit icon'), 'Edit'], id={"type": "edit_button", "index": n_clicks - 1}, className='labelActionButton')
    ], id={"type": "label_div_child", "index": n_clicks - 1}))

    # On ajoute le nouveau label créé au front-end
    return old_children, False, memory


@app.callback(
    [Output('fig', 'figure', allow_duplicate=True), Output('memory', 'data', allow_duplicate=True)],
    Input({'type': 'label_selector_dropdown', 'index': ALL}, 'value'),
    State('memory', 'data'),
    prevent_initial_call=True
)
def On_Label_Type_Changed(values, memory: dict) -> tuple:  # Ce callback est appelé lorsque l'utilisateur change le type de label dans le menu déroulant
    # Met à jour le type de label
    for j, value in enumerate(values):
        memory['all_labels'][j]['label'] = value
        memory['all_labels'][j]['color'] = memory['config']["labels"][value]['color']

    return Update_Fig(memory), memory


@app.callback(
    [Output('fig', 'figure', allow_duplicate=True), Output({'type': 'start_selector_input', 'index': ALL}, 'value'),
     Output('memory', 'data', allow_duplicate=True)],
    Input({'type': 'start_selector_input', 'index': ALL}, 'value'),
    State('memory', 'data'),
    prevent_initial_call=True
)
def On_Label_Start_Input_Changed(values, memory: dict) -> tuple:  # Appelé lorsque l'utilisateur change la position de départ d'un label
    # Met à jour la valeur de début dans la liste de label interne
    for j, value in enumerate(values):
        if memory['all_labels'][j]['updated'] == 2:  # Si le label n'est pas à jour par rapport à notre entrée alors on met à jour les données du label
            memory['all_labels'][j]['positions'] = (int(value), memory['all_labels'][j]['positions'][1])
        else:  # Sinon, si l'entrée n'est pas à jour par rapport au label, on met à jour l'entrée
            values[j] = memory['all_labels'][j]['positions'][0]
            memory['all_labels'][j]['updated'] += 1  # On dit qu'une itération de la mise à jour a été effectué (il en faut 2 pour les entrées "Start" et "End")

    return Update_Fig(memory), values, memory


@app.callback(
    [Output('fig', 'figure', allow_duplicate=True), Output({'type': 'end_selector_input', 'index': ALL}, 'value'),
     Output('memory', 'data', allow_duplicate=True)],
    Input({'type': 'end_selector_input', 'index': ALL}, 'value'),
    State('memory', 'data'),
    prevent_initial_call=True
)
def On_Label_End_Input_Changed(values, memory: dict) -> tuple:  # Appelé lorsque l'utilisateur change la position de fin d'un label
    # Met à jour la valeur de fin dans la liste de label interne
    for j, value in enumerate(values):
        if memory['all_labels'][j]['updated'] == 2:  # Si le label n'est pas à jour par rapport à notre entrée alors on met à jour les données du label
            memory['all_labels'][j]['positions'] = (memory['all_labels'][j]['positions'][0], int(value))
        else:  # Sinon, si l'entrée n'est pas à jour par rapport au label, on met à jour l'entrée
            values[j] = memory['all_labels'][j]['positions'][1]
            memory['all_labels'][j]['updated'] += 1  # On dit qu'une itération de la mise à jour a été effectué (il en faut 2 pour les entrées "Start" et "End")

    return Update_Fig(memory), values, memory


@app.callback(
    [Output('fig', 'figure', allow_duplicate=True), Output('label_div', 'children', allow_duplicate=True),
     Output('memory', 'data', allow_duplicate=True)],
    Input({'type': 'delete_label_button', 'index': ALL}, 'n_clicks'),
    [State('label_div', 'children'), State('memory', 'data')],
    prevent_initial_call=True
)
def On_Delete_Button_Pressed(n_clicks, children, memory: dict) -> tuple:  # Appelé lorsque le bouton "Delete" est appuyé
    # On trouve quel bouton a été pressée
    current_label_index = Get_Label_Index_From_CTX(memory)
    current_n_clicks = n_clicks[current_label_index]

    # S'il s'agit de l'appel initial ou qu'aucune zone n'est sélectionnée alors on empêche la mise à jour de l'application
    if current_n_clicks is None or current_n_clicks == 0:
        raise PreventUpdate

    if memory['edit']['is_editing'] and memory['edit']['editing_id'][0] > current_label_index:
        memory['edit']['editing_id'][0] -= 1

    # Si l'on est actuellement en train de modifier le label que l'on veut supprimer alors on quitte le mode de modifiation
    if memory['edit']['is_editing'] and memory['edit']['editing_id'][0] == current_label_index:
        figs[memory['session_id']][0][0].clear_selection()
        memory['edit']['is_editing'] = False

    # On supprime le label
    memory['all_labels'].pop(current_label_index)
    memory['edit']['precedent_clicks'].pop(current_label_index)
    children.pop(current_label_index)

    return Update_Fig(memory), children, memory


@app.callback(
    Output('save_data', 'data'),
    Input('save_data_button', 'n_clicks'),
    State('memory', 'data'),
    prevent_initial_call=True
)
def On_Save_Button_Pressed(n_clicks, memory: dict) -> dict:  # Appelé lorsque le bouton Save est pressé
    file_content = Generate_Save_Content(memory)

    return dict(content=file_content, filename=f'{memory["currently_uploaded_file"].split(".")[0]}_labels.json')


@app.callback(
    [Output('fig', 'figure', allow_duplicate=True), Output('label_div', 'children', allow_duplicate=True),
     Output('add_label_button', 'n_clicks'), Output('memory', 'data', allow_duplicate=True), Output('upload_file_not_found_modal', 'is_open'), Output('upload_file_not_found_modal_body', 'children')],
    Input('upload_save_file', 'contents'),
    [State('memory', 'data'), State('add_label_button', 'n_clicks'), State('upload_file_not_found_modal_body', 'children')],
    prevent_initial_call=True
)
def On_Save_File_Uploaded(content: str, memory: dict, current_n_clicks, modal_body_children: list) -> tuple:  # Appelé lorsqu'un précédent fichier de donnée est chargé
    # On décode le contenu du fichier
    decoded = Decode_Str(content)
    content_dict = json.loads(decoded)  # Puis, on l'ouvre sous forme d'un dictionnaire

    # On regarde si le fichier de donnée existe, si oui on continue l'exécution sinon on affiche une boite de dialogue demandant de le télécharger
    if not os.path.exists(f'downloaded\\{content_dict["file_name"]}'):
        modal_body_children[0] = f'Impossible to find the data file {content_dict["file_name"]} referenced in the loaded file. Please load it using the upload box below and make sure the file you upload has the name : {content_dict["file_name"]}'

        return figs[memory['session_id']][0][0], no_update, current_n_clicks, memory, True, modal_body_children

    # On récupère la configuration
    memory['config'] = content_dict['config']

    # On charge les labels
    memory['all_labels'].clear()
    memory['edit']['precedent_clicks'].clear()
    memory['currently_selected_data_range'] = None

    memory['currently_uploaded_file'] = content_dict['file_name']

    for label in content_dict['labels']:
        memory['all_labels'].append(content_dict['labels'][label])
        memory['edit']['precedent_clicks'].append(None)

    # On crée notre figure
    memory = Create_Fig(memory)[1]

    new_children = []

    labels = [label for label in memory['config']["labels"]]

    # On régénère le contenu du div qui stocke notre liste de label
    for label in memory['all_labels']:
        new_children.append(
            html.Div(style={'height': '50px', 'width': '100vw', 'display': 'flex', 'justify-content': 'left'},
                     children=[
                         html.P(str(label['id']), style={'height': 'inherit'}),
                         dcc.Dropdown(labels, label['label'], id={"type": "label_selector_dropdown", "index": label['id']},
                                      className="dropdown"),
                         dcc.Input(type="text", value=label['positions'][0],
                                   id={"type": "start_selector_input", "index": label['id']}, className='input',
                                   style={"height": '25px'}),
                         dcc.Input(type="text", value=label['positions'][1],
                                   id={"type": "end_selector_input", "index": label['id']}, className='input',
                                   style={"height": '25px'}),
                         html.Button(children=[html.Img(src='../assets/icons/delete.png', alt='del icon'), 'Delete'],
                                     id={"type": "delete_label_button", "index": label['id']},
                                     className="labelActionButton"),
                         html.Button(children=[html.Img(src='../assets/icons/edit.png', alt='edit icon'), 'Edit'],
                                     id={"type": "edit_button", "index": label['id']}, className='labelActionButton')]))

    return Update_Fig(memory), new_children, max([x['id'] for x in memory['all_labels']]) + 1, memory, False, modal_body_children


@app.callback(
    Output('fig', 'figure', allow_duplicate=True),
    Input('selection_mode_button', 'n_clicks'),
    State('memory', 'data'),
    prevent_initial_call=True
)
def Trigger_Selection_Mode(n_clicks, memory: dict) -> go.Figure:  # Appelé lorsqu'on appuie sur le bouton pour passer en mode zoom
    figure: go.Figure = figs[memory['session_id']][0][0]

    currently_visible_data_range = memory['current_visible_data_range']

    # On active le mode sélection tout en conservant le zoom
    figure.update_layout(dragmode='select', selectdirection='h', xaxis=dict(range=currently_visible_data_range[0], autorange=currently_visible_data_range[2]), yaxis=dict(range=currently_visible_data_range[1], autorange=currently_visible_data_range[2]))

    return figure


@app.callback(
    [Output('fig', 'figure', allow_duplicate=True), Output('memory', 'data', allow_duplicate=True)],
    Input('annotation_mode_button', 'n_clicks'),
    State('memory', 'data'),
    prevent_initial_call=True
)
def Disable_Annotations_Button(n_clicks, memory: dict) -> tuple:  # Appelé lorsque le bouton pour désactiver les annotations est cliqué
    # On active / désactive les annotations dans la mémoire
    memory['annotations_visible'] = not memory['annotations_visible']

    # On met à jour la figure
    return Update_Fig(memory), memory


@app.callback(
    [Output('fig', 'figure', allow_duplicate=True), Output('memory', 'data', allow_duplicate=True), Output('label_div', 'children', allow_duplicate=True)],
    Input('upload_config_file', 'contents'),
    [State('memory', 'data'), State('label_div', 'children')],
    prevent_initial_call=True
)
def On_Config_File_Uploaded(content: str, memory: dict, children: list) -> tuple:  # Appelé lorsqu'on charge un fichier de config custom
    # On décode le contenu du fichier
    decoded_content = Decode_Str(content)
    content_dict = json.loads(decoded_content)

    # S'il ne contient pas les mêmes labels que l'ancien fichier de config alors on efface la liste des labels crée
    if memory['config']['labels'] != content_dict['labels']:
        memory['all_labels'].clear()
        children.clear()

    # On charge la config dans la mémoire
    memory['config'] = content_dict

    # On crée notre figure
    memory = Create_Fig(memory)[1]

    # Puis, on effectue les mises à jour
    return Update_Fig(memory), memory, children


@app.callback(
    [Output('fig', 'figure', allow_duplicate=True), Output('memory', 'data', allow_duplicate=True), Output('confirm_file_already_exist', 'displayed')],
    Input('upload_data_file', 'contents'),
    [State('upload_data_file', 'filename'), State('memory', 'data')],
    prevent_initial_call=True
)
def On_Data_File_Uploaded(content, filename, memory) -> tuple:  # Appelé lorsque l'utilisateur charge un fichier de donnée
    # On décode le contenu du fichier
    decoded_content = Decode_Str(content)
    decoded_content = os.linesep.join([s for s in decoded_content.splitlines() if s])
    file_name = '.'.join(filename.split('.')[:-1])

    # On l'enregistre, pour pouvoir le recharger lorsque l'utilisateur chargera un fichier de sauvegarde qui a utilisé ce fichier de données
    if not os.path.exists(f"downloaded\\{filename}"):
        open(f"downloaded\\{filename}", 'w').write(decoded_content)
    else:
        # On enregistre le fichier de manière temporaire
        temp = 'temp_' + str(uuid.uuid4())

        open(f"downloaded\\{temp}", 'w').write(decoded_content)

        # On regarde si le fichier avec le même nom contient le même contenu
        if not filecmp.cmp(f"downloaded\\{temp}", f'downloaded\\{filename}'):
            # Sinon, on demande à l'utilisateur de changer le nom de son fichier
            os.remove(f"downloaded\\{temp}")
            return no_update, no_update, True

        # Si oui, on continue normalement en utilisant cet ancien fichier
        os.remove(f"downloaded\\{temp}")

    # On sauvegarde son nom dans notre mémoire
    memory['currently_uploaded_file'] = filename

    # On recrée la figure
    memory = Create_Fig(memory)[1]

    return Update_Fig(memory), memory, False


@app.callback(
    Output('upload_file_not_found_modal', 'is_open', allow_duplicate=True),
    Input('upload_missing_data_file', 'contents'),
    [State('upload_missing_data_file', 'filename')],
    prevent_initial_call=True
)
def On_Missing_Data_File_Uploaded(content, filename) -> bool:  # Appelé lorsque l'utilisateur charge un fichier de donnée à partir de la boite de dialogue de fichier manquant
    # On décode le contenu du fichier
    decoded_content = Decode_Str(content)

    # On l'enregistre
    if not os.path.exists(f"downloaded\\{filename}"):
        open(f"downloaded\\{filename}", 'w').write(decoded_content)

    return False


@app.callback(
    [Output('memory', 'data', allow_duplicate=True), Output('fig', 'figure', allow_duplicate=True)],
    Input({"type": "edit_button", "index": ALL}, 'n_clicks'),
    [State('memory', 'data')],
    prevent_initial_call=True
)
def On_Edit_Button_Pressed(n_clicks, memory) -> tuple:  # Appelé lorsque le bouton de modification est cliqué
    # On récupère l'index du label
    label_index = Get_Label_Index_From_CTX(memory)

    # Si jamais il s'agit d'un appel initial ou d'un appel lié à un rafraichissement de la liste de bouton, on annule la mise à jour
    if n_clicks[label_index] is None or memory['edit']['precedent_clicks'][label_index] == n_clicks[label_index]:
        raise PreventUpdate

    memory['edit']['precedent_clicks'][label_index] = n_clicks[label_index]

    fig: go.Figure = figs[memory['session_id']][0][0]

    fig.clear_selection()

    # Si nous étions déjà en train de modifier
    if memory['edit']['is_editing']:
        # On quitte le mode de modification et on efface la boite de sélection
        memory['edit']['is_editing'] = False
        return memory, fig

    # Sinon, on ajoute une boite de sélection et on entre en mode de modification
    fig.add_selection(x0=memory['all_labels'][label_index]['positions'][0], y0=memory['max_data'], x1=memory['all_labels'][label_index]['positions'][1], y1=memory['min_data'])

    memory['edit']['is_editing'] = True
    memory['edit']['editing_id'][0] = label_index
    memory['edit']['editing_id'][1] = memory['all_labels'][label_index]['id']

    return memory, fig


@app.callback(
    [Output('memory', 'data', allow_duplicate=True), Output('fig', 'figure', allow_duplicate=True)],
    Input('event_listener', 'n_events'),
    [State('event_listener', 'event'), State('memory', 'data')],
    prevent_initial_call=True
)
def On_Keyboard_Event(n_events, event, memory: dict) -> tuple:  # Appelé lorsqu'une touche du clavier est pressée
    if 'key' not in event:
        raise PreventUpdate

    # On récupère la touche pressée
    key = event['key']

    if key == 'Enter' and memory['edit']['is_editing']:
        # On désactive le mode sélection
        fig: go.Figure = figs[memory['session_id']][0][0]

        memory['edit']['is_editing'] = False
        fig.clear_selection()

        return memory, fig

    raise PreventUpdate
