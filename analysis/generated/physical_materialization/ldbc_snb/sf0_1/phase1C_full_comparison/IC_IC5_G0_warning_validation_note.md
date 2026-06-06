# Manual validation note: IC5 / G0 warning

The physical materialization manifest marked `IC5_NewGroups / G0` as
`ready_with_warnings`.

A direct MongoDB validation showed that the candidate database contains the
required physical collections for the IC5 reference traversal:

- persons: 1528
- posts: 135701
- comments: 151043
- forums: 13750
- person_knows_person: 14073
- forum_has_member_person: 123268
- forum_container_of_post: 135701
- post_has_creator_person: 135701

Therefore, this warning is interpreted as a manifest/validation-summary recording
issue, not as a materialization failure. The candidate is considered ready for
the physical benchmark.
