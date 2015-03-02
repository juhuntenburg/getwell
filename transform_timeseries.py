from nipype.pipeline.engine import Node, Workflow, MapNode
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.ants as ants
import nipype.interfaces.afni as afni



def create_transform_pipeline(name='transfrom_timeseries'):
    
    # set fsl output type
    fsl.FSLCommand.set_default_output_type('NIFTI_GZ')
    
    # initiate workflow
    transform_ts = Workflow(name='transform_timeseries')
    
    # inputnode
    inputnode=Node(util.IdentityInterface(fields=['orig_ts',
                                                  'mni', 
                                                  'mni_mask',
                                                  'epi2anat_itk',
                                                  'anat2std_lin',
                                                  'anat2std_nonlin']),
                   name='inputnode')
   
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['trans_ts', 
                                                   'trans_ts_smooth',
                                                   'trans_ts_mean']),
                    name='outputnode')
    
    
    # make list of transforms
    def makelist(anat2std_nonlin, anat2std_lin, epi2anat_lin):
        transformlist=[anat2std_nonlin, anat2std_lin, epi2anat_lin]
        return transformlist
    
    transformlist = Node(interface=util.Function(input_names=['epi2anat_lin', 'anat2std_lin', 'anat2std_nonlin'],
                                        output_names=['transformlist'],
                                        function=makelist),
                            name='transformlist')
    
    transform_ts.connect([(inputnode, transformlist, [('epi2anat_itk', 'epi2anat_lin'),
                                                      ('anat2std_lin', 'anat2std_lin'),
                                                      ('anat2std_nonlin', 'anat2std_nonlin')])
                          ])
    
    
    # split timeseries in single volumes
    split=Node(fsl.Split(dimension='t',
                         out_base_name='timeseries'),
                 name='split')
    
    transform_ts.connect([(inputnode, split, [('orig_ts','in_file')])])
    
    # apply all transforms
    applytransform = MapNode(ants.ApplyTransforms(interpolation = 'BSpline'),
                             iterfield=['input_image'],
                             name='applytransform')
       
    transform_ts.connect([(inputnode, applytransform, [('mni', 'reference_image')]),
                          (split, applytransform, [('out_files', 'input_image')]),
                          (transformlist, applytransform, [('transformlist', 'transforms')])
                          ])
    
    
    # re-concatenate volumes
    merge=Node(fsl.Merge(dimension='t',
                         merged_file='rest_preprocessed2std.nii.gz'),
               name='merge')
    transform_ts.connect([(applytransform ,merge,[('output_image','in_files')])
                          ])
    
    # remask timeseries
    mask = Node(fsl.ApplyMask(out_file='rest_preprocessed2std.nii.gz'),
                name='mask')
    
    transform_ts.connect([(merge, mask, [('merged_file', 'in_file')]),
                          (inputnode, mask, [('mni_mask', 'mask_file')]),
                          (mask, outputnode, [('out_file', 'trans_ts')])
                          ])
    
    # calculate new mean
    tmean = Node(fsl.maths.MeanImage(dimension='T',
                                     out_file='rest_preprocessed2std_mean.nii.gz'),
                 name='tmean')

    transform_ts.connect([(mask, tmean, [('out_file', 'in_file')]),
                          (tmean, outputnode, [('out_file', 'trans_ts_mean')])
                          ])

    # smooth timeseries
    smooth = Node(afni.Merge(blurfwhm=6,
                             doall=True,
                             outputtype='NIFTI_GZ',
                             out_file='smoothed6mm.nii.gz'),
                  name='smooth')
    
    # remask timeseries
    mask2 = Node(fsl.ApplyMask(out_file='rest_preprocessed2std_fwhm6.nii.gz'),
                name='mask2')
    
    transform_ts.connect([(mask, smooth, [('out_file', 'in_files')]),
                          (smooth, mask2, [('out_file', 'in_file')]),
                          (inputnode, mask2, [('mni_mask', 'mask_file')]),
                          (mask2, outputnode, [('out_file', 'trans_ts_smooth')])
                          ])
    
    
    return transform_ts