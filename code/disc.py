#!/usr/bin/env python3
#----------------------------------------------------------------------
# helper routines 
#---------------------------------------------------------------------.

import math,collections
# Index of refraction for optical fiber
FIBER_RI = 1/1.52
FACTOR_5000 = 0.40
FACTOR_3000 = 0.35
FACTOR_2000 = 0.30
FACTOR_1000 = 0.25
FACTOR_500 = 0.18
REDUCTION_FACTOR = FACTOR_500
SPEED_OF_LIGHT = 299792.458 # km/s

class Disc(object):
    def __init__(self, hostname, latitude, longitude, ping):
        """
        ping (float): (in ms)
        """
        # in km:ping*98,615940132
        self._radius = ((ping/2)*0.001) * (REDUCTION_FACTOR*SPEED_OF_LIGHT)
        self._hostname  = hostname
        #self._instance  = instance
        #self._city=city
        #self._valid=valid
        #self._oldradius=oldradius
        self._latitude=latitude
        self._longitude=longitude

    def getHostname(self):
        return self._hostname

    def getLatitude(self):
        return self._latitude

    def getLongitude(self):
        return self._longitude


    def getRadius(self):
        return self._radius

    def overlap(self, other):
        """
        Two discs overlap if the distance between their centers is lower than
        the sum of their radius.
        """
        
        return (self.distanceFromTheCenter(other._latitude,other._longitude)) <= (self.getRadius() + other.getRadius())

    def distanceFromTheCenter(self,lat, longi):
        # Convert latitude and longitude to 
        # spherical coordinates in radians.
        degrees_to_radians = math.pi/180.0
            
        # phi = 90 - latitude
        phi1 = (90.0 - self._latitude)*degrees_to_radians
        phi2 = (90.0 - lat)*degrees_to_radians
            
        # theta = longitude
        theta1 = self._longitude*degrees_to_radians
        theta2 = longi*degrees_to_radians
            
        # Compute spherical distance from spherical coordinates.
            
        # For two locations in spherical coordinates 
        # (1, theta, phi) and (1, theta, phi)
        # cosine( arc length ) = 
        #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
        # distance = rho * arc length
        
        cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
               math.cos(phi1)*math.cos(phi2))
        if (abs(cos - 1.0) <0.000000000000001):
            arc=0.0   
        else:
            arc = math.acos( cos )
            
        # Remember to multiply arc by the radius of the earth 
        # in your favorite set of units to get length.
        return arc*6371


    def __str__(self):
        return "%s\t%s\t%s\t%s\n" % (self._hostname, self._latitude,  self._longitude, self._radius)

class Discs(object):

    def __init__(self):
        self._setDisc={}
        self._orderDisc=collections.OrderedDict()

    def getDiscs(self):
        return self._setDisc

    def removeDisc(self, disc):
        self._setDisc[disc[0].getRadius()].remove(disc)

    def overlap(self, other):

        for radius, listDisc in self._setDisc.items():
            
            for disc in listDisc:
                if disc[0].overlap(other):
                    return True
        return False
    

    def add(self,disc,geolocated):
        if(self._setDisc.get(disc.getRadius()) is None):
           self._setDisc[disc.getRadius()]=[(disc,geolocated)]
        else:
            self._setDisc[disc.getRadius()].append((disc,geolocated))

    def getOrderedDisc(self):
        self._orderDisc=collections.OrderedDict(sorted(self._setDisc.items()))
        return self._orderDisc

    def smallestDisc(self):
        self._orderDisc=collections.OrderedDict(sorted(self._setDisc.items()))
        return next(iter(self._orderDisc))

