import os
import json
import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import re
# Iterate over all json in dir and save it on a JSON.

RAW_DIR = './data/raw/rents/tutti/'
FINAL_DIR = './data/raw/rents/'


def loadJson(filename):
    with open(filename, 'r') as outfile:
        return json.load(outfile)


def posIdInParameter(id_, p):
    """Return position of the list where the id is contained"""
    pos = -1
    values = [value['id'] for value in p]
    zip_ = dict(zip(values, np.arange(0, len(p))))
    if (id_ in values):
        pos = zip_[id_]
    return pos


def cleanParameter(p):
    """From parameter objects p, return Pandas Series with only nmr. of rooms, size and type"""

    rooms, size, type_ = [np.nan] * 3

    # Check for rooms
    pos_rooms = posIdInParameter('rooms', p)
    if (pos_rooms != -1):
        rooms = p[pos_rooms]['value']

    # Check for size
    pos_size = posIdInParameter('size', p)
    if (pos_size != -1):
        size = p[pos_size]['value']

    # Check for type_
    pos_type = posIdInParameter('type', p)
    if (pos_type != -1):
        type_ = p[pos_type]['value']

    return pd.Series([rooms, size, type_])


def main():

    print("Parse tutti.ch data ... ")

    all_json_filename = os.listdir(RAW_DIR)
    # Take only .json file
    all_json_filename = list(
        filter(lambda x: x.endswith('.json'), all_json_filename))

    all_json = []
    for j_ in all_json_filename:
        # print(j_)
        j_tmp = loadJson(RAW_DIR + j_)

        # Read JSON (and flatten values)
        pd_ = json_normalize(j_tmp['items'])

        # Save pandas obj
        all_json.append(pd_)

    df = pd.concat(all_json, ignore_index=True, sort=False)

    parameters = df['parameters'].apply(lambda p: cleanParameter(p))
    parameters.columns = ['rooms', 'size', 'type_param']

    df = df.merge(parameters, left_index=True, right_index=True)

    # Drop not useful columns
    not_useful_columns = ['company_ad',
                          'image_names',
                          'language',
                          'parameters',
                          'phone_hash',
                          'thumb_name',
                          'category_info.id',
                          'category_info.parent_id',
                          'category_info.parent_name',
                          'highlight',
                          'location_info.area',  # since all 'lausanne',
                          'location_info.area_id',
                          'location_info.region_name',
                          'location_info.region_id',
                          'public_account_id',
                          'body',
                          'id',
                          'epoch_time',
                          'user_alias'
                          ]

    df.drop(not_useful_columns, axis='columns', inplace=True)

    # Rename columns
    df.rename({
        'subject': 'title',
        'rooms': 'numberRooms',
        'location_info.address': 'address',
        'location_info.plz': 'postCode',
        'size': 'surface',
        'type_param': 'annount_type',
        'category_info.name': 'real_estate_type'
    }, axis='columns', inplace=True)

    # DROP all row without surface value
    df = df[~df['surface'].isna()]
    df.reset_index(drop=True, inplace=True)

    # CLEAN SURFACE
    df['surface'] = df['surface'].str.replace('m²', '')

    # DROP all row without price value
    df = df[~df['price'].isna()]
    df.reset_index(drop=True, inplace=True)

    # DROP all row without address value
    df = df[~df['address'].isna()]
    df.reset_index(drop=True, inplace=True)

    # CLEAN PRICE
    df['price'] = df['price'].str.replace('.- par mois', '')
    df['price'] = df['price'].str.replace('.-', '')
    df['price'] = df['price'].str.replace('par sem.', '')
    df['price'] = df['price'].str.replace('\'', '')
    df['price'] = df['price'].str.strip()

    df['address'] = df['address'].astype(str)

    def get_street_number(str_):
        split = re.findall(r'\d+', str_)
        if len(split) > 0:
            return split[0]
        else:
            return 0

    def get_street_name(str_):
        split = re.findall(r'\D+', str_)
        if len(split) > 0:
            return split[0]
        else:
            return ''

    df['street'] = df['address'].apply(lambda x: get_street_name(x)).astype(str)
    df['number'] = df['address'].apply(lambda x: get_street_number(x)).astype(str)

    # EXPORT TO JSON FORMAT
    df = df.query(
        'real_estate_type == "Maisons" or real_estate_type == "Appartements"'
    )
    df = df.query('type == "u"')
    df = df.drop(['type', 'real_estate_type', 'annount_type'], axis='columns')
    df.to_json(FINAL_DIR + 'tutti.json', orient='records')

    print("Saved 'tutti.json' in ./data/rents/tutti.json")
