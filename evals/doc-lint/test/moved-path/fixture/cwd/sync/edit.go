package sync

import "time"

type Edit struct {
	Note       string
	Body       string
	ServerTime time.Time
}
