from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.c3 as c3
import os

def create_coreg_pipeline(name='coreg'):
    
    # fsl output type
    fsl.FSLCommand.set_default_output_type('NIFTI_GZ')
    
    # initiate workflow
    coreg = Workflow(name='coreg')
    
    #inputnode 
    inputnode=Node(util.IdentityInterface(fields=['anat_brain',
                                                  'epi_mean',
                                                  'fs_subject_id',
                                                  'fs_subjects_dir'
                                                  ]),
                   name='inputnode')
    
    # outputnode                                     
    outputnode=Node(util.IdentityInterface(fields=['epi2anat_mat',
                                                   'epi2anat_itk',
                                                   'epi2anat']),
                    name='outputnode')
    
    
    # linear registration with bbregister
    bbregister = Node(fs.BBRegister(contrast_type='t2',
                                    out_fsl_file='epi2anat.mat',
                                    registered_file='rest_mean_coregistered.nii.gz',
                                    init='fsl'
                                    ),
                    name='bbregister')
    
    coreg.connect([(inputnode, bbregister, [('fs_subjects_dir', 'subjects_dir'),
                                                 ('fs_subject_id', 'subject_id'),
                                                 ('epi_mean', 'source_file')]),
                        (bbregister, outputnode, [('out_fsl_file', 'epi2anat_mat'),
                                                  ('registered_file', 'epi2anat')
                                                  ]),
                        ])

    # convert transform to itk
    itk = Node(interface=c3.C3dAffineTool(fsl2ras=True,
                                          itk_transform='epi2anat.txt'), 
                     name='itk')
    
    coreg.connect([(inputnode, itk, [('anat_brain', 'reference_file'),
                                     ('epi_mean', 'source_file')]),
                   (bbregister, itk, [('out_fsl_file', 'transform_file')]),
                   (itk, outputnode, [('itk_transform', 'epi2anat_itk')])
                   ])
    
    return coreg