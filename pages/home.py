import dash
from dash import dcc, html
from dashapp import default_figs, default_all_labels, default_currently_selected_data_range, default_config, default_data
import dash_bootstrap_components as dbc
from functions import GetMinValueInDataFrame, GetMaxValueInDataFrame
from dash_extensions.EventListener import EventListener

dash.register_page(__name__, path='/')

layout = html.Div([
        html.H1("Graph Labeling Tool"),

        html.H2("Load data"),

        dcc.Upload(id='upload_config_file', children=html.Div([html.Img(src='../assets/icons/upload.png', alt='upload icon'), 'Drag and Drop or Select ', html.A('a config file (json)')]), className='uploader'),

        dcc.Upload(id='upload_data_file', children=html.Div([html.Img(src='../assets/icons/upload.png', alt='upload icon'), 'Drag and Drop or Select ', html.A('a data file (csv)')]), className='uploader'),

        html.H2("Labels"),

        html.Div(children=[
            html.Button(children=[html.Img(src='../assets/icons/download.png', alt='download icon'), 'Save labels'], id="save_data_button", className="actionsButton"),
            dcc.Upload(id='upload_save_file', children=html.Div([html.Img(src='../assets/icons/upload.png', alt='upload icon', style={'width': '25px', 'height': '25px'}), 'Load labels']), className='uploader', style={'margin-left': '20px', 'width': '200px', 'height': '50px', 'transform': 'translateY(-10px)'}),
        ], style={'width': '100vw', 'display': 'flex', 'justify-content': 'left'}),

        html.P('⚠️ It is not recommended to edit the label positions using the Start and End input box, use the edit button instead. ⚠️', style={'font-size': '0.4cm'}),

        html.Div([
            html.Div(style={'height': '50px', 'width': '100vw', 'display': 'flex', 'justify-content': 'left'}, children=[
                html.P('ID', style={'height': 'inherit'}),
                html.P('Label', style={'height': 'inherit', 'margin-left': '60px'}),
                html.P('Start', style={'height': 'inherit', 'margin-left': '125px'}),
                html.P('End', style={'height': 'inherit', 'margin-left': '180px'})
            ]),

            html.Div(children=[], id="label_div", className='labelDiv')
        ]),

        html.H2("Graph(s)"),

        html.Button(children=[html.Img(src='../assets/icons/selection.png', alt='selection icon'), 'Selection mode'], id='selection_mode_button', className="labelActionButton", style={'margin-left': '0'}),
        html.Button(children=[html.Img(src='../assets/icons/see-icon.png', alt='eye icon'), 'Hide/Show annotations'], id='annotation_mode_button', className="labelActionButton", style={'margin-left': '10px'}),
        html.Button(children=[html.Img(src='../assets/icons/add.png', alt='add icon'), 'Add label'], id="add_label_button", className='labelActionButton', style={'margin-left': '10px'}),

        html.Div(children=dcc.Graph(id="fig", figure=default_figs[0]), id='figs-div'),

        html.Div(children=[], id='test', className='sessionIDDiv'),
        html.Div(children=[], id='session_id_div', className='sessionIDDiv'),
        html.Div(children=['Icon pack : bit.ly/3NaiHyv'], className='sessionIDDiv'),

        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Uh Oh ! Unfindable data file")),
            dbc.ModalBody([
                'Impossible to find the data file referenced in the loaded file.',
                dcc.Upload(id='upload_missing_data_file', children=html.Div(
                    [html.Img(src='../assets/icons/upload.png', alt='upload icon'), 'Upload ',
                     html.A('a data file (csv)')]), className='uploader'),
            ], id='upload_file_not_found_modal_body'),
            dbc.ModalFooter('Once you have loaded the data file, close this popup and reload your label file')
        ], id='upload_file_not_found_modal', is_open=False),

        dcc.ConfirmDialog(
            id='confirm_no_area_selected',
            message='Make sure you are not in edit mode and you have select an area on the graph before creating a label',
        ),

        dcc.ConfirmDialog(
            id='confirm_file_already_exist',
            message='There is already a file with a different content and the same name uploaded on the server. Please choose a different name.',
        ),

        dcc.Download(id='save_data'),

        dcc.Store(id='memory', data={
            'all_labels': default_all_labels,
            'currently_selected_data_range': default_currently_selected_data_range,
            'current_visible_data_range': ((0, 0), (0, 0), True),
            'config': default_config,
            'min_data': GetMinValueInDataFrame(default_data.loc[:, default_data.columns != default_config['timestamp_row']]) - 1000,
            'max_data': GetMaxValueInDataFrame(default_data.loc[:, default_data.columns != default_config['timestamp_row']]) + 1000,
            'annotations_visible': True,
            'currently_uploaded_file': default_config["data-file"],
            'edit': {'is_editing': False, 'editing_id': [-1, -1], 'precedent_clicks': []},
            'session_id': ''
        }),

        dcc.Interval(id='figs_interval_cleaner', interval=600000),

        EventListener(
            logging=True, id="event_listener"
        )
], className='mainDiv')
