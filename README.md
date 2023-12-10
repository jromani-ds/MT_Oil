# MT_Oil
A repo that provides guidance for extracting data from Montana Board of Oil and Gas Conservation, pulling the corresponding data from Frac Focus. Includes examples of Exploratory Data Analysis and times series forecasting on the production data.


## `pull_data.py`

Contains functions to pull data

`pull_prod_data()` pulls production data from the Montana Board of Oil and Gas Conservation
`pull_ff_data()` pull stimulaton data from Frac Focus

## `model.py`
Contains functions to merge production and ff datasets together, clean data, do feature engineering, and building machine learning model to predict well productivity

`clean_data()` Cleans data of typographical errors
`feature_engineer()` Calculate, 360 oil production, lateral length, lbs of proppant/ft, gals of stimulation fluid/ft, lbs/gal proppant/fluid in stimulation, etc. 

`ml_model()` makes a machine learning model and provides metrics on how well it fits the data.

