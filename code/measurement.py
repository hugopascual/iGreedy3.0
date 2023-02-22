#!/usr/bin/env python
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------
# helper functions to launch RIPE Atlas measurement  (./igreedy -m)
#---------------------------------------------------------------------.

asciiart = """
180 150W  120W  90W   60W   30W  000   30E   60E   90E   120E  150E 180
|    |     |     |     |     |    |     |     |     |     |     |     |
+90N-+-----+-----+-----+-----+----+-----+-----+-----+-----+-----+-----+
|          . _..::__:  ,-"-"._       |7       ,     _,.__             |
|  _.___ _ _<_>`!(._`.`-.    /        _._     `_ ,_/  '  '-._.---.-.__|
|.{     " " `-==,',._\{  \  / {)     / _ ">_,-' `                mt-2_|
+ \_.:--.       `._ )`^-. "'      , [_/( G        e      o     __,/-' +
|'"'     \         "    _L       0o_,--'                )     /. (|   |
|         | A  n     y,'          >_.\\._<> 6              _,' /  '   |
|         `. c   s   /          [~/_'` `"(   l     o      <'}  )      |
+30N       \\  a .-.t)          /   `-'"..' `:._        c  _)  '      +
|   `        \  (  `(          /         `:\  > \  ,-^.  /' '         |
|             `._,   ""        |           \`'   \|   ?_)  {\         |
|                `=.---.       `._._ i     ,'     "`  |' ,- '.        |
+000               |a    `-._       |     /          `:`<_|h--._      +
|                  (      l >       .     | ,          `=.__.`-'\     |
|                   `.     /        |     |{|              ,-.,\     .|
|                    |   ,'          \ z / `'            ," a   \     |
+30S                 |  /             |_'                |  __ t/     +
|                    |o|                                 '-'  `-'  i\.|
|                    |/                                        "  n / |
|                    \.          _                              _     |
+60S                            / \   _ __  _   _  ___ __ _ ___| |_   +
|                     ,/       / _ \ | '_ \| | | |/ __/ _` / __| __|  |
|    ,-----"-..?----_/ )      / ___ \| | | | |_| | (_| (_| \__ \ |_ _ |
|.._(                  `----'/_/   \_\_| |_|\__, |\___\__,_|___/\__| -|
+90S-+-----+-----+-----+-----+-----+-----+--___/ /--+-----+-----+-----+
     Based on 1998 Map by Matthew Thomas   |____/ Hacked on 2015 by 8^/  

"""

import json
import time
import os
import string
import sys
import time
import getopt
import socket
import collections
import webbrowser

import RIPEAtlas

class Measurement(object):
    def __init__(self, ip,ripeProbes=None):

        if(self.checkIP(ip)):
            self._ip = ip
        else:
            print >>sys.stderr, ("Target must be an IP address, NOT AN HOST NAME")
            sys.exit(1)
        self._ripeProbes = ripeProbes
        self._numberOfPacket =2 #to improve
        self._numberOfProbes = 5 #to improve, introduce as parameter, in alternative to the list of probes
        self._measurement = None
        self.result = None

        self._percentageSuccessful = 0.8 
        
    def getIP(self):
        return self._ip

    def getRipeProbes(self):
        return self._ripeProbes

    def checkIP(self,str):
        try:
            addr = socket.inet_pton(socket.AF_INET6, str)
        except socket.error: # not a valid IPv6 address
            try:
                addr = socket.inet_pton(socket.AF_INET, str)
            except socket.error: # not a valid IPv4 address either
                return False
        return True

    def loadProbes(self,pathVPs=None):
        temp_list_probes=[]
        temp_information_probes={}
        if pathVPs is None:
            pathVPs = "./datasets/ripe-vps"

        tempInformationProbes={}
        tempListProbes=[]
        for line in open(pathVPs,'r').readlines():
            if line.startswith("#"): #skip header and comments
                continue 
            hostname,latitude,longitude = line.strip().split("\t")
            temp_list_probes.append(hostname)
            temp_information_probes[hostname]=[latitude,longitude]
        self._numberOfProbes=len(temp_list_probes)
        return (",".join(temp_list_probes),temp_information_probes) #building the list

    def doMeasure(self,listProbes):
    
        data = { "definitions": [
               { "target": self._ip, "description": "Ping %s" % self._ip,
               "type": "ping", "is_oneoff": True, "packets": self._numberOfPacket} ],
             "probes": [
                 { "requested": self._numberOfProbes} ] }
        data["probes"][0]["type"] = "probes"
        data["probes"][0]["value"] = listProbes

        if string.find( self._ip, ':') > -1:
            af = 6
        else:
            af = 4
        data["definitions"][0]['af'] = af
        print("Running measurement from Ripe Atlas:")
        self.measurement = RIPEAtlas.Measurement(data)
        print("ID measure: %s\tTARGET: %s\tNumber of Vantage Points: %i " % (self.measurement.id,  self._ip,self.measurement.num_probes))

    def retrieveResult(self,infoProbes):
        self.result = self.measurement.results(wait=True, percentage_required=self._percentageSuccessful)
        numVpAnswer=0
        numVpFail=0
        totalRtt = 0
        numLatencyMeasurement = 0
        numVpTimeout = 0
        print("Number of answers: %s" % len(self.result))
        pathFile="datasets/measurement/"+self._ip+"-"+str(self.measurement.id)+"-"+str(time.time()).split(".")[0]
        inputIgreedyFiles=open(pathFile,'w')
        inputIgreedyFiles.write("#hostname	latitude	longitude	rtt[ms]\n")
        for result in self.result:
            VP = result["prb_id"]
            for measure in result["result"]:
                numVpAnswer += 1
                if measure.has_key("rtt"):
                    totalRtt += int(measure["rtt"])
                    numLatencyMeasurement += 1
                    inputIgreedyFiles.write(str(VP)+"\t"+str(infoProbes[str(VP)][0])+"\t"+str(infoProbes[str(VP)][1])+"\t"+str(measure["rtt"])+"\n")
                elif measure.has_key("error"):
                    numVpFail += 1
                elif measure.has_key("x"):
                    numVpTimeout += 1
                else:
                    print >>sys.stderr, ("Error in the measurement: result has no field rtt, or x or error")
        inputIgreedyFiles.close()
        if numVpAnswer == 0:
            print("Watson, we have a problem, no successful test!")
            sys.exit(0)
        else:

            try:
                print("Resume: %i successful tests (%.1f %%), %i errors (%.1f %%), %i timeouts (%.1f %%), average RTT: %i ms" % \
                      (numLatencyMeasurement,numLatencyMeasurement*100.0/numVpAnswer, 
                       numVpFail, numVpFail*100.0/numVpAnswer, 
                       numVpTimeout, numVpTimeout*100.0/numVpAnswer, totalRtt/numLatencyMeasurement))
            except:
                  c=0
        return (numLatencyMeasurement,pathFile)

