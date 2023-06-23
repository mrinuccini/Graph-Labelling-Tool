# Graph Labeling tool 
## About
This repository contains a graph labeling tool. You can load custom config files, data file, and labels them. Then, you can save the labels data and use them in an other tool or load them back later.

<br>

<img src="https://i.imgur.com/o3JpPtc.png">

## Functionalities 
- Add as many labels as you want.
- Upload custom config files and custom data file.
- Save your work to use in other programs.
- Load your precedent work.
- Edit / Delete created label.
- Auto collapse functionality, meaning that two labels cannot superpose each other.
- Data file saving on the server so that you don't have to re-upload data file everytime you want to reload a precedent work.
- Dark mode support (beta).

## Installation
### Tools
- [**Python**](https://www.python.org/) : Python 3.11 or later
### Libraries
This tool requires the following libraries to work :

- [**Dash**](https://www.python.org/) : ```pip install dash```
- [**Plotly**](https://plotly.com/python/) : ```pip install plotly```
- [**Pandas**](https://pandas.pydata.org) : ```pip install pandas```
- [**Dash Extensions**](https://www.dash-extensions.com) : ```pip install dash-extensions```

You can also install them using the script located in ```scripts\setup.bat```.

## Usage
### Important :
Don't delete the files ```data\ECG_config.json``` and ```downloaded\ECG.csv```. They are necessary to the start of the application (to create the default fig).
### Config file :
Each config file must contain the following parameters :
- ```timestamp_row``` (int) : If a column of your data set is used to represent the the indices of the other column, write it's name / index here. Leave it to null if no column is used to represent the indices of the others.
- ```data_sampling_ratio``` (int) : Indicates the ratio of data to show on the graph : 1/data_sampling_ratio.
- ```data_slicing``` (int) : Indicates the number of rows to load in the application. If you want all rows to be loaded, leave it to -1. 
- ```coefficient``` (float) : All data in your data set will be multiplicated by this number.
- ```labels``` (dict) : A dictionary, containing all the labels the user can choose from. The keys must be string representing the name of the label and the value must be a dictionary containing the following data :
- - ```name``` (str) : The name of the label.
- - ```color``` (str) : The color of the label.
- ```legend``` (list) : This parameter can be left empty. It is a list of dictionaries. There must be one dict per columns in your dataset. Each dictionary must contain the following parameters :
- - ```name``` (str) : The name of the variable that will be showed  in the legend.
- - ```line-style``` (str) : The style of the line on the graph.
- - ```line-color``` (str) : The color of the line on the graph.

A config looks like the following  : (Please note that the parameter ```data-file``` is not mandatory)
```json
{
  "data-file": "ECG.csv",
  "timestamp_row": null,
  "data_sampling_ratio": 10,
  "data_slicing": -1,
  "coefficient": 0.5,
  "labels": {
    "bradycardie": {
      "name": "bradycardie",
      "color": "#ffa600"
    },

    "normal": {
      "name": "normal",
      "color": "#bc5090"
    },

    "tachycardie": {
      "name": "tachycardie",
      "color": "#003f5c"
    }
  },
  "legend": [
    {
      "name": "ECG",
      "line-style": "solid",
      "line-color": "red"
    }
  ]
}
```
# Credits
- [**Matthias Rinuccini**](https://github.com/mrinuccini/) : Creator of the project.
- [**Icon pack**](https://www.flaticon.com/fr/packs/multimedia-collection) : Icons used in the app.