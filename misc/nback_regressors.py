#!/usr/bin/python
# coding: utf-8
# builds fsl compatible regressors 
# from original presentation logfiles
# check if paths are correct
# commandline usage: nback_regressors.py -id GETWELL_ID

# libraries
import pandas as pd
import numpy as np
from glob import glob as glob
import os

# set path
data_dir = '/home/getwell/data/raw/log_phys/' # path to subjects logfile 
block_dir = '/home/getwell/data/nback/' # path to xls files with block information
output_dir = '/home/getwell/data/nback/' # path to subjects nback analysis

# parse commandline arguments
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="create nback regressors")
    parser.add_argument("-getwell", dest="getwell_id",help="enter getwell subject id",required=True)
    args = parser.parse_args()
    subject_id = args.getwell_id

# create folders
os.makedirs(output_dir+subject_id+'a/regressors')
os.makedirs(output_dir+subject_id+'b/regressors')


####### main loop for pre and post session #######

# create fix and word (emo and diff valences) regressors for each session and save to txt file
for session in ['pre','post']:
    # read in  logfile and block information
    if session == 'pre':
        logpath=glob(data_dir+subject_id+'a*/log/*-Emo_N_Back.log')[0]
        log=pd.read_csv(logpath, delimiter='\t',header=0, skiprows=[0,1,2,4])
        blocks=pd.read_excel(block_dir+'pre_blocks.xls', 'Tabelle1')
        outpath=output_dir+subject_id+'a/regressors/pre_'+subject_id
    elif session =='post':
        logpath=glob(data_dir+subject_id+'b*/log/*-Emo_N_Back.log')[0]
        log=pd.read_csv(logpath, delimiter='\t',header=0, skiprows=[0,1,2,4])
        blocks=pd.read_excel(block_dir+'post_blocks.xls','Tabelle1')
        outpath=output_dir+subject_id+'b/regressors/post_'+subject_id
    
    # build dataframe with only code and time rows and only start, wordI, break, + events
    df=log.iloc[:,[3,4]]
    event=df[(df['Code']=='Start')|(df['Code']=='WORDI')|(df['Code']=='BREAK')|(df['Code']=='+')]
    first_pulse=df[df['Code']=='255'].iloc[0]['Time']
    
    
    #### build regressors ####
    # first fix: 2nd 'start' to 1st 'wordI'
    fix=[[event.iloc[1,1],event.iloc[2,1]]]
    
    # first emo word block: 1st 'wordI' to 1st 'break'(placeholder)
    emo=[[event.iloc[2,1],np.nan]]
    
    # other blocks, fix: 'break' to 'wordI', emo: 'wordI' to 'break'
    for i in range(event.shape[0]):
        if event.iloc[i]['Code']=='BREAK':
           fix.append([event.iloc[i]['Time'],event.iloc[i+1]['Time']])
           emo[-1][1]=event.iloc[i]['Time']
           emo.append([event.iloc[i+1]['Time'],np.nan])
        elif event.iloc[i]['Code']=='+':
            emo[-1][1]=event.iloc[i]['Time']
    
    # create dataframes, reset time to first pulse onset, divide by 10000to get s
    emo=pd.DataFrame((emo-first_pulse)/10000, columns=['start','end'])
    fix=pd.DataFrame((fix-first_pulse)/10000, columns=['start','end'])
    
    # check if all values are there
    if emo.shape!=(15,2):
        print session+': emo df out of shape'
    if fix.shape!=(15,2):
        print session+': fix df out of shape'
    if np.isnan(emo['start']).max()|np.isnan(emo['end']).max():
        print session+': emo contains nan'
    if np.isnan(fix['start']).max()|np.isnan(fix['end']).max():
        print session+': fix contains nan'
    
    # append column for actual duration of each event, drop end column
    emo['duration']=emo.end-emo.start
    emo=emo.drop('end',1)
    fix['duration']=fix.end-fix.start
    fix=fix.drop('end',1)
    
    # get set values for block durations and compare to actual durations
    emo_dur=blocks[blocks['condition']!='fix'].iloc[:,[3]]
    emo_dur['']=range(15)
    emo_dur=emo_dur.set_index('')
    if (emo-emo_dur)['duration'].max()>1000:
        print session+': timing emo blocks differs too much from set value'
    
    fix_dur = blocks[blocks['condition']=='fix'].iloc[:,[3]]
    fix_dur['']=range(15)
    fix_dur=fix_dur.set_index('')
    if (fix-fix_dur)['duration'].max()>100:
        print session+': timing fix blocks differs too much from set value'
    
    #get valence information and create single regressors
    emo_val=blocks[blocks['condition']!='fix'].iloc[:,[0]]
    emo_val['']=range(15)
    emo_val=emo_val.set_index('')
    emo['valence']=emo_val
    emo['modulation']=1
    fix['modulation']=1
    pos=emo[emo['valence']=='pos'].drop(['valence'],1)
    neu=emo[emo['valence']=='neu'].drop(['valence'],1)
    neg=emo[emo['valence']=='neg'].drop(['valence'],1)
    emo=emo.drop(['valence'],1)
    
    # append modulation column
    fix['modulation']=1
    emo['modulation']=1
    
    #save regressors to file
    fix.to_csv(outpath+'_fix.txt', header=False, index=False, sep='\t')
    emo.to_csv(outpath+'_emo.txt', header=False, index=False, sep='\t')
    neg.to_csv(outpath+'_neg.txt', header=False, index=False, sep='\t')
    neu.to_csv(outpath+'_neu.txt', header=False, index=False, sep='\t')
    pos.to_csv(outpath+'_pos.txt', header=False, index=False, sep='\t')
