# P4-lab
In this repository there are 3 laboratory. In each laboratory there are two kinds of machines, switch or client/server/sniffer. The purpose is implement the network with one or more P4 switch. Of course, you can run ping in all machines and make conversation between client and server. Below the rappresentation of topologies:
* lab-single-switch:

![lab-single-switch](https://github.com/giuseppevalentinobaldi/P4-lab/blob/master/res/lab-single-switch.png)

* lab-double-switch:

![lab-double-switch](https://github.com/giuseppevalentinobaldi/P4-lab/blob/master/res/lab-double-switch.png)

* lab-triple-switch:

![lab-triple-switch](https://github.com/giuseppevalentinobaldi/P4-lab/blob/master/res/lab-triple-switch.png)

Let's look now inside the client folder, this is composed of the following files:
```
    /
    ├── config_run.sh
    ├── client.py
    └── udp_client.py
``` 
Instead, the server contains the following files:
```
    /
    ├── config_run.sh
    ├── server.py
    └── udp_server.py
```    
Finally, the files contained in the switch:
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
To launch one of the 3 laboratories, just install [Kathará](https://github.com/Kidel/Kathara), place it in the root folder of the lab with the terminal and run the following command:
```
lstart
```
while switching off the laboratory just launch the following command:
```
lclose
```
waits for all machines to start and for each of them execute the following command:
```
./config_run.sh
```
wait for the rules to be loaded in P4 switches and have fun.
