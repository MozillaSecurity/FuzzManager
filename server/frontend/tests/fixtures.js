export const emptyNotifications = {
  count: 0,
  next: null,
  previous: null,
  results: [],
};

export const bucketHitNotification = {
  actor_url: "/reportmanager/buckets/8/",
  description: "The bucket 8 received a new report entry 42",
  external_bug_url: null,
  id: 2,
  target_url: "/reportmanager/reports/42/",
  timestamp: "2021-06-23T10:42:00Z",
  verb: "bucket_hit",
};

export const inaccessibleBugNotification = {
  actor_url: null,
  description:
    "The bug 29 pointing to the external bug 1630591 on bugzilla-dev.allizom.org has become inaccessible",
  external_bug_url: "https://bugzilla-dev.allizom.org/1630591",
  id: 1,
  target_url: null,
  timestamp: "2021-07-16T08:37:20Z",
  verb: "inaccessible_bug",
};

export const unreadNotifications = {
  count: 2,
  next: null,
  previous: null,
  results: [bucketHitNotification, inaccessibleBugNotification],
};

export const emptyBuckets = {
  count: 0,
  next: null,
  previous: null,
  results: [],
};

export const buckets = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      bug: "1630739",
      bug_closed: null,
      bug_hostname: "bugzilla-dev.allizom.org",
      bug_urltemplate: "https://bugzilla-dev.allizom.org/1630739",
      id: 1,
      description: "A short description for bucket 1",
      signature: "{ symptoms: 'some symptoms' }",
      size: 3,
      view_url: "/reportmanager/buckets/1/",
      report_history: [{ begin: "2021-06-23T10:42:00Z", count: 1 }],
    },
    {
      bug: null,
      bug_closed: null,
      bug_hostname: null,
      bug_urltemplate: null,
      id: 2,
      description: "A short description for bucket 2",
      signature: "{ symptoms: 'some symptoms' }",
      size: 5,
      view_url: "/reportmanager/buckets/2/",
      report_history: [{ begin: "2021-06-23T10:42:00Z", count: 1 }],
    },
  ],
};

export const emptyReportStats = {
  totals: [0, 0, 0],
  inFilterGraphData: new Array(14).fill(0),
  outFilterGraphData: new Array(14).fill(0),
  frequentBuckets: {},
};

export const reportStatsData = {
  totals: [12, 24, 48],
  inFilterGraphData: new Array(24 * 14).fill(5),
  outFilterGraphData: new Array(24 * 14).fill(1),
  frequentBuckets: {
    1: [1, 2, 3],
    2: [3, 0, 0],
  },
};
