#!/bin/bash
# Switch starter
echo "1 - to run simple router base forwarding"
echo "2 - to run simple switch base forwarding"
echo "3 - to run simple switch heavy hitter"
read -p 'What do you want to do ?: ' dovar
setup_config(){
	echo "> Compile program P4!!"
	p4c-bm2-ss --p4v $3 /behavioral-model/targets/$1/$2.p4 -o /behavioral-model/targets/$1/$2.json
	echo "> Configure the switch!!"
	sysctl -w net.ipv4.ip_forward=0
	/etc/init.d/procps restart
	echo "> Start the service!!"
	./behavioral-model/targets/$1/$1 -i 0@eth0 -i 1@eth1 -i 2@eth2 --log-console /behavioral-model/targets/$1/$2.json --pcap &
	sleep 10
	echo "> no Ready!!"
	/behavioral-model/tools/runtime_CLI.py --json /behavioral-model/targets/$1/$2.json < /behavioral-model/targets/$1/$4.txt
	mv /usr/sbin/tcpdump /usr/bin/tcpdump
	ln -s /usr/bin/tcpdump /usr/sbin/tcpdump
	echo "> Ready!!"
} 
case $dovar in
     1)
     	setup_config simple_router ipv4_forward_P4_14 14 commands_P4_14
        ;;
     2)
		setup_config simple_switch ipv4_forward 16 commands
        ;;
     3)
     	setup_config simple_switch heavy_hitter 14 commands_heavy_hitter
        ;; 
     *)
        echo "> Error!! -->command not find "
        ;;
esac
