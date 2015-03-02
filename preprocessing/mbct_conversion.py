# imports for pipeline
from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
from dcmconvert import create_dcmconvert_pipeline
import nipype.interfaces.io as nio


working_dir = '/scr/ilz2/getwell/working_dir/'
data_dir = '/scr/ilz2/getwell/raw/'
out_dir = '/scr/ilz2/getwell/nifti/'

loe = []
for line in open('/scr/ilz2/getwell/subjects_loe.txt','r').readlines():
    loe.append(line.strip())
      
getwell = []
for line in open('/scr/ilz2/getwell/subjects_getwell.txt','r').readlines():
    getwell.append(line.strip())

#loe=['loe_4117', 'loe_4190']
#getwell=['107a', '107b']


convert = Workflow(name='convert')
convert.base_dir = working_dir
convert.config['execution']['crashdump_dir'] = convert.base_dir + "/crash_files"

# infosource to iterate over scans
subject_infosource = Node(util.IdentityInterface(fields=['loe_id', 'getwell_id']), 
                  name='subject_infosource')
subject_infosource.iterables=[('loe_id', loe), ('getwell_id', getwell)]
subject_infosource.synchronize=True


# define templates and select files
templates={'anat':'{loe_id}/anat/*.dcm',
           'rest': '{loe_id}/rest/*.dcm'}

selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

convert.connect([(subject_infosource, selectfiles, [('loe_id', 'loe_id')])])


# workflow to convert dicoms
anat_dcmconvert=create_dcmconvert_pipeline(name='anat_convert')
anat_dcmconvert.inputs.inputnode.filename='anat'
convert.connect([(selectfiles, anat_dcmconvert, [('anat', 'inputnode.dicoms')])])

rest_dcmconvert=create_dcmconvert_pipeline(name='rest_convert')
rest_dcmconvert.inputs.inputnode.filename='rest'
convert.connect([(selectfiles, rest_dcmconvert, [('rest', 'inputnode.dicoms')])])

# sink to store files
sink = Node(nio.DataSink(base_directory=out_dir,
                          parameterization=False), 
             name='sink')

convert.connect([(subject_infosource, sink, [('getwell_id', 'container')]),
                 (anat_dcmconvert, sink, [('outputnode.nifti', '@anat')]),
                 (rest_dcmconvert, sink, [('outputnode.nifti', '@rest')])
                 ])


convert.run()#(plugin='CondorDAGMan')