#!/bin/bash

mergelist=/scr/hugo1/getwell/glm_randomise/glm_5/glm5_mergelist.txt
merged_file=/scr/hugo1/getwell/glm_randomise/glm_5/test_glm5_dmn_merged.nii.gz
glm=/scr/hugo1/getwell/glm_randomise/glm_5/glm5
randomise_out=/scr/hugo1/getwell/glm_randomise/test_randomise_5/

fslmerge -t $merged_file `cat ${mergelist}`

randomise -i $merged_file -o $randomise_out -d ${glm}.mat -t ${glm}.con -T
