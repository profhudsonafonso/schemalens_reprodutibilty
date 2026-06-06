# Manual validation note: IS7 / G0 warning

The materialization manifest marked `IS7_RepliesOfMessage / G0` as
`ready_with_warnings` because the manifest entry recorded `posts` with zero
documents in `physical_collections_created_json`.

A direct MongoDB validation showed that the candidate database contains the
required physical collections:

- posts: 135701
- comments: 151043
- comment_reply_of_post: 74256
- comment_reply_of_comment: 76787
- post_has_creator_person: 135701
- comment_has_creator_person: 151043
- persons: 1528

Therefore, this warning is interpreted as a manifest-recording issue, not as a
materialization failure. The candidate is considered ready for the physical
benchmark.
