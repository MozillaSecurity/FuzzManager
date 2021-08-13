import axios from "axios";

const mainAxios = axios.create({
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  withCredentials: true,
});

export const retrieveBucket = async (id) =>
  (await mainAxios.get(`/crashmanager/rest/buckets/${id}/`)).data;

export const listBuckets = async (params) =>
  (await mainAxios.get("/crashmanager/rest/buckets/", { params })).data;

export const createBucket = async ({ params, ...data }) =>
  (await mainAxios.post("/crashmanager/rest/buckets/", data, { params })).data;

export const updateBucket = async ({ id, params, ...data }) =>
  (await mainAxios.patch(`/crashmanager/rest/buckets/${id}/`, data, { params }))
    .data;

export const retrieveCrash = async (id) =>
  (await mainAxios.get(`/crashmanager/rest/crashes/${id}/`)).data;

export const retrieveCrashTestCase = async (id) =>
  (await mainAxios.get(`/crashmanager/rest/crashes/${id}/download/`)).data;

export const retrieveCrashTestCaseBinary = async (id) =>
  new Uint8Array(
    (
      await mainAxios.request({
        url: `/crashmanager/rest/crashes/${id}/download/`,
        responseType: "arraybuffer",
      })
    ).data
  );

export const listCrashes = async (params) =>
  (await mainAxios.get("/crashmanager/rest/crashes/", { params })).data;

export const listBugProviders = async () =>
  (await mainAxios.get("/crashmanager/rest/bugproviders/")).data;

export const listTemplates = async () =>
  (await mainAxios.get("/crashmanager/rest/bugzilla/templates/")).data;

export const listUnreadNotifications = async (params) =>
  (await mainAxios.get("/crashmanager/rest/inbox/", { params })).data;

export const dismissNotification = async (id) =>
  (await mainAxios.patch(`/crashmanager/rest/inbox/${id}/mark_as_read/`)).data;

export const dismissAllNotifications = async () =>
  (await mainAxios.patch("/crashmanager/rest/inbox/mark_all_as_read/")).data;

export const listPools = async (params) =>
  (await mainAxios.get("/taskmanager/rest/pools/", { params })).data;

export const listTasks = async (params) =>
  (await mainAxios.get("/taskmanager/rest/tasks/", { params })).data;
