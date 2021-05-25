import axios from "axios";

const mainAxios = axios.create({
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  withCredentials: true,
});

export const retrieveBucket = async (id) =>
  (await mainAxios.get(`/crashmanager/rest/buckets/${id}/`)).data;

export const createBucket = async ({ params, ...data }) =>
  (await mainAxios.post("/crashmanager/rest/buckets/", data, { params })).data;

export const updateBucket = async ({ id, params, ...data }) =>
  (await mainAxios.patch(`/crashmanager/rest/buckets/${id}/`, data, { params }))
    .data;

export const listCrashes = async (params) =>
  (await mainAxios.get("/crashmanager/rest/crashes/", { params })).data;
