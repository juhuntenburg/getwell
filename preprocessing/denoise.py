from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.fsl as fsl
from nipype.algorithms.misc import TSNR
import nipype.interfaces.utility as util
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.afni as afni
import nipype.interfaces.ants as ants
import nipype.interfaces.io as nio  
import nipype.algorithms.rapidart as ra
from compcor import extract_noise_components
from normalize_timeseries import time_normalizer
from nuissance_regression import create_filter_matrix


def create_denoise_pipeline(name='denoise'):

    # workflow
    denoise = Workflow(name='denoise')

    # Define nodes
    inputnode = Node(interface=util.IdentityInterface(fields=['epi_mean',
                                                              'brain_mask',
                                                              'epi2anat_itk',
                                                              'func', #these are realigned 
                                                              'fs_subjects_dir',
                                                              'fs_subject_id',
                                                              'motion_parameters',
                                                              'highpass_sigma',
                                                              'lowpass_sigma',
                                                              'tr'
                                                                 ]),
                        name='inputnode')
    
    outputnode = Node(interface=util.IdentityInterface(fields=['tsnr_file',
                                                                'noise_mask',
                                                                'csf_mask',
                                                                'brain_mask2func',
                                                                'compcor_components',
                                                                'combined_motion',
                                                                'outlier_files',
                                                                'intensity_files',
                                                                'outlier_stats',
                                                                'outlier_plots',
                                                                'nuissance_regressors',
                                                                'denoised_file',
                                                                'bandpassed_file',
                                                                'normalized_file']),
                     name='outputnode')
    
    
    # project brain mask into func space
    brain_mask2func = Node(ants.ApplyTransforms(dimension=3,
                                                invert_transform_flags=[True],
                                                output_image='T1_brain_mask2epi.nii.gz',
                                                interpolation = 'NearestNeighbor'),
                          'brain2func')
    
    denoise.connect([(inputnode, brain_mask2func, [('epi2anat_itk', 'transforms'),
                                                   ('brain_mask', 'input_image'),
                                                   ('epi_mean', 'reference_image')]),
                      (brain_mask2func, outputnode, [('output_image', 'brain_mask2func')])
                     ])
    
    # mask functional data
    mask_epi = Node(fsl.ApplyMask(out_file='rest_masked.nii.gz'),
                    name='mask_epi')
     
    denoise.connect([(inputnode, mask_epi, [('func', 'in_file')]),
                     (brain_mask2func, mask_epi, [('output_image', 'mask_file')])
                     ])
    
    # detrend epi
    detrend = Node(afni.Detrend(args='-polort 2',
                                outputtype='NIFTI_GZ'),
                   name='detrend')
    
    denoise.connect([(mask_epi, detrend, [('out_file', 'in_file')])])
    
    # calculate tsnr file 
    tsnr = Node(TSNR(),
                name='tsnr')
     
    denoise.connect([(detrend, tsnr, [('out_file', 'in_file')]),
                     (tsnr, outputnode, [('tsnr_file', 'tsnr_file')])])
    
    # threshold the tsnr stddev file to 98th percentile as noise mask for compcor
    getthresh = Node(interface=fsl.ImageStats(op_string='-p 98'),
                           name='getthreshold')
    
    threshold_stddev = Node(fsl.Threshold(out_file='noise_mask.nii.gz'), 
                               name='threshold')
    
    denoise.connect([(tsnr, threshold_stddev, [('stddev_file', 'in_file')]),
                     (tsnr, getthresh, [('stddev_file', 'in_file')]),
                     (getthresh, threshold_stddev, [('out_stat', 'thresh')]),
                     (threshold_stddev, outputnode, [('out_file','noise_mask')])
                     ])
    
    
    # perform artefact detection
    artefact=Node(ra.ArtifactDetect(save_plot=True,
                                    parameter_source='FSL',
                                    mask_type='file',
                                    norm_threshold=1,
                                    zintensity_threshold=3,
                                    ),
                 name='artefact')
    
    denoise.connect([(inputnode, artefact, [('func', 'realigned_files'),
                                            ('motion_parameters', 'realignment_parameters')]),
                     (brain_mask2func, artefact, [('output_image', 'mask_file')]),
                     (artefact, outputnode, [('norm_files', 'combined_motion'),
                                             ('outlier_files', 'outlier_files'),
                                             ('intensity_files', 'intensity_files'),
                                             ('statistic_files', 'outlier_stats'),
                                             ('plot_files', 'outlier_plots')])])
    
    # import aseg file from freesurfer
    def get_aparc_aseg(files):
        for name in files:
            if 'aparc+aseg' in name:
                return name
    
    fs_import = Node(interface=nio.FreeSurferSource(),
                     name = 'fs_import')
    
    denoise.connect([(inputnode, fs_import, [('fs_subjects_dir', 'subjects_dir'),
                                             ('fs_subject_id', 'subject_id')])])

    # extract csf mask for a compcor
    # the values are almost equat to mri_binarize wm+vcsf option
    # apart from: 82 removed (hypointensities), 15 (4th ventricle), 24 (csf) added?
    csfmask = Node(fs.Binarize(match = [2, 41, 251, 252, 253, 254, 255, 4, 5, 14, 43, 44, 72, 31, 63, 15, 24],
                               erode=1,
                               out_type = 'nii.gz',
                               binary_file='wmcsf_mask.nii.gz'), 
                   name='csfmask')
    
    wmcsf_mask2epi = Node(ants.ApplyTransforms(dimension=3,
                                              invert_transform_flags=[True],
                                              output_image='wmcsf_mask2epi.nii.gz',
                                              interpolation = 'NearestNeighbor'),
                          name = 'wmcsf_mask2epi')
    
    
    denoise.connect([(fs_import, csfmask, [(('aparc_aseg', get_aparc_aseg), 'in_file')]),
                     (csfmask, wmcsf_mask2epi, [('binary_file', 'input_image')]),
                     (inputnode, wmcsf_mask2epi, [('epi2anat_itk', 'transforms'),
                                                  ('epi_mean', 'reference_image')]),
                     (wmcsf_mask2epi, outputnode, [('output_image', 'csf_mask')])
                     ])


    # extracting physiological noise components using both acompcor and tcompcor
    compcor = Node(util.Function(input_names=['realigned_file',
                                              'noise_mask_file',
                                              'num_components',
                                              'csf_mask_file',
                                              'realignment_parameters',
                                              'outlier_file',
                                              'selector',
                                              'regress_before_PCA'],
                                     output_names=['noise_components','pre_svd'],
                                     function=extract_noise_components),
                       name='compcor')
    compcor.inputs.num_components = 6
    compcor.inputs.regress_before_PCA = True #regress out motion and outliers before deriving components
    compcor.inputs.selector = [True,True] # do both acompcor and tcompcor
    compcor.inputs.selector = [True,True] # do both acompcor and tcompcor
    
    
    denoise.connect([(inputnode, compcor, [('func', 'realigned_file'),
                                           ('motion_parameters', 'realignment_parameters')]),
                     (threshold_stddev, compcor, [('out_file', 'noise_mask_file')]),
                     (wmcsf_mask2epi, compcor, [('output_image', 'csf_mask_file')]),
                     (compcor, outputnode, [('noise_components', 'compcor_components')]),
                     (artefact, compcor, [('outlier_files', 'outlier_file')])
                     ])


    # create design matrix for nuissance regression
    designmatrix = Node(util.Function(input_names=['motion_params',
                                                   'composite_norm',
                                                   'compcorr_components',
                                                   'global_signal',
                                                   'art_outliers',
                                                   'selector',
                                                   'demean'],
                                        output_names=['filter_file'],
                                        function=create_filter_matrix),
                          name='designmatrix')
    
    designmatrix.inputs.selector=[True, False, True, False, True, True]
    designmatrix.inputs.demean=False
    #[motion_params, composite_norm, compcorr_components, global_signal, art_outliers, motion derivatives]
    
    
    denoise.connect([(artefact, designmatrix, [('outlier_files','art_outliers'),
                                               ('norm_files', 'composite_norm'),
                                               ('intensity_files', 'global_signal'),
                                               ]),
                     (compcor, designmatrix, [('noise_components', 'compcorr_components')]),
                     (inputnode, designmatrix, [('motion_parameters', 'motion_params')]),
                     (designmatrix, outputnode, [('filter_file', 'nuissance_regressors')])
                     ])
        
    # filter out noise from detrended file
    remove_noise = Node(fsl.FilterRegressor(filter_all=True,
                                            out_file='rest_denoised.nii.gz'),
                           name='remove_noise')
    
    denoise.connect([(detrend, remove_noise, [('out_file', 'in_file')]),
                     (designmatrix, remove_noise, [('filter_file', 'design_file')]),
                     (remove_noise, outputnode, [('out_file', 'denoised_file')])
                     ])
    
    # bandpass filter  denoised file
    bandpass_filter = Node(fsl.TemporalFilter(out_file='rest_denoised_bandpassed.nii.gz'),
                              name='bandpass_filter')

    denoise.connect([(inputnode, bandpass_filter,[( 'highpass_sigma','highpass_sigma'),
                                                  ('lowpass_sigma', 'lowpass_sigma')]),
                     (remove_noise, bandpass_filter, [('out_file', 'in_file')]),
                     (bandpass_filter, outputnode, [('out_file', 'bandpassed_file')])
                     ])
    
    
    # normalize scans
    normalize_time=Node(util.Function(input_names=['in_file','tr'],
                                         output_names=['out_file'],
                                         function=time_normalizer),
                           name='normalize_time')
    
    
    denoise.connect([(inputnode, normalize_time, [('tr', 'tr')]),
                     (bandpass_filter, normalize_time, [('out_file', 'in_file')]),
                     (normalize_time, outputnode, [('out_file', 'normalized_file')])
                     ])
    
    return denoise
