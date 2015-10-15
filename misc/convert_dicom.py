#!/usr/bin/python

# libraries
import dcmstack
from glob import glob
import dicom
import nibabel
import os

# parse commandline arguments
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="convert dicoms to nifti")
    parser.add_argument("-getwell", dest="getwell_id",help="enter getwell subject id",required=True)
    parser.add_argument("-loe", dest="loe_id",help="enter loe subject id",required=True)
    args = parser.parse_args()
    getwell_id = args.getwell_id
    loe_id = args.loe_id

# convert and save anatomy
anat_dicom='/home/getwell/data/raw/dicom/'+loe_id+'/anat/'
anat_dir='/home/getwell/data/anat/'+getwell_id+'/'
os.makedirs(anat_dir)


anat_stack = dcmstack.DicomStack()

for file in glob(anat_dicom+'*.dcm'):
    anat_dc = dicom.read_file(file, force=True)
    anat_stack.add_dcm(anat_dc)

anat_nii = anat_stack.to_nifti(embed_meta=True)
nibabel.save(anat_nii, anat_dir+'anat.nii.gz')



# convert and save different tasks

for task in ['nback','afflab','rest1', 'rest2']: #'afflab'
	func_dicom='/home/getwell/data/raw/dicom/'+loe_id+'/'+task+'/'
	func_dir='/home/getwell/data/'+task+'/'+getwell_id+'/func/'
	os.makedirs(func_dir)
	func_stack = dcmstack.DicomStack()

	for file in glob(func_dicom+'*.dcm'):
		func_dc = dicom.read_file(file, force=True)
		func_stack.add_dcm(func_dc)
	
	func_nii = func_stack.to_nifti(embed_meta=True)
	nibabel.save(func_nii, func_dir+task+'_orig.nii.gz')