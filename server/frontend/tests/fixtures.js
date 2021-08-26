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

export const unreadNotifications = {
  count: 2,
  next: null,
  previous: null,
  results: [bucketHitNotification, inaccessibleBugNotification],
};
