import mmap
import os
import re

from ...model.Lab import Lab
from ...manager.docker import DockerManager
from ...utils import check_value,getHostname,check_common_ancestor
class IntParser(object):
    
    @staticmethod
    def parse(path):
        lab_int_path = os.path.join(path, 'lab.int')

        if os.path.exists(lab_int_path):
            
            # Reads lab.conf in memory so it is faster.
            with open(lab_int_path, 'r') as lab_file:
                lab_mem_file = mmap.mmap(lab_file.fileno(), 0, access=mmap.ACCESS_READ)

            lab = Lab(path)

            line_number = 1
            line = lab_mem_file.readline().decode('utf-8')
            while line:
                matches = re.search(r"^(?P<key>\"(\w+.)+\")=(?P<value>\"(\w+.)+\")$",
                                    line.strip()
                                    )
                if matches:
                    #Deve essere locale alla macchina che legge il lab.int
                    key = matches.group("key").replace('"', '').replace("'", '')
                    #Dominio diverso da quello della macchina che legge il lab.int
                    value = matches.group("value").replace('"', '').replace("'", '')
                    if not(check_common_ancestor(key,value)):
                        raise Exception("[ERROR] In line %d: "
                                        "la macchina %s non è un antenato comune di %s e %s " %(line_number,getHostname(),key,value))
                else:
                    raise Exception("[ERROR] In line %d: Invalid characters `%s`." % (line_number, line))

                line_number += 1
                line = lab_mem_file.readline().decode('utf-8')
                
                
            
            lab.check_integrity()
            
            return lab
        
        else:
            print("Lab.int non presente")

    

