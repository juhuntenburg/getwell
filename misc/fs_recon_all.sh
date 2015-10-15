#!/bin/bash

#subjects= 134b 131b

for subject in 134b 131b ; do
	echo "creating freesurfer subject" $subject
	recon-all -s $subject \
	-i /home/getwell/data/anat/$subject/anat.nii.gz

	echo "extracting surface subject" $subject
	recon-all -all -subjid $subject
done
 
