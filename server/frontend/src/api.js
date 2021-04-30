import axios from 'axios'

axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
axios.defaults.withCredentials = true

export const retrieveBucket = async id => (await axios.get(`/crashmanager/rest/buckets/${id}/`)).data

export const createBucket = async ({ params, ...data }) => (await axios.post(`/crashmanager/rest/buckets/`, data, { params })).data

export const updateBucket = async ({ id, params, ...data }) => (await axios.patch(`/crashmanager/rest/buckets/${id}/`, data, { params })).data