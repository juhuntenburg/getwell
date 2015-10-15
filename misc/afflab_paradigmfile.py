#!/usr/bin/python
# coding: utf-8
# builds freesurfer fs fast compatible paradigm file
# from original presentation logfiles

# libraries
import pandas as pd
import numpy as np
from glob import glob as glob
import os

# set path
data_dir = '/home/getwell/data/raw/log_phys/' # path to subjects logfile 
output_dir = '/home/getwell/data/afflab/' # path to subjects afflab folder

# loop over subjects
subjects=['131a','131b','134a','134b']

for subject_id in subjects:
    print subject_id

    # check whether file exists and delete it if necessary
    #if os.direxists(output_dir+subject_id+'/regressors')==False:
    #    os.makedirs(output_dir+subject_id+'/regressors')
    if os.path.exists(output_dir+subject_id+'/'+subject_id+'_afflab.par'):
        os.remove(output_dir+subject_id+'/'+subject_id+'_afflab.par')

    # read in logfile
    logpath=glob(data_dir+subject_id+'*/log/*-afflab.log')[0]
    log=pd.read_csv(logpath, delimiter='\t',header=0, skiprows=[0,1,2,4])
    
    # build dataframe with only code and time rows and only relevant events (skipping 255 pulse)
    df=log.iloc[:,[3,4]]
    event=df[(df['Code']=='fix')|(df['Code']=='neutral')|(df['Code']=='glücklich')|(df['Code']=='wütend')|(df['Code']=='long_fix')|(df['Code']=='instruction_next_block')]
    first_pulse=df[df['Code']=='255'].iloc[0]['Time']
    
    # build array for freesurfer parameter file
    par=[[]]

    # loop through events, take onset (relative to first pulse) and duration, convert to sec
    # get condition information, write all into array

    for i in range(event.shape[0]-1):
        onset=float(event.iloc[i]['Time']-first_pulse)/10000
        duration=float((event.iloc[i+1]['Time']-event.iloc[i]['Time']))/10000

        if event.iloc[i]['Code']=='long_fix':
            if float(duration-20.0)>0.05:
                print subject_id+' '+session+': long_fix '+str(i)+' bad timing'
            else:
                par.append([('%.3f' % onset),0,('%.3f' % duration),1,'long_fix'])
        elif event.iloc[i]['Code']=='glücklich':
            if float(duration-4.0)>0.05:
                print subject_id+' '+session+': happy '+str(i)+' bad timing'
            else: 
                par.append([('%.3f' % onset),1,('%.3f' % duration),1,'happy'])
        elif event.iloc[i]['Code']=='wütend':
            if float(duration-4.0)>0.05:
                print subject_id+' '+session+': angry '+str(i)+' bad timing'
            else: 
                par.append([('%.3f' % onset),2,('%.3f' % duration),1,'angry'])
        elif event.iloc[i]['Code']=='neutral':
            if float(duration-4.0)>0.05:
                print subject_id+' '+session+': neutral '+str(i)+' bad timing'
            else:
                par.append([('%.3f' % onset),3,('%.3f' % duration),1,'neutral'])
        elif event.iloc[i]['Code']=='fix':
            par.append([('%.3f' % onset),4,('%.3f' % duration),1,'short_fix'])

    # create dataframe and check size
    par_df=pd.DataFrame(par[1:])
    if par_df.shape!=(152,5):
         print subject_id+' '+session+': dataframe bad shape'
         quit()
    
    # save to file
    par_df.to_csv(output_dir+subject_id+'/afflab.par', header=False, index=False, sep='\t')
