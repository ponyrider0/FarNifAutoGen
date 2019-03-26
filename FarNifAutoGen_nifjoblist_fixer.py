import os.path

nif_list_jobfile = "nif_list.job"
nif_joblist = dict()

if not os.path.exists(nif_list_jobfile):
    print "no nif joblist found. exiting."
    exit()
else:
    print "joblist found"
    
nifjob_stream = open(nif_list_jobfile, "r")
for line in nifjob_stream:
    line = line.rstrip("\r\n")
    nif_filename, ref_scale = line.split(',')
    if nif_joblist.get(nif_filename) == None:
        nif_joblist[nif_filename] = float(ref_scale)
    else:
        if ref_scale > nif_joblist[nif_filename]:
            nif_joblist[nif_filename] = float(ref_scale)
nifjob_stream.close()

nif_list_jobfile = nif_list_jobfile.replace(".job","-B.job")

nifjob_stream = open(nif_list_jobfile, "w")
for nif_filename in nif_joblist:
#    print nif_filename + "," + str(nif_joblist[nif_filename])
    line = nif_filename + "," + str(nif_joblist[nif_filename]) + "\n"
    nifjob_stream.write(line)
nifjob_stream.close()
