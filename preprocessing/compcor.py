def extract_noise_components(realigned_file, noise_mask_file, num_components, csf_mask_file, selector,
                             realignment_parameters=None, outlier_file=None, regress_before_PCA=True):

    import os
    from nibabel import load
    import numpy as np
    from scipy import linalg
    from scipy.signal import detrend
    from nipype import logging
    logger = logging.getLogger('interface')

    def try_import(fname):
        try:
            a = np.genfromtxt(fname)
            return a
        except:
            return np.array([])

    options = np.array([noise_mask_file, csf_mask_file])
    selector = np.array(selector)
    imgseries = load(realigned_file)
    nuisance_matrix = np.ones((imgseries.shape[-1], 1))
    if realignment_parameters is not None:
        logger.debug('adding motion pars')
        logger.debug('%s %s' % (str(nuisance_matrix.shape),
            str(np.genfromtxt(realignment_parameters).shape)))
        nuisance_matrix = np.hstack((nuisance_matrix,
                                     np.genfromtxt(realignment_parameters)))
    if outlier_file is not None:
        logger.debug('collecting outliers')
        outliers = try_import(outlier_file)
        if outliers.shape == (): # 1 outlier
            art = np.zeros((imgseries.shape[-1], 1))
            art[np.int_(outliers), 0] = 1 # art outputs 0 based indices
            nuisance_matrix = np.hstack((nuisance_matrix, art))
        elif outliers.shape[0] == 0: # empty art file
            pass
        else: # >1 outlier
            art = np.zeros((imgseries.shape[-1], len(outliers)))
            for j, t in enumerate(outliers):
                art[np.int_(t), j] = 1 # art outputs 0 based indices
            nuisance_matrix = np.hstack((nuisance_matrix, art))
    if selector.all(): # both values of selector are true, need to concatenate
        tcomp = load(noise_mask_file)
        acomp = load(csf_mask_file)
        voxel_timecourses = imgseries.get_data()[np.nonzero(tcomp.get_data() +
                                                            acomp.get_data())]
    else:
        noise_mask_file = options[selector][0]
        noise_mask = load(noise_mask_file)
        voxel_timecourses = imgseries.get_data()[np.nonzero(noise_mask.get_data())]

    voxel_timecourses = voxel_timecourses.byteswap().newbyteorder()
    voxel_timecourses[np.isnan(np.sum(voxel_timecourses,axis=1)),:] = 0
    if regress_before_PCA:
        logger.debug('Regressing motion')
        for timecourse in voxel_timecourses:
            #timecourse[:] = detrend(timecourse, type='constant')
            coef_, _, _, _ = np.linalg.lstsq(nuisance_matrix, timecourse[:, None])
            timecourse[:] = (timecourse[:, None] - np.dot(nuisance_matrix,
                                                          coef_)).ravel()

    pre_svd = os.path.abspath('pre_svd.npz')
    np.savez(pre_svd,voxel_timecourses=voxel_timecourses)
    _, _, v = linalg.svd(voxel_timecourses, full_matrices=False)
    components_file = os.path.join(os.getcwd(), 'noise_components.txt')
    np.savetxt(components_file, v[:num_components, :].T)
    return components_file, pre_svd

