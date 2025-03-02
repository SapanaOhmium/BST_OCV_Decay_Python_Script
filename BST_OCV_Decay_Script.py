# -*- coding: utf-8 -*-
"""
Created on Mon Oct 30 10:54:29 2023

@author: sapana.pawar
"""

# Import the relevant libraries
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


# Import the required Dash libraries
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from io import BytesIO
import base64

# Initialize the app
app = dash.Dash(__name__)
# Initialize the server
server = app.server

# Build the components
Header_componet = html.H1('OCV Decay Plot', style={'backgroundColor': 'white',
                          'color': 'darkcyan', 'text-align': 'center', 'font-size': 50})

# Design the app layout
app.layout = html.Div([
    dbc.Row([Header_componet]),
    
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload File'),
        multiple=False
        ),
    
    dcc.Dropdown(
        id='sheet-dropdown',
        multi=True),
    
        html.Div([
            html.Label('Start Duration:'),
            dcc.Input(id='start-duration', type='number', value=1),
            html.Label('End Duration:'),
            dcc.Input(id='end-duration', type='number', value=60),
            ], style={'margin-top':'10px'}),
        
        dbc.Row([dbc.Col(html.Button('Update Plateau Durations', id='update-table-button', n_clicks=0, style={'margin':'10px'}))]),
                    
        dcc.Input(id='graph-title-input', type='text', value='Edit Title For OCV Decay Chart',style={'margin':'10px', 'width': '50%', 'height':'20px'}),
        dbc.Row([dbc.Col(html.Button('Edit Title', style={'margin':'10px'}))]),            
        html.Div([dcc.Graph(
            id='plot'),
            ], style={'width':'80%', 'height':'800px','display':'inline-block', 'vertical-align':'top'}),
        
        html.Div([
            dcc.Checklist(
                id='legend-toggle',
                options=[{'label':'Show Legend', 'value':'show_legend'}],
                value=['show_legend']
                                ),
            
            dash_table.DataTable(id='slope-table',
                                 columns=[
                                     {'name':'Cell', 'id':'cell'},
                                     {'name':'Slope Value', 'id': 'slope_value'},
                                             ],
                                 style_table={'width': '100%', 'marginTop':'20px'},
                                 style_cell={'textAlign':'center'},
                                         
                                 style_header={'backgroundColor':'rgb(230, 230, 230)','fontWeight':'bold'},
                                         ),
            ], style={'width':'18%', 'display':'inline-block', 'margin-left': '2%',
                                      'vertical-align':'top'}),
                      ])
     
     

@app.callback(
    Output('sheet-dropdown', 'options'),
    [Input('upload-data', 'contents')]
    )


def update_sheet_dropdown(contents):
    if contents is None:
       raise PreventUpdate
    content_type, content_string = contents.split(',')

    decoded = BytesIO(base64.b64decode(content_string))
    xls = pd.ExcelFile(decoded)
    sheets = xls.sheet_names

    return [{'label': sheet, 'value':sheet} for sheet in sheets]


         
@app.callback(
    [Output('plot', 'figure'),
     Output('slope-table', 'data')],
    [Input('upload-data', 'contents'),
     Input('sheet-dropdown', 'value'),
     Input('start-duration', 'value'),
     Input('end-duration', 'value'),
     Input('graph-title-input', 'value'),
     Input('legend-toggle', 'value')],
    prevent_initial_call=True
 )  


def update_graph(contents, selected_sheets, start_duration, end_duration, graph_title, legend_toggle):

    if selected_sheets is None:
       raise PreventUpdate
    
       
    content_type, content_string = contents.split(',')

    decoded = BytesIO(base64.b64decode(content_string))
    
    xls = pd.ExcelFile(decoded)
    
    slope_table_data = []
    
    fig = go.Figure()
    
    color_cycle = px.colors.qualitative.Dark24
    
    for sheet in selected_sheets:
        #Read the dataframe
        df = pd.read_excel(xls, sheet_name=sheet) 
        #Filter the dataframe where sequence name is OCV Decay
        #df = df[df['Sequence Name'].str.lower().str.contains('ocv')]
        #convert the time column to datetime format, handling errors by coercing invalid values to NaT
        df['Time'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M', errors='coerce')
        #forward-fill missing value in the 'Time' column
        df['Time']= df['Time'].ffill()
        #add seconds to the time data (assuming seconds start from 00)
        df['Time'] = df['Time'] + pd.to_timedelta(df.groupby('Time').cumcount()*5, unit='s')
        #calculate the time difference between consecutive rows
        df['timedelta'] = df['Time'].diff().fillna(pd.Timedelta(seconds=5)) #Assuming 5 seconds interval
        #set the first row to a timedelta of 0
        df.loc[0, 'timedelta'] = pd.Timedelta(0)
        #calculate the cumulative time difference from the first row
        df['cumulative_time'] = df['timedelta'].cumsum()
        #convert the duration to minutes
        df['durations'] = df['cumulative_time'].dt.total_seconds()/60
        #ocv_df.to_csv('modifiedcsv.csv')
        #select columns
        selected_columns = []
        for col in df.columns:
            if col.startswith('Cell'):
                #if not np.isclose(0, df[col].median()):
                if df[col].nunique() > 1:
                    selected_columns.append(col)
        
        
        for i, col in enumerate(selected_columns):
            
            duration =df['durations']
            cell_voltages = df[col]
            
            #Calculate the slopes between adjecent points
            #slope = np.diff(cell_voltages)/np.diff(duration)

            start_duration = float(start_duration)
            end_duration = float(end_duration)
   
            # Check if there is a plateau within a specified ranges
            plateau_indices_filtered = [i for i in range(len(duration)-1)if start_duration < duration[i] < end_duration]
            print(plateau_indices_filtered)
            
            if len(plateau_indices_filtered)>=1:
 
                #Extract the plateau duration for plateau region
                plateau_duration = [duration[i] for i in plateau_indices_filtered]  
               
                #Extract the plateau voltages for plateau region
                plateau_voltages = [cell_voltages[i] for i in plateau_indices_filtered]
               
                #Claculate the slope using the firt and last points of the plateau region    
                delta_volt = plateau_voltages[-1] - plateau_voltages[0]
                delta_time = plateau_duration[-1] - plateau_duration[0]
                slope = abs(delta_volt / delta_time)
           
                
                #Add overall line to the plot without showing in the legend
                fig.add_trace(go.Scatter(x=duration, y=cell_voltages, mode='lines', line=dict(color=color_cycle[i]), name=f'{col}' , showlegend=False))
                
                #Highlight the plateau region with a scatter plot
                fig.add_trace(go.Scatter(x=plateau_duration, y=plateau_voltages, mode='markers',
                                         marker=dict(color=color_cycle[i]), name=f'{col} (Slope: {slope:.4f})'))
                
                #update the slope table
                cell_name= col.split()[-1]
                slope_table_data.append({'cell': cell_name, 'slope_value': round(slope, 4)})
             
            else:
                print("No plateau region found")
                #Add overall marker to the plot without showing in the legend
                fig.add_trace(go.Scatter(x=duration, y=cell_voltages, mode='markers',marker=dict(color=color_cycle[i]),  name=f'{col}'))
                
       
        fig.update_layout(
            xaxis_title='Duration (min)',
            yaxis_title='Cell Voltage [V]',
            title=graph_title,
            font=dict(size=16),
            showlegend='show_legend' in legend_toggle,
            legend=dict(orientation = 'h', yanchor='bottom', y=0.2, xanchor='left', x=1),
            template='plotly_white')  
      
        
        return fig, slope_table_data   
    
        
                
# Run the app
if __name__ == '__main__':
    app.run(debug=False)  