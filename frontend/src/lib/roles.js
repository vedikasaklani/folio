export const ROLE_LABEL = { OW: 'Owner', AD: 'Admin', ED: 'Editor', VR: 'Viewer' }
export const canWrite = (role) => role !== 'VR'
