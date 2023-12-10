# importing libraries
import zipfile
from urllib.request import urlopen
import shutil
import os
import pandas as pd

def pull_prod_data():

    url = 'http://bogc.dnrc.mt.gov/production/historical.zip'
    file_name = 'historical.zip'

    # extracting zipfile from URL
    with urlopen(url) as response, open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

        # extracting required file from zipfile
        with zipfile.ZipFile(file_name) as zf:
            zf.extract('histLeaseProd.tab')
            zf.extract('histprodwell.tab')
            zf.extract('histWellData.tab')

    # deleting the zipfile from the directory
    os.remove('historical.zip')

    # loading data from the file
    lease_prod_df = pd.read_csv('histLeaseProd.tab', sep='\t')
    well_prod_df = pd.read_csv('histprodwell.tab', sep='\t')
    well_data_df = pd.read_csv('histWellData.tab', sep='\t')

    return lease_prod_df, well_prod_df, well_data_df

def pull_ff_data(state_no=25):

    url = 'https://fracfocusdata.org/digitaldownload/FracFocusCSV.zip'
    file_name = 'FracFocusCSV.zip'

    # extracting zipfile from URL
    with urlopen(url) as response, open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

        # extracting required files from zipfile and put in dictionary
        zip_file = zipfile.ZipFile(file_name)
        dfs = {csv_file.filename: pd.read_csv(zip_file.open(csv_file.filename), low_memory=False)
               for csv_file in zip_file.infolist()
               if csv_file.filename.endswith('.csv')}

    registryupload_keys = [item for item in list(dfs.keys()) if 'Frac' not in item]
    registryupload_dict = {x: dfs[x] for x in registryupload_keys}
    registryupload_df = pd.concat(registryupload_dict, axis=0)
    registryupload_df.head()

    FracFocusRegistry_keys = [item for item in list(dfs.keys()) if 'registryupload' not in item]
    FracFocusRegistry_dict = {x: dfs[x] for x in FracFocusRegistry_keys}
    FracFocusRegistry_df = pd.concat(FracFocusRegistry_dict, axis=0)
    FracFocusRegistry_df.head()

    FracFocusRegistry_df_MT = FracFocusRegistry_df[FracFocusRegistry_df['StateNumber'] == state_no]
    registryupload_df_MT = registryupload_df[registryupload_df['StateNumber'] == state_no]


    return FracFocusRegistry_df_MT, registryupload_df_MT