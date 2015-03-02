#!/usr/bin/python

with open('/scr/hugo1/getwell/glm_randomise/glm_5/subjects_glm5.txt', 'r') as f:
    subjects=[line.strip() for line in f]


dmn_diff=[]

for sub in subjects:
    dmn_diff.append('/scr/hugo1/getwell/diffmaps/dmn_diffmap_'+sub+'.nii.gz')

with open ('/scr/hugo1/getwell/glm_randomise/glm_5/glm5_mergelist.txt', 'w') as f:
    for file in dmn_diff:
        f.write(file+'\n')

