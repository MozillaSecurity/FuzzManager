export const emptyNotifications = {
  count: 0,
  next: null,
  previous: null,
  results: [],
};

export const bucketHitNotification = {
  actor_url: "/crashmanager/signatures/8/",
  description: "The bucket 8 received a new crash entry 42",
  external_bug_url: null,
  id: 2,
  target_url: "/crashmanager/crashes/42/",
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

export const tasksFailedNotification = {
  actor_url: "/taskmanager/pools/1/",
  description: "Pool 1 has failed tasks",
  external_bug_url: null,
  id: 3,
  target_url: "/taskmanager/pools/1/",
  timestamp: "2021-06-23T10:42:00Z",
  verb: "tasks_failed",
};

export const unreadNotifications = {
  count: 3,
  next: null,
  previous: null,
  results: [
    bucketHitNotification,
    inaccessibleBugNotification,
    tasksFailedNotification,
  ],
};

export const emptyBuckets = [];

export const buckets = [
  {
    best_quality: 0,
    bug: "1630739",
    bug_closed: null,
    bug_hostname: "bugzilla-dev.allizom.org",
    bug_urltemplate: "https://bugzilla-dev.allizom.org/1630739",
    crash_history: [{ begin: "2021-06-23T10:42:00Z", count: 1 }],
    doNotReduce: false,
    frequent: false,
    has_optimization: false,
    id: 1,
    opt_pre_url: "/crashmanager/signatures/1/preoptimized/",
    permanent: false,
    reassign_in_progress: false,
    shortDescription: "A short description for bucket 1",
    signature: "{ symptoms: 'some symptoms' }",
    size: 3,
    view_url: "/crashmanager/signatures/1/",
  },
  {
    best_quality: 0,
    bug: null,
    bug_closed: null,
    bug_hostname: null,
    bug_urltemplate: null,
    crash_history: [{ begin: "2021-06-23T10:42:00Z", count: 1 }],
    doNotReduce: false,
    frequent: false,
    has_optimization: false,
    id: 2,
    opt_pre_url: "/crashmanager/signatures/2/preoptimized/",
    permanent: false,
    reassign_in_progress: false,
    shortDescription: "A short description for bucket 2",
    signature: "{ symptoms: 'some symptoms' }",
    size: 5,
    view_url: "/crashmanager/signatures/2/",
  },
];

export const emptyCrashStats = {
  totals: [0, 0, 0],
  inFilterGraphData: new Array(14).fill(0),
  outFilterGraphData: new Array(14).fill(0),
  frequentBuckets: {},
};

export const crashStatsData = {
  totals: [12, 24, 48],
  inFilterGraphData: new Array(24 * 14).fill(5),
  outFilterGraphData: new Array(24 * 14).fill(1),
  frequentBuckets: {
    1: [1, 2, 3],
    2: [3, 0, 0],
  },
};
