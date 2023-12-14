# importing libraries
import zipfile
from urllib.request import urlopen
import shutil
import os
import pandas as pd


def pull_prod_data():
    """
    Retrieves well and lease production data

            Returns:
                    lease_prod_df (pandas.DataFrame): lease production data in a dataframe
                    well_prod_df (pandas.DataFrame: well production data in a dataframe
    """
    url = 'https://bogfiles.dnrc.mt.gov//Reporting/Production/Historical/MT_Historical_Production.zip'
    file_name = 'MT_Historical_Production.zip'

    # extracting zipfile from URL
    with urlopen(url) as response, open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

        # extracting required file from zipfile
        with zipfile.ZipFile(file_name) as zf:
            zf.extract('MT_HistoricalPRUProduction.tab')
            zf.extract('MT_HistoricalWellProduction.tab')

    # deleting the zipfile from the directory
    os.remove('MT_Historical_Production.zip')

    # loading data from the file
    lease_prod_df = pd.read_csv('MT_HistoricalPRUProduction.tab', sep='\t')
    well_prod_df = pd.read_csv('MT_HistoricalWellProduction.tab', sep='\t')

    return lease_prod_df, well_prod_df


def pull_well_data():
    """
    Retrieves well header data

            Returns:
                    well_data_df (pandas.DataFrame): dataframe with well header info
    """
    url = 'https://bogfiles.dnrc.mt.gov//Reporting/Wells/MT_CompleteWellList.zip'
    file_name = 'MT_CompleteWellList.zip'

    # extracting zipfile from URL
    with urlopen(url) as response, open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

        # extracting required file from zipfile
        with zipfile.ZipFile(file_name) as zf:
            zf.extract('MT_HistoricalWellList.tab')

    # deleting the zipfile from the directory
    os.remove('MT_CompleteWellList.zip')

    # loading data from the file
    well_data_df = pd.read_csv('MT_HistoricalWellList.tab', sep='\t')

    return well_data_df


def pull_ff_data(state_name='Montana'):
    """
    Returns well header data

            Parameters:
                    state_name (str): name of the state to filter data

            Returns:
                    FracFocusRegistry_df (pandas.DataFrame): frac focus registry data in a dataframe
                    registryupload_df (pandas.DataFrame: registry upload data in a dataframe
    """
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

    if state_name:
        FracFocusRegistry_df = FracFocusRegistry_df[FracFocusRegistry_df['StateName'] == state_name]
        registryupload_df = registryupload_df[registryupload_df['StateName'] == state_name]

    return FracFocusRegistry_df, registryupload_df
