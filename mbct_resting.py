from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import nipype.interfaces.afni as afni
from strip_rois import strip_rois_func
from moco import create_moco_pipeline
from coreg import create_coreg_pipeline
from transform_timeseries import create_transform_pipeline
from denoise import create_denoise_pipeline

# subjects
subjects = []
for line in open('/scr/ilz2/getwell/subject_resting_2ndround.txt','r').readlines():
    subjects.append(line.strip())

subjects=['106a','106b']

# settings
vol_to_remove = 5
epi_resolution = 3
TR = 2.3
lowpass=0.1
highpass = 0.01

# set directories
working_dir = '/scr/ilz2/getwell/working_dir/'
data_dir = '/scr/ilz2/getwell/'
out_dir = '/scr/ilz2/getwell/preprocessed/'
freesurfer_dir = '/scr/ilz2/getwell/freesurfer/' 
standard_brain = '/usr/share/fsl/5.0/data/standard/MNI152_T1_1mm_brain.nii.gz'
standard_brain_2mm = '/usr/share/fsl/5.0/data/standard/MNI152_T1_2mm_brain.nii.gz'
standard_brain_2mm_mask = '/usr/share/fsl/5.0/data/standard/MNI152_T1_2mm_brain_mask.nii.gz'

# set fsl output type to nii.gz
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

# main workflow
func_preproc = Workflow(name='mbct_resting')
func_preproc.base_dir = working_dir
func_preproc.config['execution']['crashdump_dir'] = func_preproc.base_dir + "/crash_files"

# infosource to iterate over scans
subject_infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='subject_infosource')
subject_infosource.iterables=('subject_id', subjects)

def trim_id(subject_id):
    short_id = subject_id[:3]
    return short_id

def prepost(subject_id):
    if subject_id[3]=='a':
        prepost=subject_id[:3]+'/rest_pre'
    elif subject_id[3]=='b':
        prepost=subject_id[:3]+'/rest_post'
    return prepost
    

# select files
templates={'func': 'nifti/{subject_id}/rest.nii.gz',
           'anat_head' : 'preprocessed/{short_id}/anat/T1.nii.gz',
           'anat_brain' : 'preprocessed/{short_id}/anat/T1_brain.nii.gz',
           'brain_mask' : 'preprocessed/{short_id}/anat/T1_brain_mask.nii.gz',
           'anat2std_lin': 'preprocessed/{short_id}/anat/transform0GenericAffine.mat',
           'anat2std_nonlin': 'preprocessed/{short_id}/anat/transform1Warp.nii.gz'
           }
selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")


# node to remove first volumes
remove_vol = Node(util.Function(input_names=['in_file','t_min'],
                                output_names=["out_file"],
                                function=strip_rois_func),
                  name='remove_vol')
remove_vol.inputs.t_min = vol_to_remove

# slicetimecorrection
slicetime = Node(afni.TShift(tr=str(TR),
                             tzero=0,
                             tpattern='alt+z',
                             outputtype='NIFTI_GZ'),
                 name='slicetimer')

# workflow for motion correction
moco=create_moco_pipeline()

# workflow for coregistration
coreg=create_coreg_pipeline()
coreg.inputs.inputnode.fs_subjects_dir=freesurfer_dir

# workflow to denoise timeseries
denoise = create_denoise_pipeline()
denoise.inputs.inputnode.fs_subjects_dir = freesurfer_dir
denoise.inputs.inputnode.highpass_sigma= 1./(2*TR*highpass)
denoise.inputs.inputnode.lowpass_sigma= 1./(2*TR*lowpass)
denoise.inputs.inputnode.tr = TR
# https://www.jiscmail.ac.uk/cgi-bin/webadmin?A2=ind1205&L=FSL&P=R57592&1=FSL&9=A&I=-3&J=on&d=No+Match%3BMatch%3BMatches&z=4

# workflow for applying transformations to timeseries
transform_ts = create_transform_pipeline()
transform_ts.inputs.inputnode.mni = standard_brain_2mm
transform_ts.inputs.inputnode.mni_mask = standard_brain_2mm_mask

#sink to store files
sink = Node(nio.DataSink(parameterization=False,
                         base_directory=out_dir,
                         substitutions=[('plot.rest_realigned', 'outlier_plot'),
                                        ('filter_motion_comp_norm_compcor_art_dmotion', 'nuissance_matrix'),
                                        ('rest_realigned.nii.gz_abs.rms', 'rest_realigned_abs.rms'),
                                        ('rest_realigned.nii.gz.par','rest_realigned.par'),
                                        ('rest_realigned.nii.gz_rel.rms', 'rest_realigned_rel.rms'),
                                        ('rest_realigned.nii.gz_abs_disp', 'abs_displacement_plot'),
                                        ('rest_realigned.nii.gz_rel_disp', 'rel_displacment_plot'),
                                        ('art.rest_coregistered_outliers', 'outliers'),
                                        ('global_intensity.rest_coregistered', 'global_intensity'),
                                        ('norm.rest_coregistered', 'composite_norm'),
                                        ('stats.rest_coregistered', 'stats')]),
             name='sink')


# connections
func_preproc.connect([(subject_infosource, selectfiles, [('subject_id', 'subject_id'),
                                                        (('subject_id', trim_id), 'short_id')]),
                      (subject_infosource, sink, [(('subject_id', prepost), 'container')]),
                      (selectfiles, remove_vol, [('func', 'in_file')]),
                      (remove_vol, slicetime, [('out_file', 'in_file')]),
                      (slicetime, moco, [('out_file', 'inputnode.epi')]),
                      (selectfiles, coreg, [('anat_brain', 'inputnode.anat_brain')]),
                      (subject_infosource, coreg, [(('subject_id', trim_id), 'inputnode.fs_subject_id')]),
                      (moco, coreg, [('outputnode.epi_mean', 'inputnode.epi_mean')]),
                      (subject_infosource, denoise, [(('subject_id', trim_id), 'inputnode.fs_subject_id')]),
                      (selectfiles, denoise, [('brain_mask', 'inputnode.brain_mask')]),
                      (moco, denoise, [('outputnode.epi_moco', 'inputnode.func'),
                                       ('outputnode.par_moco', 'inputnode.motion_parameters'),
                                       ('outputnode.epi_mean', 'inputnode.epi_mean')]),
                      (coreg, denoise, [('outputnode.epi2anat_itk', 'inputnode.epi2anat_itk')]),
                      (denoise, transform_ts, [('outputnode.normalized_file', 'inputnode.orig_ts')]),
                      (selectfiles, transform_ts, [('anat2std_lin', 'inputnode.anat2std_lin'),
                                                   ('anat2std_nonlin', 'inputnode.anat2std_nonlin'),
                                                   ]),
                      (coreg, transform_ts, [('outputnode.epi2anat_itk', 'inputnode.epi2anat_itk')]),
                      (moco, sink, [('outputnode.epi_moco', 'realign.@realigned_ts'),
                                    ('outputnode.par_moco', 'realign.@par'),
                                    ('outputnode.rms_moco', 'realign.@rms'),
                                    ('outputnode.mat_moco', 'realign.MAT.@mat'),
                                    ('outputnode.epi_mean', 'realign.@mean'),
                                    ('outputnode.rotplot', 'realign.plots.@rotplot'),
                                    ('outputnode.transplot', 'realign.plots.@transplot'),
                                    ('outputnode.dispplots', 'realign.plots.@dispplots')]),
                      (coreg, sink, [('outputnode.epi2anat', 'coregister.@epi2anat'),
                                     ('outputnode.epi2anat_mat', 'coregister.@epi2anat_mat'),
                                     ('outputnode.epi2anat_itk', 'coregister.@epi2anat_itk')]),
                      (transform_ts, sink, [('outputnode.trans_ts', '@full_transform_ts'),
                                            ('outputnode.trans_ts_smooth', '@full_transform_ts_smooth'),
                                            ('outputnode.trans_ts_mean', '@full_transform_mean')]),
                    (denoise, sink, [#('outputnode.tsnr_file', 'denoise.@tsnr'),
                                     ('outputnode.noise_mask', 'denoise.@noise_mask'),
                                     ('outputnode.csf_mask', 'denoise.@csf_mask'),
                                     ('outputnode.compcor_components', 'denoise.txtfiles.@compcor'),
                                     ('outputnode.combined_motion','denoise.txtfiles.@combined_motion'),
                                     ('outputnode.outlier_files','denoise.txtfiles.@outlier'),
                                     ('outputnode.intensity_files','denoise.txtfiles.@intensity'),
                                     ('outputnode.outlier_stats','denoise.txtfiles.@outlierstats'),
                                     ('outputnode.outlier_plots','denoise.@outlierplots'),
                                     ('outputnode.nuissance_regressors', 'denoise.txtfiles.@regressors'),
                                     #('outputnode.denoised_file', 'denoise.@denoised_file'),
                                     #('outputnode.bandpassed_file', 'denoise.@bandpassed_file'),
                                     ('outputnode.brain_mask2func', 'denoise.@brain_resamp'),
                                     ('outputnode.normalized_file', 'denoise.@normalized')
                                       ])
                     ])


func_preproc.run(plugin='MultiProc')