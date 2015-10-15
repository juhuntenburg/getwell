
import os                                    # system functions
import nipype.interfaces.io as nio           # Data i/o
import nipype.interfaces.fsl as fsl          # fsl
import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.algorithms.rapidart as ra      # artifact detection
import nipype.interfaces.freesurfer as fs
from preproc import create_preproc_pipeline



"""
Set up complete workflow
==================================================================================
"""


# directories and variables
data_dir='/home/getwell/data/nback/'
fs_subjects_dir='/home/getwell/data/freesurfer'
out_dir='/home/getwell/data/nback/'
#subjects=['107a']
subjects=[]
f = open('/home/getwell/data/nback/nback_subjects.txt','r')
for line in f:
    subjects.append(line.strip())



# main workflow 
main=pe.Workflow(name='main')
main.base_dir='/home/getwell/data/nback/working_dir/'
main.config['execution'] = {'remove_unnecessary_outputs': 'False'}


# infosource to iterate over subjects
infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_id', 'subjects_dir']),
                     name="infosource")
infosource.iterables = ('subject_id', subjects)
infosource.inputs.subjects_dir=fs_subjects_dir


# datasource to grab data
datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id'],
                                               outfields=['func'],
                                               base_directory=data_dir,
                                               sort_filelist=True,
                                               template='%s/func/nback_orig.nii.gz',
                                               template_args = dict(func=[['subject_id']])),
                     name = 'datasource')


# datasink to store data
sink = pe.Node(interface=nio.DataSink(base_directory=out_dir,
                                      parameterization=False),
                     name='sink')

# preproc pipeline
preproc=create_preproc_pipeline(name='preproc')


#connections
main.connect([(infosource, datasource, [('subject_id', 'subject_id')]),
  (infosource, preproc, [('subjects_dir', 'inputnode.subjects_dir'),
                           ('subject_id', 'inputnode.subject_id')]),
  (datasource, preproc, [('func', 'inputnode.func')]),
  (infosource, sink, [('subject_id', 'container')]),
  (preproc, sink, [('outputnode.motion_par','preproc.motion.@par'),
                      ('outputnode.motion_mat','preproc.motion.MAT.@mat'),
                      ('outputnode.motion_rms','preproc.motion.@rms'),
                      ('outputnode.motion_plots','preproc.motion.@plot'),
                      ('outputnode.rms_plot','preproc.motion.@rmsplot'),
                      ('outputnode.moco_timeseries','preproc.motion.@timeseries'),
                      ('outputnode.moco_bet_mask', 'preproc.masking.@bet_mask'),
                      ('outputnode.moco_bet_mean', 'preproc.masking.@bet_mean_masked'),
                      ('outputnode.moco_bet_intthr_mask', 'preproc.masking.@intthr_mask'),
                      ('outputnode.moco_bet_intthr_dil_mask', 'preproc.masking.@intthr_mask_dil'),
                      ('outputnode.moco_bet_intthr_dil_mean', 'preproc.masking.@intthr_dil_mean_masked'),
                      ('outputnode.moco_bet_intthr_dil_smooth_timeseries', 'preproc.smoothing.@smoothed_ts'),
                      ('outputnode.moco_bet_intthr_dil_smooth_intnorm_timeseries', 'preproc.smoothing.@smoothed_intnorm_ts'),
                      ('outputnode.moco_bet_intthr_dil_smooth_intnorm_highpass_timeseries', 'preproc.highpass.@highpass_ts'),
                      ('outputnode.moco_bet_intthr_dil_smooth_intnorm_highpass_mean', 'preproc.highpass.@highpass_mean'),
                      ('outputnode.art_voxel_displacement_timeseries', 'preproc.artefacts.@displacement_ts'),
                      ('outputnode.art_global_intensity', 'preproc.artefacts.@global_int'),
                      ('outputnode.art_composite_norm', 'preproc.artefacts.@composite_norm'),
                      ('outputnode.art_outlier_volume_list', 'preproc.artefacts.@outlier_list'),
                      ('outputnode.art_outlier_plot', 'preproc.artefacts.@plot'),
                      ('outputnode.art_statistics', 'preproc.artefacts.@stats'),
                      ('outputnode.moco_bet_intthr_dil_coreg_mean', 'preproc.coreg.@mean'),
                      ('outputnode.epi2anat_mat','preproc.coreg.@mat'),
                      ('outputnode.epi2anat_dat','preproc.coreg.@dat'),
                      ('outputnode.epi2anat_itk','preproc.coreg.@itk'),
                      ('outputnode.epi2anat_mincost','preproc.coreg.@mincost'),
                      ('outputnode.anat_head','preproc.anatomy.@head'),
                      ('outputnode.anat_brain','preproc.anatomy.@brain')])
  ])


main.write_graph('graph.dot', graph2use='hierarchical', format='pdf', simple_form=True)
main.run()