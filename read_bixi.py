# -*- coding: utf-8 -*-
"""
Created on Wed May 31 23:59:25 2017

@author: Colin-N. Brosseau
"""
import time
import numpy as np
import bz2
import glob
import os
import datetime
import xmltodict
from xml.parsers.expat import ExpatError  # for xmltodict

import matplotlib.pylab as plt

"""
Remarks:
    Sometimes, some stations appear or disappear.
    See for example between 2017-06-05_07:24:00.xml.bz2 and 
    2017-06-05_07:25:00.xml.bz2
    
    The server is refreshed at each 120 second in mean. Refresh time is 120 +/- 5 s.

    At some times, the number of docks at some stations change. For exemple,
    on 2017-06-05 station 'De la Commune / King' passed from 48 docks to
    88 docks.
    
    Most of the stations seems to have a bug in their total number of docks.
    For exemple, station 'De la Commune / King' sometimes fluctuate between
    88 and 89 docks. Sometimes it goes down to 1-2 for few minutes and go back
    to 88-89.
"""

class BadXMLFile(Exception):
    """
    Represents a bad .xml file.
    """
    pass

def read_raw(year, month=None, day=None, directory='.', verbose=0):
    """
    Read all available raw data for a day, a month or a year.

    Data files are supposed to be in format AAAA-MM-DD_xxxxxx.xml.bz2. Where
    AAAA is year, MM is month, DD is day. xxxxxx could be anything. Files must be 
    in .xml.bz2 format.
    

    Parameters
    ----------
    year : int
    
        Year (YYYY) to import.


    month : int
    
        month to import.
        If None,import all months availables


    day : int
    
        Day to import.
        If None,import all days availables.
        Has to be omited (or set to None) if month=None.


    directory : str
    
        Source directory for the files.

    
    verbose : int, [0, 1, 2]
        
        Level of verbosity


    Returns
    -------
    time_vector: int, shape (n_measurements,)


    bikes_available: dict

        Each element is the number of bikes available (shape (n_measurements,)) in the corresponding station (key is 'terminalName').


    max_bikes: dict

        Each element is the maximum number of bikes available (shape (n_measurements,)) in the corresponding station (key is 'terminalName').


    stations_metadata: dict

        Each element is a dictionary of metadata for the corresponing station (key is 'terminalName').
        Metadata available:
            'id': int
            'installed': bool
            'lat': float
                lattitude
            'locked': bool
            'long': float
                longitude
            'name': str
                name of the station (human readable)
            'public': bool
            'temporary': bool

    Possible bug: if a station disappear and reapear during the day, corresponding bikes_abailable and max_bikes will be wrong
    """
    if month is None:
        assert day is None, "day has to be omited (or set to None) if month=None."
        list_filename = sorted(glob.glob(os.path.join(directory, "%04d-*.xml.bz2" % (year))))
    elif day is None:
        list_filename = sorted(glob.glob(os.path.join(directory, "%04d-%02d-*.xml.bz2" % (year, month))))
    else:        
        list_filename = sorted(glob.glob(os.path.join(directory, "%04d-%02d-%02d_*.xml.bz2" % (year, month, day))))
    
    bn = bixi_newtork()
    i = 0
    for filename in list_filename:
        i += 1
        if verbose > 0:
            print(str(i) + "/" + str(len(list_filename))  +  "   " + filename)
        try:
            ddd, last_update = bixi2dict(filename)
            bn.add(ddd, last_update)
        except BadXMLFile:
            pass
        
    return bn


class bixi_newtork():
    """
    Contains informations related to the whole bixi network (all stations).
    """
    def __init__(self):
        self.last_update = 0
        self.stations = {}
        
    def add(self, d, update_time):
        """
        Add new informations from the network
        
        d : dictionnary
        """
        
        # only add informations if they are new
        if update_time != self.last_update:
            self.last_update = update_time
            for i in d:
                station_name = i['terminalName']
                try:
                    self.stations[station_name].add(i)
                except KeyError:
                    self.stations[station_name] = station()
                    self.stations[station_name].add(i)
                    

def equal_dicts(d1, d2, ignore_keys):
    d1_filtered = dict((k, v) for k,v in d1.items() if k not in ignore_keys)
    d2_filtered = dict((k, v) for k,v in d2.items() if k not in ignore_keys)
    return d1_filtered == d2_filtered
            

class station():
    """
    Contains the informations related to a station.
    """
    def __init__(self):
        # Metadata of the station
        # list of dictionnaries
        self.metadata = []
        # Time of observation (unix time)
        self.measure_time = np.array([], dtype=np.uint32)
        # Number of available bikes
        self.bikes = np.array([], dtype=np.uint8)  # biggest station is 89 docks
    
    def add(self, d):
        """
        Add new information to a station.
        
        d : 
            dictionnary reprensenting the state of the station
        """
        dic = d.copy()

        # Changing informations
        try:
            # Update only if there is new information in the numer of bikes
            if dic['lastUpdateTime'] != self.measure_time[-1]:
                self.measure_time = np.append(self.measure_time, dic['lastUpdateTime'])
                self.bikes = np.append(self.bikes, dic['nbBikes'])
        except IndexError:
                self.measure_time = np.array([dic['lastUpdateTime']], dtype=np.uint32)
                self.bikes = np.array([dic['nbBikes']], dtype=np.uint8)

        # Total number of docks
        dic['numDocks'] = dic['nbBikes'] + dic['nbEmptyDocks']

        # Delete informations not related to metadata
        del dic['lastCommWithServer']
        del dic['nbBikes']
        del dic['nbEmptyDocks']
        try:
            # Update only if metadata changed
            if not equal_dicts(dic, self.metadata[-1], 'lastUpdateTime'):
                self.metadata.append(dic)
        except IndexError:
            self.metadata = [dic]

def bixi2dict(filename):
    """
    Extract content of a bixi status file to a dictionnary.
    

    Parameters
    ----------
    filename : str
    
        File to import. Must be in format .xml.bz2. 
        Files are taken from https://montreal.bixi.com/data/bikeStations.xml


    Returns
    -------
    stations : list of dicts
        Each element of the list represents a station. 
        A station is itself a dict with fields:

            'id' : int
                id of the station
                
                
            'installed' : bool
                    
                    
            'lastCommWithServer' : int
                time of last communication with the server  . 
                Epoch (Unix) time           
            
        
            'lastUpdateTime' : 
                time of last update of the station  . 
                Epoch (Unix) time           
            
            
            'lat' : float
                lattitude of the station        
            
            
            'locked' : bool            
            
            
            'long' : float
                longitude of the station            
                
            
            'name' : str
                name of the station (street corners)
            
            
            'nbBikes' : int
                number of available bikes
            
            
            'nbEmptyDocks' : int
                number of empty docks
                
                
            'public' : bool
            
            
            'temporary' :bool
            
            
            'terminalName' : int
                terminal name
                
        last_update : int
            last update time of the network (Unix time)
    """
    def xmlbz2todict(filename):
        """
        Convert a bz2-ed xml file to a dictionnary


        Parameters
        ----------
        filename : str
        
            File to import. Must be in format .xml.
            
    
        Returns
        -------
        list_stations : list
            List of dictionnaries. Each dictionnary represent the state of a station a a given time.
        last_update : int
            Last update of the xml file. Unix time * 1000
        """
        file = bz2.BZ2File(filename, 'rb')
        try:
            return xmltodict.parse(file, xml_attribs=True) 
        except ExpatError:
            raise BadXMLFile(filename)         

    d = xmlbz2todict(filename)['stations']
    try:
        last_update = int(int(d['@LastUpdate'])/1000)
    except ValueError:
        raise BadXMLFile(filename)
    list_stations = d['station']
    
#    for station in list_stations:
    for i, station in enumerate(list_stations):
        try:
#            print(' ')
#            print(station)
            list_int = ['id', 'lastCommWithServer', 'lastUpdateTime', 'nbBikes', 'nbEmptyDocks', 'terminalName']
            for key in list_int:
                station[key] = int(station[key])
            list_bool = ['installed', 'locked', 'public', 'temporary']
            for key in list_bool:
                station[key] = bool(station[key])
            list_float = ['lat', 'long']
            for key in list_float:
                station[key] = float(station[key])
                
            # put time in Unix time
            station['lastUpdateTime'] = int(station['lastUpdateTime']/1000)
            station['lastCommWithServer'] = int(station['lastCommWithServer']/1000)
        except TypeError:
            del list_stations[i]
            """
            Delete this kind of buggy data:
            OrderedDict([('id', '595'), ('name', '4000'), ('terminalName', '4000'), 
            ('lastCommWithServer', None), ('lat', '0'), ('long', '0'), ('installed', 'true'), 
            ('locked', 'false'), ('installDate', None), ('removalDate', None), 
            ('temporary', 'false'), ('public', 'true'), ('nbBikes', '0'), 
            ('nbEmptyDocks', '0'), ('lastUpdateTime', '0')])
            """
        
    return list_stations, last_update
        

def resample_time(X, y):
    """
    Calculate values over a even spaced vector.
    Output time vector is 0 -> 1438 with steps of 2. Unit is minutes.
    If y is a dictionnary, each key represent a vector (y). It then resample every vector
    """
    if isinstance(y, dict):
        for key in y:
            x_fit, y_fit = resample_time(X, y[key])
            y[key] = y_fit
        return x_fit
    else:
        if len(np.shape(X)) == 1:  # X vector must have 2 dimensions. If needed, create a simgleton dimension.
            X = X[:, np.newaxis]
        from sklearn.tree import DecisionTreeRegressor
        regressor = DecisionTreeRegressor(random_state = 0)
        regressor.fit(X, y)
        x_fit = np.arange(0, 1440, 2)[:, np.newaxis] 
        y_fit = regressor.predict(x_fit)
        #plt.scatter(X, y, color = 'red')
        #plt.plot(x_fit, y_fit, '.:', color = 'blue')
        #plt.show()
        return x_fit, y_fit
    

if __name__ == '__main__':
    bn = read_raw(2017,8,31,directory='source', verbose=1)
    
    
