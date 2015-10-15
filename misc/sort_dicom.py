#!/usr/bin/python
# coding: utf-8
# sorts getwell dicoms into different folders
# check if paths are set correctly
# commandline usage: sort_dicom.py -id LOE_ID


# libraries
from glob import glob
import os

# parse commandline arguments
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="sort dicoms")
    parser.add_argument("-loe", dest="loe_id",help="enter loe subject id",required=True)
    args = parser.parse_args()
    loe_id = args.loe_id

# go to subjects dicom folder
path= '/home/getwell/data/raw/dicom/'+loe_id
os.chdir(path)

# sort dicoms
rest1 = glob('*-0002-*.dcm')
nback = glob('*-0003-*.dcm')
rest2 = glob('*-0004-*.dcm')
afflab = glob('*-0005-*.dcm')
anat = glob('*-0006-*.dcm')
one=glob('*-0001-*.dcm')
ninetynine=glob('*-0099-*.dcm')

# make sure the number of dicoms is correct, create directories and sort
if len(rest1) != 257:
        print('rest1 image number not correct')
else:
    os.makedirs('rest1')
    for dicom in rest1:
        os.rename(dicom, 'rest1/'+dicom)

if len(nback) != 293:
    print('nback image number not correct')
else:
    os.makedirs('nback')
    for dicom in nback:
        os.rename(dicom, 'nback/'+dicom)
        
if len(rest2) != 257:
    print('rest2 image number not correct')
else:
    os.makedirs('rest2')
    for dicom in rest2:
        os.rename(dicom, 'rest2/'+dicom)
        
if len(afflab) != 287:
    print('afflab image number not correct')
else:
    os.makedirs('afflab')
    for dicom in afflab:
        os.rename(dicom, 'afflab/'+dicom)
        
if len(anat) !=176:
    print('anatomical image number not correct')
else:
    os.makedirs('anat')
    for dicom in anat:
        os.rename(dicom, 'anat/'+dicom)
        
os.makedirs('01')
for dicom in one:
    os.rename(dicom, '01/'+dicom)

os.makedirs('99')
for dicom in ninetynine:
    os.rename(dicom, '99/'+dicom)