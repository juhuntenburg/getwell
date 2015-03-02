from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.io as nio
from reconall import create_reconall_pipeline
import nipype.interfaces.utility as util
from ants import create_normalize_pipeline
from mgzconvert import create_mgzconvert_pipeline


#set subjects to process
subjects = []
for line in open('/scr/ilz2/getwell/subjects_struct_2ndround.txt','r').readlines():
    subjects.append(line.strip())
#subjects=['163','172']

subjects=['106']
 
# set directories
working_dir = '/scr/ilz2/getwell/working_dir/'
data_dir = '/scr/ilz2/getwell/nifti/'
out_dir = '/scr/ilz2/getwell/preprocessed/'
freesurfer_dir = '/scr/ilz2/getwell/freesurfer/' 
standard_brain = '/usr/share/fsl/5.0/data/standard/MNI152_T1_1mm_brain.nii.gz'

# main workflow
struct_preproc = Workflow(name='struct_preproc')
struct_preproc.base_dir = working_dir
struct_preproc.config['execution']['crashdump_dir'] = struct_preproc.base_dir + "/crash_files"

# infosource to iterate over scans
subject_infosource = Node(util.IdentityInterface(fields=['subject_id']), 
                  name='subject_infosource')
subject_infosource.iterables=('subject_id', subjects)


# select files
templates={'anat': '{subject_id}b/anat.nii.gz'}
selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

struct_preproc.connect([(subject_infosource, selectfiles, [('subject_id', 'subject_id')])])

# workflow to run freesurfer reconall
reconall=create_reconall_pipeline()
reconall.inputs.inputnode.fs_subjects_dir=freesurfer_dir
struct_preproc.connect([(subject_infosource, reconall, [('subject_id', 'inputnode.fs_subject_id')]),
                        (selectfiles, reconall, [('anat', 'inputnode.anat')])])

# workflow to get brain, head and wmseg from freesurfer and convert to nifti
mgzconvert=create_mgzconvert_pipeline()
struct_preproc.connect([(reconall, mgzconvert, [('outputnode.fs_subject_id', 'inputnode.fs_subject_id'),
                                                ('outputnode.fs_subjects_dir', 'inputnode.fs_subjects_dir')])
                        ])

# workflow to normalize anatomy to standard space
normalize=create_normalize_pipeline()
normalize.inputs.inputnode.standard = standard_brain
struct_preproc.connect([(mgzconvert, normalize, [('outputnode.anat_brain', 'inputnode.anat')])])

#sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                         parameterization=False,
                         substitutions=[('transform_Warped', 'T1_brain2std')]),
             name='sink')

struct_preproc.connect([(subject_infosource, sink, [('subject_id', 'container')]),
                        (mgzconvert, sink, [('outputnode.anat_head', 'anat.@head'),
                                            ('outputnode.anat_brain', 'anat.@brain'),
                                            ('outputnode.brain_mask', 'anat.@brain_mask'),
                                            ('outputnode.wmedge', 'anat.@wmedge'),
                                            ('outputnode.wmseg', 'anat.@wmseg')]),
                        (normalize, sink, [('outputnode.anat2std', 'anat.@anat2std'),
                                           ('outputnode.anat2std_transforms', 'anat.@anat2std_transforms'),
                                           ('outputnode.std2anat_transforms', 'anat.@std2anat_transforms')])
                        ])
#struct_preproc.write_graph(dotfilename='struct_preproc.dot', graph2use='colored', format='pdf', simple_form=True)
struct_preproc.run(plugin='MultiProc')#plugin='CondorDAGMan')
