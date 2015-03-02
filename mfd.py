import numpy as np


subjects = []
with open('/scr/hugo1/getwell/glm_5_like3_validsufficient/subjects_glm5.txt', 'r') as s:
    subjects = [line.strip() for line in s]

 
mfd_pre = []
mfd_post = []
 
for sub in subjects:
     
    for sess in ['pre', 'post']:
 
        with open('/scr/hugo1/getwell/preprocessed/'+sub+'/rest_'+sess+'/realign/rest_realigned_rel.rms', 'r') as f:
            rms_val = [abs(float(line.strip())) for line in f]
            
        rms_mean=np.mean(rms_val)
         
        if sess=='pre': 
            mfd_pre.append(rms_mean)
             
        elif sess=='post': 
            mfd_post.append(rms_mean)
            
#mfd_pre = mfd_pre[:-2]
#mfd_post =  mfd_post[:-2]

mean_mfd_pre = np.mean(mfd_pre)
mean_mfd_post = np.mean(mfd_post)

mfd_pre_demeaned=np.zeros_like(mfd_pre)
mfd_post_demeaned=np.zeros_like(mfd_post)


for i in range(len(mfd_pre)):
    mfd_pre_demeaned[i] = mfd_pre[i]-mean_mfd_pre

for j in range(len(mfd_post)):
    mfd_post_demeaned[j] = mfd_post[j]-mean_mfd_post
    
print len(mfd_pre)
print mean_mfd_pre
print mfd_pre_demeaned

print mfd_post
print mean_mfd_post
print mfd_post_demeaned


with open('/scr/hugo1/getwell/glm_5_like3_validsufficient/glm5_mfd_pre.txt', 'rw+') as p1:
    for val in mfd_pre:
        print>>p1, val
        
with open('/scr/hugo1/getwell/glm_5_like3_validsufficient/glm5_mfd_post.txt', 'rw+') as p2:
    for val in mfd_post:
        print>>p2, val
        
        
with open('/scr/hugo1/getwell/glm_5_like3_validsufficient/glm5_mfd_pre_demeaned.txt', 'rw+') as p3:
    for val in mfd_pre_demeaned:
        print>>p3, val
        
with open('/scr/hugo1/getwell/glm_5_like3_validsufficient/glm5_mfd_post_demeaned.txt', 'rw+') as p4:
    for val in mfd_post_demeaned:
        print>>p4, val
        