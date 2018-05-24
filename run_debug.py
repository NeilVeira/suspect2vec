import os 
import argparse
import re
import signal
import random

import utils
import analyze

def run_debug(name, verbose=False):
    print "Running debug on %s..." %(name)
    stdout,stderr = utils.run("onpoint-cmd --template-file=%s.template" %(name))
    
    if stdout == None:
        print "onpoint-cmd exceeded time limit of 48 hours"
        return False 
    
    #check logs for errors
    log_file = "onpoint-cmd-%s.log" %(name)
    if not os.path.exists(log_file):
        print "Error:"
        print stdout
        print stderr 
        return False        
    log = open(log_file).read()
    if "error:" in log.lower():
        print "vdb failed, check logs"
        return False        

    return True 
    
    
def main(base_name, new_name=None, min_suspects=999999, aggressiveness=0.5, skip_run=False, verbose=False):
    if not os.path.exists(base_name+".template"):
        raise ValueError("File %s does not exist" %(base_name+".template"))
    dir = os.path.dirname(base_name)    
    orig_dir = os.getcwd()
    os.chdir(dir)
    base_name = os.path.basename(base_name)

    if new_name is None:
         success = run_debug(base_name, verbose=verbose)
         os.chdir(orig_dir)  
         return success
    
    else:   
        if not skip_run:
            with open("args.txt","w") as f:
                f.write("%i\n" %(min_suspects))
                f.write("%.3f\n" %(aggressiveness))
            assert os.system("cp %s_embeddings.txt embeddings.txt" %(base_name)) == 0
            assert os.system("cp %s.template %s.template" %(base_name,new_name)) == 0
            
            # Change project name 
            linez = open(new_name+".template").readlines()
            for i in range(len(linez)):
                if linez[i].startswith("PROJECT="):
                    linez[i] = "PROJECT=%s\n" %(new_name)
            with open(new_name+".template","w") as f:
                f.write("".join(linez))
        
            success = run_debug(new_name, verbose=verbose)
            if not success:
                os.chdir(orig_dir) 
                return False
                
        assert os.path.exists(new_name+".vennsawork")
        
        analyze.basic_analysis(base_name, new_name, verbose=verbose)
            
        os.chdir(orig_dir)  
        return True
    
    
def init(parser):
    parser.add_argument("base_name", help="Name of baseline failure.")
    parser.add_argument("new_name", nargs='?', default=None, help="Name of new failure to run. " \
        "If not specified base_name will be run.")
    parser.add_argument("--min_suspects", type=int, default=999999, 
        help="Minimum number of suspects to find before predicting")
    parser.add_argument("--aggressiveness", type=float, default=0.5, help="Threshold below which suspects are blocked")
    parser.add_argument("-v","--verbose", action="store_true", default=False, help="Display more info")
    parser.add_argument("--skip_run", action="store_true", default=False, 
        help="Skip running the debug and just do the suspect prediction analysis")
   
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    init(parser)
    args = parser.parse_args()
    main(args.base_name, args.new_name, args.min_suspects, args.aggressiveness, args.skip_run, args.verbose)