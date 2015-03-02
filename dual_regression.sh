#!/bin/bash

ica_template=/scr/hugo1/getwell/rsn_networks10/all_networks.nii.gz
out_dir=/scr/hugo1/getwell/dual_regression/
file_list=/scr/hugo1/getwell/subjects_dual_regression.txt

dual_regression $ica_template 1 -1 0 $out_dir `cat ${file_list}`
