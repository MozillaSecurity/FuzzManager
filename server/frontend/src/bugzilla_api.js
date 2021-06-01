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
