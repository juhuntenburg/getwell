import nibabel
import numpy as np
 
epis = []
with open('/scr/hugo1/getwell/dominance/dominance_epi.txt', 'r') as s:
    epis = [line.strip() for line in s]
    
networks = []
with open('/scr/hugo1/getwell/dominance/dominance_networks.txt', 'r') as s:
    networks = [line.strip() for line in s]

idxs = []
ratios = []
switches_dmn2tpn=[]
switches_tpn2dmn=[]
    
for sub in range(len(epis)):
    print 'running test '+str(sub+1)
    epi = nibabel.load(epis[sub])
    epi_data = epi.get_data()
    epi_shape = epi.get_shape()
 
    network = nibabel.load(networks[sub])
    network_data = network.get_data()
     
     
#     dmn_mask = network_data[:,:,:,3] > 0
#     dmn_weights = network_data[dmn_mask,3]
#     dmn_wght_av_timeseries = np.average(epi_data[dmn_mask,:],axis=0, weights=dmn_weights)
#  
#     tpn_mask = network_data[:,:,:,3] < 0
#     tpn_weights = network_data[tpn_mask,3]
#     tpn_wght_av_timeseries =  np.average(epi_data[tpn_mask,:],axis=0, weights=tpn_weights)
     
    dmn_tpn = network_data[:,:,:,3] 
    
    dmn_mask = dmn_tpn !=0#> 0
    tpn_mask = dmn_tpn !=0#< 0
    
    dmn_flat = dmn_tpn[dmn_mask]
    tpn_flat = dmn_tpn[tpn_mask]
    
    dmn_90th_percentile = np.percentile(dmn_flat, 90)#np.percentile(dmn_flat, 90)
    tpn_90th_percentile = np.percentile(dmn_flat, 10)#-np.percentile(abs(tpn_flat),90)
    
    dmn_top10_mask = dmn_tpn > dmn_90th_percentile
    tpn_top10_mask = dmn_tpn < tpn_90th_percentile
    
    dmn_top10 = dmn_tpn[dmn_top10_mask]
    tpn_top10 = dmn_tpn[tpn_top10_mask]
     
    from scipy import stats
#     z_dmn_wght_av_timeseries = stats.zscore(dmn_wght_av_timeseries, axis = 0)
#     z_tpn_wght_av_timeseries = stats.zscore(tpn_wght_av_timeseries, axis = 0)
#  
#     dmn_dominance_vector = np.zeros(epi_shape[3])
#     dmn_dominance_vector[z_dmn_wght_av_timeseries > z_tpn_wght_av_timeseries]=1
#     dmn_dominance_vector[z_dmn_wght_av_timeseries < z_tpn_wght_av_timeseries]=(-1)
#     idx_dmn_dominance = sum(dmn_dominance_vector)


    dmn_top10_av_timeseries = np.average(epi_data[dmn_top10_mask,:], axis=0)
    tpn_top10_av_timeseries = np.average(epi_data[tpn_top10_mask,:], axis=0)
     
    z_dmn_top10_av_timeseries = stats.zscore(dmn_top10_av_timeseries, axis = 0)
    z_tpn_top10_av_timeseries = stats.zscore(tpn_top10_av_timeseries, axis = 0)
    
    dmn_dominance_vector = np.zeros(epi_shape[3])
    dmn_dominance_vector[z_dmn_top10_av_timeseries > z_tpn_top10_av_timeseries]=1
    dmn_dominance_vector[z_dmn_top10_av_timeseries < z_tpn_top10_av_timeseries]=(-1)
    idx_dmn_dominance = sum(dmn_dominance_vector)
    
    ratio_dmn_dominance_vector = np.zeros(epi_shape[3])
    ratio_dmn_dominance_vector[z_dmn_top10_av_timeseries > z_tpn_top10_av_timeseries]=1
    ratio_tpn_dominance_vector = np.zeros(epi_shape[3])
    ratio_tpn_dominance_vector[z_dmn_top10_av_timeseries < z_tpn_top10_av_timeseries]=1
    dmn_tpn_ratio=sum(ratio_dmn_dominance_vector)/sum(ratio_tpn_dominance_vector)
    
    
    
    switch_dmn2tpn=0
    switch_tpn2dmn=0
    
    for tp in range(len(dmn_dominance_vector)-1):
        if dmn_dominance_vector[tp+1]>dmn_dominance_vector[tp]:
            switch_dmn2tpn+=1
        if dmn_dominance_vector[tp+1]<dmn_dominance_vector[tp]:
            switch_tpn2dmn+=1
 
    idxs.append(idx_dmn_dominance)
    ratios.append(dmn_tpn_ratio)
    switches_dmn2tpn.append(switch_dmn2tpn)
    switches_tpn2dmn.append(switch_tpn2dmn)
 
idxs_pre=idxs[::2]
idxs_post=idxs[1::2]

ratios_pre=ratios[::2]
ratios_post=ratios[1::2]

switches_dmn2tpn_pre=switches_dmn2tpn[::2]
switches_dmn2tpn_post=switches_dmn2tpn[1::2]

switches_tpn2dmn_pre=switches_tpn2dmn[::2]
switches_tpn2dmn_post=switches_tpn2dmn[1::2]

with open('/scr/hugo1/getwell/dominance/dominance_pre_new.txt', 'rw+') as f1:
    for val in idxs_pre:
        print>>f1, val
        
with open('/scr/hugo1/getwell/dominance/dominance_post_new.txt', 'rw+') as f2:
    for val in idxs_post:
        print>>f2, val
        
with open('/scr/hugo1/getwell/dominance/dominance_pre_ratio.txt', 'rw+') as f3:
    for val in ratios_pre:
        print>>f3, val
        
with open('/scr/hugo1/getwell/dominance/dominance_post_ratio.txt', 'rw+') as f4:
    for val in ratios_post:
        print>>f4, val
        
with open('/scr/hugo1/getwell/dominance/dominance_pre_dmn2tpn.txt', 'rw+') as f5:
    for val in switches_dmn2tpn_pre:
        print>>f5, val

with open('/scr/hugo1/getwell/dominance/dominance_post_dmn2tpn.txt', 'rw+') as f6:
    for val in switches_dmn2tpn_post:
        print>>f6, val

with open('/scr/hugo1/getwell/dominance/dominance_pre_tpn2dmn.txt', 'rw+') as f7:
    for val in switches_tpn2dmn_pre:
        print>>f7, val

with open('/scr/hugo1/getwell/dominance/dominance_post_tpn2dmn.txt', 'rw+') as f8:
    for val in switches_tpn2dmn_post:
        print>>f8, val
#print idxs_pre
#print idxs_post


