# autoipcfg
The autoipcfg script uses EOS's eAPI infrastructure to take the output of
show lldp neighbor, looks a user-defined delimiter and for IP addresse that
is configured as part of a port description.  It then configures the
neighbor port with that IP address.  For example if your delimiter is
configured to be ":" the following port description would configure
1.1.1.1 with a 24 bit mask on the neighbor port of Ethernet1:
```
     Interface Ethernet1
         description This should be my neighbors ip address: 1.1.1.1/24
```

Note both a correct formatted IP address and subnet mask must be found
for the configuration to take place.

## Requirements

  * Arista EOS 4.12 or later
  * [pyeapi](http://github.com/arista-eosplus/pyeapi) eAPI Library
  
## Installation

The source code is provided at: [autoipcfg](https://github.com/arista-eosext/autoipcfg/)

* running ` python setup.py install ` from inside the source directory will install the script and also download the pyeapi libray if its not found on the source system

## Getting Started

### Configuration of [pyeapi](http://github.com/arista-eosplus/pyeapi) eAPI Library

* Detailed information about pyeapi can be found at [pyeapi](http://github.com/arista-eosplus/pyeapi) 
* [Example Config File](https://github.com/arista-eosplus/pyeapi/blob/master/examples/nodes.conf)

### Configuration of EOS device

The autoipcfg requires that eAPI be enabled on the Arista device.  This is done via the following configuration in global config mode
```
     switch#configure terminal
     switch(config)#management api http-commands
     switch(config-mgmt-api-http-cmds)#no shutdown
```
eAPI defaults to using https as the transport protocol but that is configurable.  The options are:
```
     switch(config-mgmt-api-http-cmds)#protocol ?
       http         Configure HTTP server options
       https        Configure HTTPS server options
       unix-socket  Configure Unix Domain Socket
```

If you are using a locally defined user in your pyeap conf file you would configure that in global config mode as well.  If you are using a locally defined user this username and password should match what is configured in the pyeapi configuration file
```
     switch#configure terminal
     switch(config)#username eapi secret password privilege 15 
```
You can also choose to have user authenicated via TACACS+/RADIUS as well.  If you need assistance with that configuration please see the configuration guide at www.arista.com

The next step is to configure autoipcfg to run as a daemon.  This is another global configuration on the EOS device:

```
     switch#configure terminal
     switch(config)#daemon autoipcfg
     switch(config-daemon-autoipcfg)#command /usr/bin/autoipcfg <(flags)
```

Flags you can set are:
```
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

   Flag         Description         Default Value
   ==============================================
   --node       DUT's hostame/IP            localhost
   --delim      ip address delimiter        : (colon)
   --interval   wait time between cycels    30 seconds
   --no_syslag   turns off syslog messages  False
   --config      config file for pyeapi     NULL (will use pyeapi defaults)

```


Configuring the script to run like above will allow EOS ProcMgr to restart to the script if it stops unexcedately.  You also have the option of running the script via the bash console in EOS

```
     switch#bash
     
     Arista Networks EOS shell
     [admin@switch ~]$autoipcfg &
```

## Example

This is example we have switchA connected to switchB via ports Ethernet1 and Ethernet2 respecitvely.  

#### SwitchA:
* Using http as a eAPI transport protcol
* Local user
* Running the autoipcfg script every 5 seconds

####Switch B
* Using https as a eAPI transport protocol
* User authenticated via an authentication server (config not shown)
* Using "*" as the delimiter
* Custom eapi config location
* Running script every 5 seconds

switchA(Eternet1)------(Ethernet2>)switchB.

Relevant configuration on switchA:
```
user eapi password password privilege 15

Interface Etherenet1
     description link to switchB*1.1.1.2/30
     
management api http-commands
      no shutdown
      protocol http

daemon autoipcfg
     command /usr/bin/autoipcfg --interval 5 --node switchA
```
Relevant configuration on switchB:
```
Interface Etherenet2
     description link to switchA:1.1.1.1/30

management api http-commands
      no shutdown

daemon autoipcfg
     command /usr/bin/autoipcfg --interval 5 --node switchB --delim * --config /mnt/flash/custom_eapi.conf

```

After the script is Ethernet1 on switchA will read:

```
      Interface Etherenet1
           description link to switchB*1.1.1.2/30
           no switchport
           ip address 1.1.1.1/30

```

Ethernet2 on switchB will read:

```
      Interface Etherenet2
         description link to switchA:1.1.1.1/30
         no switchport
         ip address 1.1.1.2/30

```

notifications from the script will be sent to the /var/log/messages file.  You can see the messages using the following command:
```
switchA#bash sudo cat /var/log/messages | grep 'AUTOIPCFG\|pyeapi'
```





