# MT_Oil
A repo that provides guidance for extracting data from Montana Board of Oil and Gas Conservation, pulling the corresponding data from Frac Focus. Includes examples of Exploratory Data Analysis on the production data.

You can step through the analysis and EDA using the `Montana_OilGas_Data_Prediction.ipynb` jupyter notebook.

Alternatively, if you want to build the image to start making predictions, run `docker build -t mt-oil-model .`
Train the model and return predictions using `docker run mt-oil-model` .


## `pull_data.py`

Contains functions to pull data

`pull_prod_data()` pulls production data from the Montana Board of Oil and Gas Conservation.

`pull_well_data()` pulls well data from the Montana Board of Oil and Gas Conservation.

`pull_ff_data()` pull stimulaton data from Frac Focus.

## `prod_model.py`

Contains functions to munge data and create machine learning model to predict well production

`preprocess_ff_data()` performs feature engineering on FF data to have well stimulation data.

`preprocess_well_data()` munges well data to obtain well location data and drilling direction.

`preprocess_prod()` manipulates production data to obtain cumulative production at specified intervals.

`preprocess_prod()` manipulates production data to obtain cumulative production at specified intervals.

`data_merge()` merges datasets to together to create a tabular data set to feed into ML pipeline.

`model_pipeline()` executes a ML pipeline to create predictions of well productivity.

## `tests.py`

Contains unit tests.

`TestProdModel` class contains unit tests for `prod_model.py`
