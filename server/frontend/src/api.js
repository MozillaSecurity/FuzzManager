import axios from "axios";

const mainAxios = axios.create({
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  withCredentials: true,
});

export const pollAsyncOp = async (id) =>
  (await mainAxios.get(`/reportmanager/rest/op/${id}/`)).status === 200;

export const retrieveBucket = async (id) =>
  (await mainAxios.get(`/reportmanager/rest/buckets/${id}/`)).data;

export const listBuckets = async (params) =>
  (await mainAxios.get("/reportmanager/rest/buckets/", { params })).data;

export const reportStats = async (params) =>
  (await mainAxios.get("/reportmanager/rest/reports/stats/", { params })).data;

export const createBucket = async ({ params, ...data }) =>
  (await mainAxios.post("/reportmanager/rest/buckets/", data, { params })).data;

export const updateBucket = async ({ id, params, ...data }) =>
  (
    await mainAxios.patch(`/reportmanager/rest/buckets/${id}/`, data, {
      params,
    })
  ).data;

export const retrieveReport = async (id) =>
  (await mainAxios.get(`/reportmanager/rest/reports/${id}/`)).data;

export const retrieveReportTestCase = async (id) =>
  (await mainAxios.get(`/reportmanager/rest/reports/${id}/download/`)).data;

export const retrieveReportTestCaseBinary = async (id) =>
  new Uint8Array(
    (
      await mainAxios.request({
        url: `/reportmanager/rest/reports/${id}/download/`,
        responseType: "arraybuffer",
      })
    ).data,
  );

export const deleteReports = async (params) =>
  (await mainAxios.delete("/reportmanager/rest/reports/", { params })).data;

export const listReports = async (params) =>
  (await mainAxios.get("/reportmanager/rest/reports/", { params })).data;

export const listBugProviders = async () =>
  (await mainAxios.get("/reportmanager/rest/bugproviders/")).data;

export const listTemplates = async () =>
  (await mainAxios.get("/reportmanager/rest/bugzilla/templates/")).data;

export const listUnreadNotifications = async (params) =>
  (await mainAxios.get("/reportmanager/rest/inbox/", { params })).data;

export const dismissNotification = async (id) =>
  (await mainAxios.patch(`/reportmanager/rest/inbox/${id}/mark_as_read/`)).data;

export const dismissAllNotifications = async () =>
  (await mainAxios.patch("/reportmanager/rest/inbox/mark_all_as_read/")).data;
