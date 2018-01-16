# P4 examples
In this repository there are three Kathará labs. In each lab there are two kind of machines, switch or client/server/sniffer. The purpose is implement the network with one or more P4 switches. Of course, you can run ping in all machines and start conversation between client and server. Below the representation of the three topologies:
* **lab-single-switch**:

![lab-single-switch](https://github.com/giuseppevalentinobaldi/P4-lab/blob/master/res/lab-single-switch.png)

* **lab-double-switch**:

![lab-double-switch](https://github.com/giuseppevalentinobaldi/P4-lab/blob/master/res/lab-double-switch.png)

* **lab-triple-switch**:

![lab-triple-switch](https://github.com/giuseppevalentinobaldi/P4-lab/blob/master/res/lab-triple-switch.png)

In each lab, the folder that is mounted inside the client network nodes shoul contains the following files:
```
    /
    ├── config_run.sh
    ├── client.py
    └── udp_client.py
``` 
Instead, the folder for the server network node contains the following files:
```
    /
    ├── config_run.sh
    ├── server.py
    └── udp_server.py
```    
Finally, the files used to implement the switch:
```
    /
    ├── /behavioral-model
    |       └── /targets
    |               ├──/simple_router
    |               |       ├── commands_P4_14.txt
    |               |       └── ipv4_forward_P4_14.p4 
    |               └──/simple_switch
    |                       ├──/includes
    |                       |       ├── headers.p4
    |                       |       └── parser.p4
    |                       ├── commands.txt
    |                       ├── commands_heavy_hitter.txt
    |                       ├── heavy_hitter.p4
    |                       └── ipv4_forward.p4
    └── config_run.sh
```
To launch one of the three laboratories, just install [Kathará](https://github.com/Kidel/Kathara) following the instruction and start the labs with `lstart`. 

Wait for all network nodes to start and for each of them execute the script `config_run.sh`. This process can also be made automatic by editing the .startup files.

Wait for the rules to be loaded in every P4 switch and have fun.

To end the lab, run `lclean`.
