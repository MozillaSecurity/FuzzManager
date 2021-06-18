import axios from "axios";

const bugzillaAxios = axios.create({
  withCredentials: false,
});

export const whoAmI = async ({ hostname, key }) =>
  (
    await bugzillaAxios.get(`https://${hostname}/rest/whoami`, {
      headers: { "X-BUGZILLA-API-KEY": key },
    })
  ).data;

export const fetchLatestConfiguration = async (hostname) =>
  (await bugzillaAxios.get(`https://${hostname}/latest/configuration`)).data;

export const fetchPossibleDuplicates = async ({ hostname, params, headers }) =>
  (
    await bugzillaAxios.get(
      `https://${hostname}/rest/bug/possible_duplicates`,
      {
        params: { ...params, include_fields: "id,summary,component,status" },
        headers,
      }
    )
  ).data;

export const fetchSuggestedUsers = async ({ hostname, params, headers }) =>
  (
    await bugzillaAxios.get(`https://${hostname}/rest/user`, {
      params,
      headers,
    })
  ).data;

export const createBug = async ({ hostname, headers, ...data }) =>
  (await bugzillaAxios.post(`https://${hostname}/rest/bug`, data, { headers }))
    .data;

export const createComment = async ({ hostname, id, headers, ...data }) =>
  (
    await bugzillaAxios.post(
      `https://${hostname}/rest/bug/${id}/comment`,
      data,
      { headers }
    )
  ).data;

export const retrieveComment = async ({ hostname, id }) =>
  (await bugzillaAxios.get(`https://${hostname}/rest/bug/comment/${id}`)).data;

export const createAttachment = async ({ hostname, id, headers, ...data }) =>
  (
    await bugzillaAxios.post(
      `https://${hostname}/rest/bug/${id}/attachment`,
      data,
      { headers }
    )
  ).data;
