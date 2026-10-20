# API

## POST /hooks/{target}

Takes a JSON body of up to 1 MB and returns 202 with a delivery id. The body is sent on to the target named in the path.

## GET /deliveries/{id}

Returns the delivery's state (queued, sent or failed) and the number of attempts so far.
