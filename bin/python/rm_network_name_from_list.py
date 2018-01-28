import sys
if "netkit_" in str(sys.argv[len(sys.argv)-3]): 
  print ("network rm " + str(sys.argv[len(sys.argv)-3]))