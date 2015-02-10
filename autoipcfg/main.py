# Copyright (c) 2015, Arista Networks, Inc. 
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# - Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# - Neither the name of Arista Networks nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARISTA NETWORKS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. #
#
# autoipcfg
#
#    Version 0.1.1 1/21/2015
#    Written by:
#       Peter Sprygada <sprygada@arista.com>
#       Dave Thelen <dt@arista.com>
#
#    Revision history:
#       0.1 - initial release
#       0.1.1 - added support for pyeapi library, and command line options
#       ...

'''
   DESCRIPTION
   The autoipcfg script uses EOS's eAPI infrastructure to take the output of 
   show lldp neighbor, looks a user-defined delimiter and for IP addresse that 
   is configured as part of a port description.  It then configures the
   neighbor port with that IP address.  For example if your delimiter is
   configured to be ":" the following port description would configure 
   1.1.1.1 with a 24 bit mask on the neighbor port of Ethernet1:

   Interface Ethernet1
     description This should be my neighbors ip address: 1.1.1.1/24

   Note both a correct formatted IP address and subnet mask must be found
   for the configuration to take place.

   INSTALLATION
     You can find the source zip file at: https://github.com/arista-eosext/autoipcfg/archive/master.zip
     once the package is extracted you can run the following command:
     python setup.py install

     To test if the script is installed successfully you can run /usr/bin/autoipcfg -h 
     and should see the following output:

     usage: autoipcfg [-h] [--node NODE] [--delim DELIM] [--interval INTERVAL]
                   [--no_syslog] [--config CONFIGFILE]

                   Automatically configure IP address via LLDP neighbor information

                   optional arguments:
                     -h, --help           show this help message and exit
                     --node NODE          Node to connect to
                     --delim DELIM        Delimiter in port description
                     --interval INTERVAL  Waiting period
                     --no_syslog          Turn off syslog messages
                     --config CONFIGFILE

   CONFIGURATION of the DUT:
   First step is to enable eapi on the device under test (DUT).  This is done via a
   lines of configuration on  DUT (e.g)
   arista#conf t
   arista(config)management api http-commands
   arista(config-mgmt-api-http-cmds)#no shutdown
   # by default eAPI runs over https (tcp port 443) however you can change the protcol 
   # in this part of the config options are http, https and unix domain sockets
   A user with approprite privledge levels will also be needed to run this script.  
   This user can be a local user or one that is authenticated via a backend
   authentication method (RADIUS, TACACS+).  If a local user is desired the following
   configuration will be needed:
   arista#conf t
   arista(config)#username eapi password changeme privledge 15

   Now you can start the process via the following configuration options:
   ariata#conf t
   arista(config)#daemon autoipcfg
   arista(config-daemon-autoipcfg)#command /usr/bin/autoipcfg <flags>
   Flags you can set for the script are:
   Flag         Description         Default Value
   ==============================================
   --node       DUT's hostame/IP            localhost
   --delim      ip address delimiter        : (colon)
   --interval   wait time between cycels    30 seconds
   --no_syslag   turns off syslog messages  False
   --config      config file for pyeapi     NULL (will use pyeapi defaults)

   CONFIGURATION of pyeapi:
   Please see the following link for configuration guidlines for this library:
   https://github.com/arista-eosplus/pyeapi

   REQUIREMENTS:
   Arista EOS version 4.12 or later
  
'''
import argparse
import re
import sys
import syslog
import time
import pyeapi.client


ETHERNET_RE = re.compile(r'Interface Ethernet([\d+/?])+')

def Log(stmt, toSyslog=True, severity=syslog.LOG_NOTICE):
    if toSyslog:
        for s in stmt.split('\n'): 
            syslog.syslog(severity, s)
    else:
       print stmt 

def lldpparser(data, delim):
    neighbors = dict()
    ipaddr = None
    token = None
    for entry in data.split('\n'):
        match = ETHERNET_RE.match(entry)
        if match:
            token = match.group(0)
            ipaddr = None

        if entry.strip().startswith('- Port Description'):
            description = entry.split(': ')[1]
            if delim in description:
              ipaddr = description.split(delim)[1].replace('"', '')

        if token is not None and ipaddr is not None:
            neighbors[token] = ipaddr
    return neighbors


def run():

   parser = argparse.ArgumentParser(description='Automatically configure IP address via LLDP neighbor information')

   parser.add_argument('--node',  action='store', dest='node',
                       default='localhost', help='Node to connect to')
   parser.add_argument('--delim', action='store', dest='delim', 
                       default=':', help='Delimiter in port description')
   parser.add_argument('--interval', action='store', dest='interval', 
                       default=30, type=float, help='Waiting period between runs')
   parser.add_argument('--no_syslog', action='store_false', dest='sendSyslog',
                       default=True, help='Turn off syslog messages')
   parser.add_argument('--config', action='store', dest='configFile',
                       default='default', help='Config File used by pyeapi')
   parseResults = parser.parse_args()
   delim = parseResults.delim
   interval = parseResults.interval
   configFile = parseResults.configFile
   nodeToConnect = parseResults.node 
   sendSyslog = parseResults.sendSyslog

   if sendSyslog:
      syslog.openlog('AUTOIPCFG', syslog.LOG_PID, syslog.LOG_LOCAL4)
   
   if configFile != 'default':
      pyeapi.client.load_config(configFile)
   if pyeapi.client.config.get_connection(nodeToConnect) is None:
      Log('%s not found in config file(s) ' % nodeToConnect, sendSyslog)
      print >>sys.stderr, '%s not found in config file ' % nodeToConnect
      sys.exit(-1)
   
   '''
   the pyeapi library will return a Node object when you pass the connect_to
   method a string that can be found in the pyeapi configuration file.  See
   more details on setting up the pyeapi configuration file at:
   https://github.com/arista-eosplus/pyeapi
   
   '''
   node = pyeapi.connect_to(nodeToConnect)
   while True:
       try:
          response = node.enable(['show lldp neighbors detail'], 'text')
       except pyeapi.eapilib.ConnectionError as e:
         Log(str(e), sendSyslog)
         print >>sys.stderr, str(e)
         sys.exit(-1)
       neighborInfo = response[0]['result']['output']
       neighbors = lldpparser(neighborInfo, delim)
       for k, v in neighbors.iteritems():
          if v:
              try:
                 '''
                 grab current IP, if one is configured.  The goal is is to see if actually need
                 to configure anything
                 '''
                 currentIp = node.enable(['show ip %s' % k])[0]['result']['interfaces'][k.split()[1]]['interfaceAddress']['primaryIp']['address']
              except pyeapi.eapilib.CommandError:
                 #looks like this port is a L2 port so we can just continue
                 currentIp = None
                 pass
              ''' 
              only configure if the ip if is not already configured.  This is mainly just to 
              save on syslog entries reporting the eapi user configuring interfaces every 
              interval as putting the same ip on the interface over and over again should 
              essentially be a no-op
              '''
              if currentIp is None or currentIp != v.split('/')[0]:
                 try:
                    node.config(['%s' % k,'no switchport', 'ip address %s' % v])
                    Log('adding ip address %s to interface %s' % (v, k), sendSyslog)
                 except pyeapi.eapilib.CommandError as e:
                    Log('Error: %s\nTrying to configure ip address %s on %s' % (e, v, k), sendSyslog)
       time.sleep(interval)
