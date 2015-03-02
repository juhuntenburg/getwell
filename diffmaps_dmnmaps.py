# imports for pipeline
from nipype.pipeline.engine import Node, Workflow
import nipype.interfaces.utility as util
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import pandas as pd

with open('/scr/hugo1/getwell/subjects_dual_regression.txt', 'r') as f:
    subjects = [line.strip() for line in f]

# local base and output directory (should usually not change)
data_dir = '/scr/hugo1/getwell/dual_regression/renamed_outputs/'
base_dir = '/scr/hugo1/getwell/working_dir/'
out_dir = '/scr/hugo1/getwell/diffmaps/'

# workflow
diff = Workflow(name='diff')
diff.base_dir = base_dir
diff.config['execution']['crashdump_dir'] = diff.base_dir + "/crash_files"


subject_infosource = Node(util.IdentityInterface(fields=['subject']), 
                  name='scan_infosource')
subject_infosource.iterables=('subject', subjects)

def difffile(subject):
    return 'diffmaps_'+str(subject)+'.nii.gz'

def dmnfile(subject):
    return 'dmn_diffmap_'+str(subject)+'.nii.gz'

# select files
templates={'corrmap_pre': 'corrmaps_{subject}_pre.nii.gz',
           'corrmap_post': 'corrmaps_{subject}_post.nii.gz',
           }
selectfiles = Node(nio.SelectFiles(templates,
                                   base_directory=data_dir),
                   name="selectfiles")

diff.connect(subject_infosource, 'subject', selectfiles, 'subject')

# make diffmaps
subtract=Node(fsl.BinaryMaths(operation='sub'),
              name='subtract')

diff.connect(selectfiles, 'corrmap_pre', subtract, 'in_file')
diff.connect(selectfiles, 'corrmap_post', subtract, 'operand_file')
diff.connect(subject_infosource, ('subject', difffile), subtract, 'out_file')

# extract dmn
dmn=Node(fsl.ExtractROI(t_min=3,
                        t_size=1),
         name='dmn')

diff.connect(subtract, 'out_file', dmn, 'in_file')
diff.connect(subject_infosource, ('subject', dmnfile), dmn, 'roi_file')


# sink
sink = Node(nio.DataSink(base_directory=out_dir,
                         parameterization=False),
                name='sink')

diff.connect([(subtract, sink, [('out_file', '@diffmap')]),
              (dmn, sink, [('roi_file', '@dmn')])])

diff.run()