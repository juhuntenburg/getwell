#!/usr/bin/env python

import os                                    # system functions
import nipype.interfaces.io as nio           # Data i/o
import nipype.interfaces.fsl as fsl          # fsl
import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.algorithms.rapidart as ra      # artifact detection
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.c3 as c3
import nipype.interfaces.ants as ants


def create_preproc_pipeline(name):

# based on nipype example workflow fMRI: FSL
# This is a generic fsl feat preprocessing workflow encompassing skull stripping
# motion correction and smoothing operations.


  
  """
  Set scan specific parameters
  ==================================================================================
  """

  hpcutoff = 0.008  # in Hz (=1/sec), 0.008 is approx 128 sec 
  TR = 2.3


  """
  Get workflow started
  ==================================================================================
  """

  # Initiate workflow
  preproc = pe.Workflow(name=name)

  # Inputnode to access data
  inputnode = pe.Node(interface=util.IdentityInterface(fields=['func',
                                                               'subject_id',
                                                               'subjects_dir']),
                      name='inputnode')

  # Outputnode to collect data
  outputnode = pe.Node(interface=util.IdentityInterface(fields=['motion_par',
                                                               'motion_mat',
                                                               'motion_rms',
                                                               'motion_plots',
                                                               'rms_plot',
                                                               'moco_timeseries',
                                                               'moco_bet_mask', # bet masking
                                                               'moco_bet_mean', 
                                                               'moco_bet_intthr_mask', # additional intensity threshold masking
                                                               'moco_bet_intthr_dil_mask',
                                                               'moco_bet_intthr_dil_mean', # UNSMOOTHED MEAN TO USE FOR COREG
                                                               'moco_bet_intthr_dil_smooth_timeseries', 
                                                               'moco_bet_intthr_dil_smooth_intnorm_timeseries', # mean intensitiy of each volume normalized to 1000
                                                               'moco_bet_intthr_dil_smooth_intnorm_highpass_timeseries', # FINAL TIMESERIES IN SUBJECT SPACE
                                                               'moco_bet_intthr_dil_smooth_intnorm_highpass_mean',
                                                               'art_voxel_displacement_timeseries',
                                                               'art_global_intensity',
                                                               'art_composite_norm',
                                                               'art_outlier_volume_list',
                                                               'art_outlier_plot',
                                                               'art_statistics',
                                                               'moco_bet_intthr_dil_coreg_mean',
                                                               'epi2anat_mat',
                                                               'epi2anat_dat',
                                                               'epi2anat_itk',
                                                               'epi2anat_mincost',
                                                               'anat_head',
                                                               'anat_brain']),
                      name='outputnode')

  """
  Convert images to float
  ==================================================================================
  """

  # Default fsl output to nii.gz
  fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

  # Convert functional images to float representation. Since there can be more than
  # one functional run we use a MapNode to convert each run.
  img2float = pe.MapNode(interface=fsl.ImageMaths(out_data_type='float',
                                               op_string = '',
                                               suffix='_dtype'),
                         iterfield=['in_file'],
                         name='img2float')
  preproc.connect(inputnode, 'func', img2float, 'in_file')



  """
  Motion correction to middle volume
  ==================================================================================
  """

  # Extract the middle volume of the first run as the reference
  extract_ref = pe.Node(interface=fsl.ExtractROI(t_size=1),
                        name = 'extractref')

  # Define a function to pick the first file from a list of files
  def pickfirst(files):
      if isinstance(files, list):
          return files[0]
      else:
          return files

  preproc.connect(img2float, ('out_file', pickfirst), extract_ref, 'in_file')

  # Define a function to return the 1 based index of the middle volume
  def getmiddlevolume(func):
      from nibabel import load
      funcfile = func
      if isinstance(func, list):
          funcfile = func[0]
      _,_,_,timepoints = load(funcfile).get_shape()
      return (timepoints/2)-1

  preproc.connect(inputnode, ('func', getmiddlevolume), extract_ref, 't_min')

  # Realign the functional runs to the middle volume of the first run
  motion_correct = pe.MapNode(interface=fsl.MCFLIRT(save_mats = True,
                                                    save_plots = True, 
                                                    save_rms = True,
                                                    out_file='moco_timeseries.nii.gz'),
                              name='realign',
                              iterfield = ['in_file'])
  preproc.connect(img2float, 'out_file', motion_correct, 'in_file')
  preproc.connect(extract_ref, 'roi_file', motion_correct, 'ref_file')

  # Plot the estimated motion parameters
  plot_motion = pe.MapNode(interface=fsl.PlotMotionParams(in_source='fsl'),
                          name='plot_motion',
                          iterfield=['in_file'])
  plot_motion.iterables = ('plot_type', ['rotations', 'translations'])
  preproc.connect(motion_correct, 'par_file', plot_motion, 'in_file')

  plot_rms = pe.MapNode(interface=fsl.PlotMotionParams(in_source='fsl',
    plot_type='displacement'),
                          name='plot_rms',
                          iterfield=['in_file'])
  preproc.connect(motion_correct, 'rms_files', plot_rms, 'in_file')

  # send relevant output to outputnode
  preproc.connect([(motion_correct, outputnode, [(('out_file', pickfirst), 'moco_timeseries'),
                                                ('par_file', 'motion_par'),
                                                ('rms_files', 'motion_rms'),
                                                ('mat_file', 'motion_mat')]),
                  (plot_rms, outputnode, [('out_file', 'rms_plot')]),
                  (plot_motion, outputnode, [('out_file', 'motion_plots')])
                  ])

  """
  EPI masking with bet and threshold 10 percent of 98th percentile
  ==================================================================================
  """

  # Calculate the mean volume of the first functional run
  meanfunc = pe.Node(interface=fsl.ImageMaths(op_string = '-Tmean',
                                              suffix='_mean'),
                     name='meanfunc')
  preproc.connect(motion_correct, ('out_file', pickfirst), meanfunc, 'in_file')

  # Strip the skull from the mean functional to generate a mask
  meanfuncmask = pe.Node(interface=fsl.BET(mask = True,
                                           out_file='moco_bet.nii.gz',
                                           frac = 0.3),
                         name = 'meanfuncmask')
  preproc.connect(meanfunc, 'out_file', meanfuncmask, 'in_file')

  # Mask the functional runs with the extracted mask
  maskfunc = pe.MapNode(interface=fsl.ImageMaths(suffix='_bet',
                                                 op_string='-mas'),
                        iterfield=['in_file'],
                        name = 'maskfunc')
  preproc.connect(motion_correct, 'out_file', maskfunc, 'in_file')
  preproc.connect(meanfuncmask, 'mask_file', maskfunc, 'in_file2')

  # Determine the 2nd and 98th percentile intensities of each functional run
  getthresh = pe.MapNode(interface=fsl.ImageStats(op_string='-p 2 -p 98'),
                         iterfield = ['in_file'],
                         name='getthreshold')
  preproc.connect(maskfunc, 'out_file', getthresh, 'in_file')

  # Make a mask based on intensity thresholidng: 10% of the 98th percentile
  threshold = pe.Node(interface=fsl.ImageMaths(out_data_type='char',
                                               out_file='moco_bet_intthr_mask.nii.gz'),
                      name='threshold')
  preproc.connect(maskfunc, ('out_file', pickfirst), threshold, 'in_file')

  # Define a function to get 10% of the intensity
  def getthreshop(thresh):
      return '-thr %.10f -Tmin -bin'%(0.1*thresh[0][1])
  preproc.connect(getthresh, ('out_stat', getthreshop), threshold, 'op_string')


  # Send relevant outputs to outputnode
  preproc.connect([(meanfuncmask, outputnode, [('mask_file', 'moco_bet_mask'),
                                                ('out_file', 'moco_bet_mean')]),
                  (threshold, outputnode, [('out_file', 'moco_bet_intthr_mask' )])])

  """
  Smoothing with SUSAN
  ==================================================================================
  """

  # Determine the median value of the functional runs using the mask 
  # i.e the median of the func when lower 10% of 98 percentile are removed
  medianval = pe.MapNode(interface=fsl.ImageStats(op_string='-k %s -p 50'),
                         iterfield = ['in_file'],
                         name='medianval')
  preproc.connect(motion_correct, 'out_file', medianval, 'in_file')
  preproc.connect(threshold, 'out_file', medianval, 'mask_file')

  # Dilate the mask
  dilatemask = pe.Node(interface=fsl.ImageMaths(suffix='_dil',
                                                op_string='-dilF'),
                       name='dilatemask')
  preproc.connect(threshold, 'out_file', dilatemask, 'in_file')

  # Mask the motion corrected functional runs with the dilated mask
  maskfunc2 = pe.MapNode(interface=fsl.ImageMaths(suffix='_mask',
                                                  op_string='-mas'),
                         iterfield=['in_file'],
                         name='maskfunc2')
  preproc.connect(motion_correct, 'out_file', maskfunc2, 'in_file')
  preproc.connect(dilatemask, 'out_file', maskfunc2, 'in_file2')

  # Determine the mean image from each functional run
  meanfunc2 = pe.MapNode(interface=fsl.ImageMaths(op_string='-Tmean',
                                                  out_file='moco_bet_intthr_dil_mean.nii.gz'),
                         iterfield=['in_file'],
                         name='meanfunc2')
  preproc.connect(maskfunc2, 'out_file', meanfunc2, 'in_file')

  # Merge the median values with the mean functional images into a coupled list
  mergenode = pe.Node(interface=util.Merge(2, axis='hstack'),
                      name='merge')
  preproc.connect(meanfunc2,'out_file', mergenode, 'in1')
  preproc.connect(medianval,'out_stat', mergenode, 'in2')

  # Smooth each run using SUSAN with the brightness threshold set to 75% of the
  # median value for each run and a mask constituting the mean functional image
  # edges of contrast smaller than the brightness threshold will be blurred (supposed noise)
  smooth = pe.MapNode(interface=fsl.SUSAN(fwhm=6.0),
                      iterfield=['in_file', 'brightness_threshold','usans'],
                      name='smooth')

  # Define two functions to get the brightness threshold for SUSAN 
  # this returns a list (in case of several func runs) of tuples with the meand image and the brightness value
  def getbtthresh(medianvals):
      return [0.75*val for val in medianvals]

  def getusans(x):
      return [[tuple([val[0],0.75*val[1]])] for val in x]

  preproc.connect(maskfunc2, 'out_file', smooth, 'in_file')
  preproc.connect(medianval, ('out_stat', getbtthresh), smooth, 'brightness_threshold')
  preproc.connect(mergenode, ('out', getusans), smooth, 'usans')

  # Mask the smoothed data with the dilated mask
  maskfunc3 = pe.MapNode(interface=fsl.ImageMaths(out_file='moco_bet_intthr_dil_smooth_timeseries.nii.gz',
                                                  op_string='-mas'),
                         iterfield=['in_file'],
                         name='maskfunc3')
  preproc.connect(smooth, 'smoothed_file', maskfunc3, 'in_file')
  preproc.connect(dilatemask, 'out_file', maskfunc3, 'in_file2')

  # Sending relevant output to outputnode
  preproc.connect([(meanfunc2, outputnode, [('out_file', 'moco_bet_intthr_dil_mean')]),
                   (dilatemask, outputnode, [('out_file', 'moco_bet_intthr_dil_mask')]),
                   (maskfunc3, outputnode, [('out_file','moco_bet_intthr_dil_smooth_timeseries')])
                   ])

  """
  Median adjustment (porportional scaling)
  ==================================================================================
  """

  # Scale each volume of the run so that the median value of the run is set to 10000
  intnorm = pe.MapNode(interface=fsl.ImageMaths(out_file='moco_bet_intthr_dil_smooth_intnorm_timeseries.nii.gz'),
                       iterfield=['in_file','op_string'],
                       name='intnorm')
  preproc.connect(maskfunc3, 'out_file', intnorm, 'in_file')

  # Define a function to get the scaling factor for intensity normalization
  def getinormscale(medianvals):
      return ['-mul %.10f'%(10000./val) for val in medianvals]
  preproc.connect(medianval, ('out_stat', getinormscale), intnorm, 'op_string')

  # Sending output to outputnode
  preproc.connect([(intnorm, outputnode, [('out_file', 'moco_bet_intthr_dil_smooth_intnorm_timeseries')])])



  """
  Highpass filtering
  ==================================================================================
  """

  # Perform temporal highpass filtering on the data
  highpass = pe.MapNode(interface=fsl.ImageMaths(out_file='moco_bet_intthr_dil_smooth_intnorm_highpass_timeseries.nii.gz',
    op_string = '-bptf %d -1'%(1/(2*TR*hpcutoff))),
                        iterfield=['in_file'],
                        name='highpass')

  # bptf needs input in sigma/volumes, which can be derived from cutoff in Hz as sigma/vol= 1/(2*TR*cutoff_in_hz)
  # https://www.jiscmail.ac.uk/cgi-bin/webadmin?A2=ind1205&L=FSL&P=R58005&1=FSL&9=A&I=-3&J=on&K=2&d=No+Match%3BMatch%3BMatches&z=4
  # -1 means no lowpass filter is used

  preproc.connect(intnorm, 'out_file', highpass, 'in_file')

  # Generate a mean functional image from the so far processed first run
  meanfunc3 = pe.MapNode(interface=fsl.ImageMaths(op_string='-Tmean',
                                                  out_file='moco_bet_intthr_dil_smooth_intnorm_highpass_mean.nii.gz'),
                         iterfield=['in_file'],
                         name='meanfunc3')
  preproc.connect(highpass, ('out_file', pickfirst), meanfunc3, 'in_file')

  #Sending relevant output to outputnode
  preproc.connect([(highpass, outputnode, [(('out_file', pickfirst),'moco_bet_intthr_dil_smooth_intnorm_highpass_timeseries')]),
                   (meanfunc3, outputnode, [('out_file', 'moco_bet_intthr_dil_smooth_intnorm_highpass_mean')])])




  """
  Artefact detection
  ==================================================================================
  """

  # Use `nipype.algorithms.rapidart` to determine which of the
  # images in the functional series (unsmoothed) are outliers based on deviations in
  # intensity and/or movement.
  art = pe.MapNode(interface=ra.ArtifactDetect(use_differences = [True, False],
                                               use_norm = True,
                                               norm_threshold = 1,
                                               zintensity_threshold = 3,
                                               parameter_source = 'FSL',
                                               mask_type = 'file'),
                   iterfield=['realigned_files', 'realignment_parameters'],
                   name="art")


  preproc.connect([(motion_correct, art, [('par_file','realignment_parameters')]),
                   (maskfunc2, art, [('out_file','realigned_files')]),
                   (dilatemask, art, [('out_file', 'mask_file')]),
                   (art, outputnode, [('displacement_files', 'art_voxel_displacement_timeseries'),
                                      ('intensity_files', 'art_global_intensity'),
                                      ('norm_files', 'art_composite_norm'),
                                      ('outlier_files','art_outlier_volume_list'),
                                      ('plot_files', 'art_outlier_plot'),
                                      ('statistic_files', 'art_statistics')])
                   ])





  """
  Calculate coregistration
  ==================================================================================
  """

  ### changed this to freesurfer. 
  ### beware: registration is the opposite way around as before ?

  # Coregistration of unsmoothed mean (meanfunc2) to FreeSurfer processed structurals with bbregister

  freesource=pe.Node(nio.FreeSurferSource(),
    name='freesource')

  bbregister=pe.Node(fs.BBRegister(contrast_type='t2',
    init='fsl',
    out_fsl_file='epi2anat.mat',
    out_reg_file='epi2anat.dat',
    registered_file='moco_bet_intthr_dil_mean_coreg.nii.gz'),
    name='bbregister')


  # convert freesurfer files to nii.gz for later reuse
  convert_head=pe.Node(fs.MRIConvert(out_type='niigz'),
    name='convert_head')

  convert_brain=pe.Node(fs.MRIConvert(out_type='niigz'),
    name='convert_brain')


  # convert fsl style mat file to itk for later use with ants
  #c3d_affine = pe.Node(c3.C3dAffineTool(fsl2ras=True,
  #                                   itk_transform='epi2anat.txt'),
  #                     name='c3d_affine')


  # function to get freesurfer subject id (in our case almost always b!) from inputnode subject id
  def fs_subject(id):
    fs_id=id[0:3]+'b'
    return fs_id

  preproc.connect([(inputnode, freesource, [(('subject_id',fs_subject), 'subject_id')]),
    (inputnode, freesource, [('subjects_dir', 'subjects_dir')]),
    (inputnode, bbregister, [(('subject_id',fs_subject), 'subject_id')]),
    (inputnode, bbregister, [('subjects_dir', 'subjects_dir')]),
    (meanfunc2, bbregister,[(('out_file',pickfirst),'source_file')]),
    (freesource, convert_head, [('T1', 'in_file')]),
    (freesource, convert_brain, [('brain', 'in_file')]),
    (convert_head, outputnode, [('out_file', 'anat_head')]),
    (convert_brain, outputnode, [('out_file', 'anat_brain')]),
    (bbregister, outputnode, [('registered_file', 'moco_bet_intthr_dil_coreg_mean'),
                              ('out_fsl_file', 'epi2anat_mat'),
                              ('out_reg_file', 'epi2anat_dat'),
                              ('min_cost_file', 'epi2anat_mincost')]),
    #(bbregister, c3d_affine, [('out_fsl_file', 'source_file')]),
    #(c3d_affine, outputnode, [('itk_transform', 'epi2anat_itk')])
    ])



  """
  Calculate normalization
  ==================================================================================
  """



  """
  Return workflow
  =====================================================================================
  """

  return preproc