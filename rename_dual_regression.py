import pandas as pd
import nipype.interfaces.fsl as fsl
from shutil import copyfile


df=pd.read_excel('/scr/hugo1/getwell/dual_regression/dual_regression_mapping.xls', 'Sheet1')

input=list(df['input'])
output=list(df['output'])
subjects=[]
new_files=[]


for i in range(len(input)):
    subject=input[i][31:34]
    
    
    sess=input[i][40:43]
    
    if sess == 'pre':
        new_file='/scr/hugo1/getwell/dual_regression/renamed_outputs/corrmaps_'+subject+'_pre.nii.gz'
        new_files.append(new_file)
        print subject
        
    elif sess == 'pos':
        new_file='/scr/hugo1/getwell/dual_regression/renamed_outputs/corrmaps_'+subject+'_post.nii.gz'
        new_files.append(new_file)
        
    else:
        print 'error with file'
    
    copyfile(output[i], new_file)
    

#subtract=fsl.BinaryMaths()