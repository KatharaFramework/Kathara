import sys
if "netkit_" in str(sys.argv[len(sys.argv)-1]): 
	print("rm -f " + str(sys.argv[len(sys.argv)-1]))
